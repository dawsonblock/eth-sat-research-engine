"""Universal SAT research entry: reduction first, jet fast path last (E1/E4).

Pipeline phases (no silent fallbacks):

1. Admit 3-CNF class (width ≤ 3 per clause).
2. Fixed-density ``source_cnf_network`` + structural check (finite, not R9.4).
3. Jet-point fast parent–child — **refused** unless a ``BoundedInteractionCertificate``
   is supplied (interaction fixture only; not arbitrary 3-CNF).
4. Exact fallback: reference decision or ``adaptive_count`` with explicit ledger rows.

No universal speedup or theorem is claimed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Mapping, Optional

from veritas.core.cnf import CNF
from veritas.research.adaptive_contract import adaptive_count
from veritas.research.sat_work_accounting import (
    DecompositionWorkLedger,
    aggregate_ledger,
    exponential_width_proxy,
)
from veritas.research.source_cnf import SourceCNFNetwork, source_cnf_network
from veritas.research.sat_external_baselines import run_baseline_matrix
from veritas.research.sat_phase_c_reduction import (
    DEFAULT_PHASE_C_BOUNDS,
    PhaseCBounds,
    phase_c_refusal_if_out_of_bounds,
    plan_primal_component_split,
)
from veritas.research.source_cnf_check import check_source_cnf_network
from veritas.solvers.reference import solve


class UniversalSatMode(str, Enum):
    DECISION = "decision"
    COUNT = "count"


@dataclass(frozen=True)
class BoundedInteractionCertificate:
    """E4 gate: fast jet solve allowed only with an explicit interaction fixture cert."""

    schema: str
    fixture_id: str
    qualification: str

    def to_dict(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "fixture_id": self.fixture_id,
            "qualification": self.qualification,
        }


# Pinned interaction harness (96-wire circulant); does not connect arbitrary CNF → parent.
INTERACTION_96_CERT = BoundedInteractionCertificate(
    schema="VERITAS_BOUNDED_INTERACTION_CERT_V1",
    fixture_id="interaction_96_circulant_jet1_beta0",
    qualification="finite_scaled_experiment_not_cnf_reduction",
)


def _transform_work_proxy(*, n: int, m: int, edges: int, factors: int) -> int:
    return n * max(m, 1) + edges + factors


def _check_work_proxy(edges: int) -> int:
    return max(1, edges // 2)


def require_3_cnf(cnf: CNF) -> None:
    if not all(0 < len(clause) <= 3 for clause in cnf.clauses):
        raise ValueError("supported class is 3-CNF (clauses width 1..3)")


def encode_fixed_density_reduction(
    cnf: CNF,
    *,
    max_wires: int,
    max_factors: int,
) -> tuple[Optional[SourceCNFNetwork], Optional[dict], DecompositionWorkLedger]:
    """Phase B.1: fixed-density CNF → subdivided bipartite network."""
    w_old = exponential_width_proxy(min(cnf.n, 28))
    t0 = time.perf_counter()
    try:
        encoded = source_cnf_network(
            cnf,
            max_clause_width=3,
            max_wires=max_wires,
            max_factors=max_factors,
        )
        elapsed = time.perf_counter() - t0
        net = encoded.network
        w_transform = _transform_work_proxy(
            n=cnf.n,
            m=len(cnf.clauses),
            edges=net.edges,
            factors=len(net.factors),
        )
        ledger = DecompositionWorkLedger(
            name="fixed_density_source_encode",
            w_old=w_old,
            w_transform=w_transform,
            child_works=(),
            w_reconstruct=0,
            w_check=0,
            metadata={
                "phase": "transform",
                "elapsed_seconds": elapsed,
                "original_edges": encoded.original_edges,
                "subdivided_edges": net.edges,
                "factors": len(net.factors),
                "outer_reduction_r94": "NOT_IMPLEMENTED",
                "child_split_q": 0,
            },
        )
        return encoded, None, ledger
    except (ValueError, ArithmeticError) as exc:
        elapsed = time.perf_counter() - t0
        ledger = DecompositionWorkLedger(
            name="fixed_density_source_encode",
            w_old=w_old,
            w_transform=_transform_work_proxy(n=cnf.n, m=len(cnf.clauses), edges=0, factors=0),
            child_works=(),
            w_reconstruct=0,
            w_check=0,
            metadata={
                "phase": "transform",
                "status": "REFUSED_ENCODE",
                "reason": str(exc),
                "elapsed_seconds": elapsed,
            },
        )
        return None, {"status": "REFUSED_ENCODE", "reason": str(exc)}, ledger


def structural_check_reduction(
    cnf: CNF,
    encoded: SourceCNFNetwork,
    *,
    max_wires: int,
    max_factors: int,
    w_old: int,
) -> tuple[dict, DecompositionWorkLedger]:
    check = check_source_cnf_network(
        cnf, encoded, max_wires=max_wires, max_factors=max_factors
    )
    w_check = _check_work_proxy(encoded.network.edges)
    ledger = DecompositionWorkLedger(
        name="source_cnf_structural_check",
        w_old=w_old,
        w_transform=0,
        child_works=(),
        w_reconstruct=0,
        w_check=w_check,
        metadata={
            "phase": "check",
            "check_status": check.get("status"),
            "valid": check.get("valid"),
            "general_theorem_proven": check.get("general_theorem_proven", False),
        },
    )
    return check, ledger


def attempt_jet_fast_path(
    *,
    interaction_cert: Optional[BoundedInteractionCertificate],
    w_old: int,
) -> tuple[dict[str, Any], DecompositionWorkLedger]:
    """E4: jet parent–child product only with explicit interaction certificate."""
    if interaction_cert is None:
        detail = {
            "status": "REFUSED",
            "reason": "no_bounded_interaction_certificate",
            "lane": "jet_parent_child_product",
            "note": "Arbitrary 3-CNF lacks ParentCall outer reduction (R9.4 open).",
        }
    elif interaction_cert.fixture_id != INTERACTION_96_CERT.fixture_id:
        detail = {
            "status": "REFUSED",
            "reason": "unknown_interaction_fixture",
            "lane": "jet_parent_child_product",
        }
    else:
        detail = {
            "status": "SKIPPED_DIAGNOSTIC_ONLY",
            "reason": "certificate_present_but_cnf_parent_map_not_wired",
            "lane": "jet_parent_child_product",
            "certificate": interaction_cert.to_dict(),
            "qualification": interaction_cert.qualification,
            "note": "Supply interaction parent JSON in a future flag; no CNF speedup yet.",
        }
    ledger = DecompositionWorkLedger(
        name="jet_fast_parent_coefficient",
        w_old=w_old,
        w_transform=0,
        child_works=(),
        w_reconstruct=0,
        w_check=0,
        metadata={"phase": "jet_fast_path", **detail},
    )
    return detail, ledger


def run_direct_exact(
    cnf: CNF,
    mode: UniversalSatMode,
    *,
    timeout_s: float,
    max_nodes: int,
    adaptive_timeout_s: float,
    w_old: int,
) -> tuple[dict[str, Any], DecompositionWorkLedger]:
    t0 = time.perf_counter()
    if mode is UniversalSatMode.DECISION:
        result = solve(cnf, count=False, timeout_s=min(timeout_s, 30.0), max_nodes=max_nodes)
        elapsed = time.perf_counter() - t0
        out: dict[str, Any] = {
            "lane": "reference_decision",
            "status": result.status,
            "model": result.model,
            "nodes": result.nodes,
            "seconds": result.seconds,
            "reason": result.reason,
        }
        w_reconstruct = result.nodes
    else:
        adaptive = adaptive_count(
            cnf,
            timeout_s=min(adaptive_timeout_s, 60.0),
        )
        elapsed = time.perf_counter() - t0
        count = adaptive.get("count")
        out = {
            "lane": "adaptive_exact_count",
            "status": adaptive.get("status"),
            "count": count,
            "engine": adaptive.get("engine"),
            "seconds": adaptive.get("elapsed_seconds"),
            "warning": adaptive.get("warning"),
        }
        exec_stats = adaptive.get("execution") or {}
        w_reconstruct = int(exec_stats.get("work_assignments", 0) or exec_stats.get("nodes", 0) or 0)
        if w_reconstruct <= 0:
            w_reconstruct = 1
    ledger = DecompositionWorkLedger(
        name="direct_exact_fallback",
        w_old=w_old,
        w_transform=0,
        child_works=(),
        w_reconstruct=w_reconstruct,
        w_check=1,
        metadata={
            "phase": "direct_solve",
            "mode": mode.value,
            "elapsed_seconds": elapsed,
            "qualification": "conventional_exact_not_universal_speedup",
        },
    )
    return out, ledger


def run_universal_sat(
    cnf: CNF,
    mode: Literal["decision", "count"] | UniversalSatMode,
    *,
    max_wires: int = 50_000,
    max_factors: int = 100_000,
    timeout_s: float = 8.0,
    adaptive_timeout_s: float = 15.0,
    max_nodes: int = 200_000,
    interaction_cert: Optional[BoundedInteractionCertificate] = None,
    phase_c_bounds: PhaseCBounds = DEFAULT_PHASE_C_BOUNDS,
    include_baseline_matrix: bool = False,
    baseline_task: Literal["decision", "count"] | None = None,
) -> dict[str, Any]:
    """Run reduction-first pipeline; always ends in an explicit exact fallback lane."""
    if isinstance(mode, str):
        mode = UniversalSatMode(mode)
    require_3_cnf(cnf)
    ledgers: list[DecompositionWorkLedger] = []
    w_old = exponential_width_proxy(min(cnf.n, 28))

    encoded, encode_refusal, enc_ledger = encode_fixed_density_reduction(
        cnf, max_wires=max_wires, max_factors=max_factors
    )
    ledgers.append(enc_ledger)

    reduction_summary: dict[str, Any] = {
        "schema": "VERITAS_UNIVERSAL_REDUCTION_STAGE_V1",
        "encode": encode_refusal or {"status": "ENCODED"},
        "structural_check": None,
    }

    if encoded is not None:
        check, chk_ledger = structural_check_reduction(
            cnf,
            encoded,
            max_wires=max_wires,
            max_factors=max_factors,
            w_old=w_old,
        )
        ledgers.append(chk_ledger)
        reduction_summary["structural_check"] = check
        reduction_summary["encoded_edges"] = encoded.network.edges
        reduction_summary["encoded_factors"] = len(encoded.network.factors)
        if not check.get("valid"):
            reduction_summary["encode"]["status"] = "STRUCTURE_CHECK_FAILED"

    phase_c_summary: dict[str, Any] = {
        "schema": "VERITAS_PHASE_C_STAGE_V1",
        "status": "SKIPPED",
    }
    refusal = phase_c_refusal_if_out_of_bounds(cnf, phase_c_bounds)
    if refusal:
        phase_c_summary = {**refusal, "schema": "VERITAS_PHASE_C_STAGE_V1"}
    elif encoded is not None and (reduction_summary.get("structural_check") or {}).get("valid"):
        try:
            split_summary, split_ledger = plan_primal_component_split(
                cnf, encoded, bounds=phase_c_bounds, w_old=w_old
            )
            ledgers.append(split_ledger)
            phase_c_summary = split_summary
        except ValueError as exc:
            phase_c_summary = {
                "schema": "VERITAS_PHASE_C_STAGE_V1",
                "status": "REFUSED",
                "reason": str(exc),
            }
    reduction_summary["phase_c_split"] = phase_c_summary

    jet_detail, jet_ledger = attempt_jet_fast_path(
        interaction_cert=interaction_cert, w_old=w_old
    )
    ledgers.append(jet_ledger)

    solve_out, solve_ledger = run_direct_exact(
        cnf,
        mode,
        timeout_s=timeout_s,
        max_nodes=max_nodes,
        adaptive_timeout_s=adaptive_timeout_s,
        w_old=w_old,
    )
    ledgers.append(solve_ledger)

    ledger_json = aggregate_ledger(ledgers)

    baseline_matrix = None
    if include_baseline_matrix:
        task = baseline_task or mode.value
        baseline_matrix = run_baseline_matrix(cnf, task=task, include_external=True)

    return {
        "schema": "VERITAS_SAT_UNIVERSAL_RUN_V1",
        "mode": mode.value,
        "formula_sha256": cnf.digest(),
        "n": cnf.n,
        "clause_count": len(cnf.clauses),
        "reduction": reduction_summary,
        "jet_fast_path": jet_detail,
        "result": solve_out,
        "decomposition_work": ledger_json,
        "baseline_matrix": baseline_matrix,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "theorem_backed": False,
        "universal_speedup_claimed": False,
        "qualification": (
            "reduction_first_fixed_density_only; jet_refused_without_E4_cert; "
            "exact_fallback_explicit"
        ),
    }
