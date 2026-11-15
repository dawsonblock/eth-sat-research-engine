"""Phase C R9.4 research lane (partial — not the arbitrary-density theorem).

Chains:
1. Fixed-density / COPY3 ``source_cnf_network`` encode (structural bijection scaffold).
2. Primal component split with a checkable **product** count invariant when components
   partition declared variables and every clause is component-local.

Sparsification, parity tests, and uniform (q, rho) for all 3-CNF remain open;
see ``docs/R9_2_R9_4_PROOF_OBLIGATIONS.md``.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from veritas.core.cnf import CNF
from veritas.research.bounded_degree import describe_network
from veritas.research.sat_phase_c_preprocess import apply_phase_c_preprocess
from veritas.research.sat_phase_c_reduction import (
    DEFAULT_PHASE_C_BOUNDS,
    PhaseCBounds,
    _cnf_primal_graph,
    plan_primal_component_split,
)
from veritas.research.graph_decomposition import components
from veritas.research.sat_work_accounting import DecompositionWorkLedger
from veritas.research.source_cnf import SourceCNFNetwork

COUNT_INVARIANT_PRODUCT = "PRODUCT_OVER_PRIMAL_COMPONENTS"
COPY3_BIJECTION = "STRUCTURAL_BIJECTION_COPY3"


def primal_component_partition_certificate(cnf: CNF) -> dict[str, Any]:
    """Check prerequisites for #SAT(F) = prod_i #SAT(F_i) on primal components."""
    if any(not clause for clause in cnf.clauses):
        return {
            "schema": "VERITAS_PRIMAL_PARTITION_CERT_V1",
            "valid": False,
            "reason": "empty_clause_unsat",
        }
    graph = _cnf_primal_graph(cnf)
    comps = components(graph)
    comp_by_var: dict[int, frozenset[int]] = {}
    for comp in comps:
        fs = frozenset(comp)
        for v in comp:
            if v in comp_by_var:
                return {
                    "schema": "VERITAS_PRIMAL_PARTITION_CERT_V1",
                    "valid": False,
                    "reason": "duplicate_variable_in_components",
                }
            comp_by_var[v] = fs

    expected = set(range(1, cnf.n + 1))
    if set(comp_by_var) != expected:
        missing = sorted(expected - set(comp_by_var))
        extra = sorted(set(comp_by_var) - expected)
        return {
            "schema": "VERITAS_PRIMAL_PARTITION_CERT_V1",
            "valid": False,
            "reason": "variables_not_partitioned",
            "missing_variables": missing,
            "unexpected_variables": extra,
        }

    for clause_index, clause in enumerate(cnf.clauses):
        vars_in_clause = {abs(lit) for lit in clause}
        if not vars_in_clause:
            continue
        comp_ids = {comp_by_var[v] for v in vars_in_clause}
        if len(comp_ids) != 1:
            return {
                "schema": "VERITAS_PRIMAL_PARTITION_CERT_V1",
                "valid": False,
                "reason": "clause_spans_components",
                "clause_index": clause_index,
            }

    return {
        "schema": "VERITAS_PRIMAL_PARTITION_CERT_V1",
        "valid": True,
        "q": len(comps),
        "components": [list(c) for c in comps],
        "count_invariant": COUNT_INVARIANT_PRODUCT,
        "qualification": (
            "Primal-graph connected components partition declared variables; "
            "each clause is internal to one component; isolated variables are "
            "own components with factor 2 each."
        ),
    }


def describe_copy3_encode_stage(
    cnf: CNF,
    encoded: SourceCNFNetwork,
    *,
    bounds: PhaseCBounds,
) -> dict[str, Any]:
    """Metadata for the bounded-degree / source encode step (within caps)."""
    describe = describe_network(
        encoded.normalized_cnf,
        max_clause_width=8,
        max_wires=bounds.max_encoded_edges,
        max_factors=bounds.max_encoded_factors,
    )
    return {
        "schema": "VERITAS_PHASE_C_ENCODE_STAGE_V1",
        "status": "ENCODED_WITHIN_CAPS",
        "count_preservation": describe.get("count_preservation", COPY3_BIJECTION),
        "method": "source_cnf_network_via_bounded_degree_copy3",
        "formula_digest": cnf.digest(),
        "normalized_digest": encoded.formula_digest,
        "original_edges": encoded.original_edges,
        "unused_variables": list(encoded.unused_variables),
        "dropped_tautologies": list(encoded.dropped_tautologies),
        "network_edges": encoded.network.edges,
        "network_factors": len(encoded.network.factors),
        "arbitrary_density_theorem": False,
        "qualification": "count_preserving_COPY3_on_normalized_cnf_within_resource_caps",
        "bounded_degree_stats": {
            k: describe[k]
            for k in (
                "n_variables",
                "n_clauses",
                "resulting_wires",
                "resulting_factors",
                "maximum_variable_occurrences",
                "maximum_factor_degree",
            )
            if k in describe
        },
    }


def r94_obligation_snapshot(*, partition_valid: bool, encode_ok: bool) -> dict[str, Any]:
    return {
        "schema": "VERITAS_R94_OBLIGATION_SNAPSHOT_V1",
        "outer_reduction": (
            "PARTIAL_COPY3_ENCODE_PLUS_PRIMAL_PRODUCT"
            if (encode_ok and partition_valid)
            else "SCAFFOLD_ONLY"
        ),
        "count_preserving_arbitrary_density": False,
        "sparsification_parity_stages": "NOT_IMPLEMENTED",
        "uniform_q_rho_theorem": False,
        "bit_time_peak_memory": "COMPLEXITY_NOT_ESTABLISHED",
        "reference": "docs/R9_2_R9_4_PROOF_OBLIGATIONS.md",
    }


def run_phase_c_outer_reduction(
    cnf: CNF,
    encoded: SourceCNFNetwork,
    *,
    bounds: PhaseCBounds = DEFAULT_PHASE_C_BOUNDS,
    w_old: int,
    task: Literal["count", "decision"] = "count",
) -> tuple[dict[str, Any], tuple[DecompositionWorkLedger, ...]]:
    """Preprocess + encode metadata + primal split with count-invariant certificate."""
    ledgers: list[DecompositionWorkLedger] = []
    _work_cnf, preprocess_detail, preprocess_ledger = apply_phase_c_preprocess(
        cnf, w_old=w_old
    )
    ledgers.append(preprocess_ledger)
    if preprocess_detail.get("status") == "UNSAT":
        detail = {
            **preprocess_detail,
            "schema": "VERITAS_PHASE_C_OUTER_REDUCTION_V1",
            "status": "REFUSED_UNSAT_AFTER_PREPROCESS",
            "recombined": {"count": 0, "rule": "preprocess_unsat"},
            "task": task,
            "theorem_backed": False,
        }
        return detail, tuple(ledgers)
    partition_cert = primal_component_partition_certificate(cnf)
    encode_stage = describe_copy3_encode_stage(cnf, encoded, bounds=bounds)

    split_summary, split_ledger = plan_primal_component_split(
        cnf,
        encoded,
        bounds=bounds,
        w_old=w_old,
        task=task,
        partition_certificate=partition_cert,
    )
    if split_ledger is not None:
        ledgers.append(split_ledger)
    ledger = split_ledger

    count_invariant: dict[str, Any] | None = None
    if partition_cert.get("valid") and task == "count":
        count_invariant = {
            "type": COUNT_INVARIANT_PRODUCT,
            "proved_in_repo": False,
            "partition_certificate_valid": True,
            "certificate": partition_cert,
            "note": (
                "Primal component product rule when certificate valid; "
                "not R9.4 theorem or arbitrary-density outer reduction."
            ),
        }

    summary: dict[str, Any] = {
        **split_summary,
        "schema": "VERITAS_PHASE_C_OUTER_REDUCTION_V1",
        "preprocess": preprocess_detail,
        "stages": [
            preprocess_detail,
            encode_stage,
            {
                "schema": "VERITAS_PHASE_C_SPLIT_STAGE_V1",
                "status": split_summary.get("status"),
                "q": split_summary.get("q"),
            },
        ],
        "partition_certificate": partition_cert,
        "count_invariant": count_invariant,
        "r94_obligations": r94_obligation_snapshot(
            partition_valid=bool(partition_cert.get("valid")),
            encode_ok=encode_stage.get("status") == "ENCODED_WITHIN_CAPS",
        ),
        "outer_reduction_r94": (
            "PARTIAL_IMPLEMENTATION" if partition_cert.get("valid") else "SCAFFOLD_ONLY"
        ),
    }
    if ledger is not None:
        ledger.metadata["outer_reduction_r94"] = summary["outer_reduction_r94"]
        ledger.metadata["partition_certificate_valid"] = partition_cert.get("valid")
        ledger.metadata["preprocess_status"] = preprocess_detail.get("status")
    split_w_new = split_summary.get("w_new_proxy")
    split_speedup = split_summary.get("speedup_ratio_proxy")
    summary["decomposition_metrics"] = {
        "schema": "VERITAS_PHASE_C_DECOMP_METRICS_V1",
        "w_old_proxy": w_old,
        "w_new_proxy_split": split_w_new,
        "speedup_ratio_split_proxy": split_speedup,
        "phase_c_q": split_summary.get("q"),
        "w_beats_direct_proxy": (
            split_speedup is not None and split_speedup > 1.0
        ),
        "qualification": "proxy_only_not_theorem",
    }
    return summary, tuple(ledgers)
