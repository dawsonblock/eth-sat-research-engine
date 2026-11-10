"""Structure-aware exact coefficient extraction (research prototype).

**Problem B:** recover A_β (and source column powers) for one exponent β at fixed
Boolean bits — what `evaluate_compiled` must preserve — without always building
the full exponent support.

**Problem A** (truncated aggregate) lives in `truncated_weighted_resummation`.

This module provides reference extractors and separator **cost estimates** only.
No general polynomial-time extractor is claimed; permanent-type barriers apply to
unrestricted inputs.

No ETH theorem or subexponential bound is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

from veritas.research.parent_child_r912.elimination import (
    EliminationBudget,
    plan_order,
    verify_order,
)
from veritas.research.parent_child_r913.algebraic_resummation import (
    Exponent,
    RowFactor,
    expand_packet_polynomial,
)
from veritas.research.parent_child_r913.dependency_analyzer import (
    mode_factor_graph_from_modes,
)
from veritas.research.tapered_v4.source_recipes import CompiledEntry

from .research_spec import PacketQuantityKind


@dataclass(frozen=True)
class ExtractionStateEstimate:
    """Symbolic separator cost sketch (not a treewidth certificate)."""

    target_beta: Exponent
    mode_count: int
    factor_rows: int
    elimination_width: int
    max_table_entries: int
    predicted_work: int
    boolean_separator_states: int
    exponent_tracking_multiplier: int
    qualification: str = "heuristic_mode_elimination_not_coefficient_extractor"


def target_coefficient_by_expansion(
    factors: Sequence[RowFactor],
    target_beta: Exponent,
    ar,
    *,
    max_monomials: int = 50_000,
):
    """Reference problem-B value: coefficient at ``target_beta`` from full expansion."""
    poly = expand_packet_polynomial(
        factors, ar, max_monomials=max_monomials, mode_count=len(target_beta)
    )
    return poly.get(target_beta, ar.ring.zero)


def estimate_extraction_state(
    modes: Sequence[dict],
    target_beta: Exponent,
    *,
    row_certificate: dict | None = None,
    budget: EliminationBudget | None = None,
    heuristic: str = "min_fill",
) -> ExtractionStateEstimate:
    """Upper-bound style estimate for separator DP on mode factor graph."""
    budget = EliminationBudget() if budget is None else budget
    graph = mode_factor_graph_from_modes(modes, row_certificate=row_certificate)
    order = plan_order(graph.scopes, graph.variables, heuristic)
    certificate = verify_order(graph.scopes, graph.variables, order, budget)
    max_exp = max(target_beta) if target_beta else 0
    exp_multiplier = max_exp + 1 if max_exp > 1 else 1
    bool_states = certificate["max_table_entries"]
    return ExtractionStateEstimate(
        target_beta=target_beta,
        mode_count=len(modes),
        factor_rows=len(graph.scopes),
        elimination_width=int(certificate["width"]),
        max_table_entries=int(certificate["max_table_entries"]),
        predicted_work=int(certificate["predicted_work"]),
        boolean_separator_states=bool_states,
        exponent_tracking_multiplier=exp_multiplier,
    )


def extraction_report(
    compiled: CompiledEntry,
    factors: Sequence[RowFactor],
    target_beta: Exponent,
    modes: Sequence[dict],
    *,
    row_certificate: dict | None = None,
) -> Dict[str, object]:
    """Compare quantity kinds for one packet (bounded diagnostics)."""
    estimate = estimate_extraction_state(
        modes, target_beta, row_certificate=row_certificate
    )
    return {
        "schema": "VERITAS_R913_COEFFICIENT_EXTRACTION_DIAG_V1",
        "quantity_kinds": [k.value for k in PacketQuantityKind],
        "target_beta": list(target_beta),
        "target_kind": PacketQuantityKind.TARGET_COEFFICIENT.value,
        "aggregate_kind": PacketQuantityKind.TRUNCATED_WEIGHTED_AGGREGATE.value,
        "state_estimate": {
            "elimination_width": estimate.elimination_width,
            "max_table_entries": estimate.max_table_entries,
            "boolean_separator_states": estimate.boolean_separator_states,
            "exponent_tracking_multiplier": estimate.exponent_tracking_multiplier,
            "effective_state_upper_bound": (
                estimate.boolean_separator_states * estimate.exponent_tracking_multiplier
            ),
            "predicted_work": estimate.predicted_work,
            "qualification": estimate.qualification,
        },
        "row_count": len(factors),
        "mode_count": len(modes),
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "separator_extractor_implemented": False,
    }
