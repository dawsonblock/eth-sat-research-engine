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
from veritas.research.sat_source_finite_lane import try_source_finite_count_lane
from veritas.research.sat_work_accounting import (
    DecompositionWorkLedger,
    aggregate_ledger,
    exponential_width_proxy,
    ledger_totals_summary,
)
from veritas.research.source_cnf import SourceCNFNetwork, source_cnf_network
from veritas.research.sat_count_invariants import collect_count_invariants
from veritas.research.sat_residual_equivalence import probe_residual_compression
from veritas.research.sat_cnf_parent_bridge import (
    DEFAULT_PARENT_BRIDGE_BOUNDS,
    ParentBridgeBounds,
    build_parent_call_from_encoded_cnf,
)
from veritas.research.sat_cross_checks import (
    combine_cross_check_agreement,
    cross_check_phase_c_vs_direct,
    cross_check_source_finite_vs_direct,
)
from veritas.research.sat_interaction_pins import (
    INTERACTION_96_PARENT_DIGEST,
    interaction_96_layout_and_budget,
    load_pinned_interaction_96_parent,
)
from veritas.research.sat_external_baselines import run_baseline_matrix
from veritas.research.sat_phase_c_r94_lane import run_phase_c_outer_reduction
from veritas.research.sat_phase_c_reduction import (
    DEFAULT_PHASE_C_BOUNDS,
    PhaseCBounds,
    phase_c_refusal_if_out_of_bounds,
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
    parent_bridge: dict[str, Any],
    w_old: int,
    jet_diagnostic_fixture: bool = False,
) -> tuple[dict[str, Any], DecompositionWorkLedger]:
    """E4: jet parent–child product only with cert + digest gate (or fixture diagnostic)."""
    bridge_digest = parent_bridge.get("content_digest")
    digest_match = bridge_digest == INTERACTION_96_PARENT_DIGEST
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
    elif not digest_match and not jet_diagnostic_fixture:
        detail = {
            "status": "REFUSED",
            "reason": "parent_digest_mismatch",
            "lane": "jet_parent_child_product",
            "bridge_digest": bridge_digest,
            "pinned_digest": INTERACTION_96_PARENT_DIGEST,
            "note": "Jet diagnostic allowed only when bridge matches pinned interaction parent.",
        }
    else:
        try:
            import time
            from veritas.research.parent_child_r913.fast_universal_solver import (
                fast_universal_parent_jet_solve,
            )

            t0 = time.perf_counter()
            parent = load_pinned_interaction_96_parent()
            layout, budget = interaction_96_layout_and_budget(parent)
            solved = fast_universal_parent_jet_solve(
                parent, layout, budget=budget, point_index=1
            )
            elapsed = time.perf_counter() - t0
            detail = {
                "status": "DIAGNOSTIC_FAST_JET_RAN",
                "lane": "jet_parent_child_product",
                "certificate": interaction_cert.to_dict(),
                "digest_gate": "match" if digest_match else "fixture_override",
                "reconstruction_equals_oracle": solved.reconstruction_equals_oracle,
                "child_group_count": solved.child_group_count,
                "elapsed_seconds": elapsed,
                "qualification": (
                    "interaction_fixture_only; does_not_answer_input_cnf; "
                    "not_universal_speedup"
                ),
            }
        except (ValueError, TypeError, OSError, RuntimeError, ArithmeticError) as exc:
            detail = {
                "status": "REFUSED",
                "reason": str(exc),
                "lane": "jet_parent_child_product",
                "digest_gate": "match" if digest_match else "fixture_override",
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
    parent_bridge_bounds: ParentBridgeBounds = DEFAULT_PARENT_BRIDGE_BOUNDS,
    include_baseline_matrix: bool = False,
    baseline_task: Literal["decision", "count"] | None = None,
    jet_diagnostic_fixture: bool = False,
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
            split_summary, phase_c_ledgers = run_phase_c_outer_reduction(
                cnf,
                encoded,
                bounds=phase_c_bounds,
                w_old=w_old,
                task="count" if mode is UniversalSatMode.COUNT else "decision",
            )
            ledgers.extend(phase_c_ledgers)
            phase_c_summary = split_summary
        except ValueError as exc:
            phase_c_summary = {
                "schema": "VERITAS_PHASE_C_STAGE_V1",
                "status": "REFUSED",
                "reason": str(exc),
            }
    reduction_summary["phase_c_split"] = phase_c_summary

    if mode is UniversalSatMode.COUNT:
        compression_probe = probe_residual_compression(
            cnf,
            max_vars=phase_c_bounds.max_residual_equivalence_vars,
            max_clauses=phase_c_bounds.max_residual_equivalence_clauses,
        )
        reduction_summary["residual_compression"] = compression_probe
        if compression_probe.get("status") == "EXACT_COUNT":
            ledgers.append(
                DecompositionWorkLedger(
                    name="residual_compression_probe",
                    w_old=w_old,
                    w_transform=int(
                        compression_probe.get("distinct_residual_classes") or 1
                    ),
                    child_works=(),
                    w_reconstruct=0,
                    w_check=1,
                    metadata={
                        "phase": "residual_compression",
                        "compression_ratio": compression_probe.get(
                            "compression_ratio_branches_over_classes"
                        ),
                    },
                )
            )
    else:
        reduction_summary["residual_compression"] = {
            "schema": "VERITAS_RESIDUAL_COMPRESSION_PROBE_V1",
            "status": "SKIPPED",
            "reason": "decision_mode",
        }

    source_finite_detail: dict[str, Any] = {
        "schema": "VERITAS_SOURCE_FINITE_COUNT_LANE_V1",
        "status": "SKIPPED",
        "reason": "not_count_mode",
    }
    if encoded is not None and (reduction_summary.get("structural_check") or {}).get("valid"):
        bridge = build_parent_call_from_encoded_cnf(
            cnf, encoded, bounds=parent_bridge_bounds
        )
        reduction_summary["parent_call_bridge"] = bridge
        w_bridge = int(bridge.get("edge_count") or bridge.get("original_edges") or 1)
        ledgers.append(
            DecompositionWorkLedger(
                name="parent_call_bridge",
                w_old=w_old,
                w_transform=w_bridge,
                child_works=(),
                w_reconstruct=0,
                w_check=1,
                metadata={"phase": "parent_bridge", "status": bridge.get("status")},
            )
        )
        if mode is UniversalSatMode.COUNT:
            source_finite_detail, src_ledger = try_source_finite_count_lane(
                cnf, w_old=w_old
            )
            if src_ledger is not None:
                ledgers.append(src_ledger)
        reduction_summary["source_finite_count"] = source_finite_detail
    else:
        reduction_summary["parent_call_bridge"] = {
            "schema": "VERITAS_CNF_PARENT_BRIDGE_V1",
            "status": "SKIPPED",
            "reason": "encode_or_check_incomplete",
        }
        reduction_summary["source_finite_count"] = source_finite_detail

    parent_bridge_snapshot = reduction_summary.get("parent_call_bridge") or {}
    jet_detail, jet_ledger = attempt_jet_fast_path(
        interaction_cert=interaction_cert,
        parent_bridge=parent_bridge_snapshot,
        w_old=w_old,
        jet_diagnostic_fixture=jet_diagnostic_fixture,
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

    cross_detail, cross_ledger = cross_check_phase_c_vs_direct(
        mode=mode.value,
        phase_c_split=phase_c_summary,
        direct_result=solve_out,
        w_old=w_old,
    )
    if cross_ledger is not None:
        ledgers.append(cross_ledger)

    source_cross_detail, source_cross_ledger = cross_check_source_finite_vs_direct(
        source_finite=source_finite_detail,
        direct_result=solve_out,
        w_old=w_old,
    )
    if source_cross_ledger is not None:
        ledgers.append(source_cross_ledger)

    combined_agreement = combine_cross_check_agreement(
        cross_detail, source_cross_detail
    )

    ledger_json = aggregate_ledger(ledgers)
    totals = ledger_totals_summary(ledger_json)

    baseline_matrix = None
    if include_baseline_matrix:
        task = baseline_task or mode.value
        baseline_matrix = run_baseline_matrix(cnf, task=task, include_external=True)

    count_invariants = collect_count_invariants(reduction_summary)

    return {
        "schema": "VERITAS_SAT_UNIVERSAL_RUN_V1",
        "count_invariants": count_invariants,
        "mode": mode.value,
        "formula_sha256": cnf.digest(),
        "n": cnf.n,
        "clause_count": len(cnf.clauses),
        "reduction": reduction_summary,
        "jet_fast_path": jet_detail,
        "result": solve_out,
        "cross_checks": {
            "schema": "VERITAS_SAT_CROSS_CHECKS_V1",
            "phase_c_vs_direct": cross_detail,
            "source_finite_vs_direct": source_cross_detail,
            "agreement": combined_agreement,
        },
        "decomposition_work": ledger_json,
        "ledger_totals": totals,
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
