"""Circulant interaction fixture: parent wire elimination vs child coefficient path.

Compares problem **B** (target coefficient via separator elimination on row
factors built from ``build_packet_modes``) against:

1. **Wire elimination reference** on the parent (production exact contraction).
2. **Independent row closed form** when each affine row touches one mode.

No ETH / subexponential / source-qualification claim. Parent contraction value
and child packet coefficient are **different** quantities; both are reported.
"""
from __future__ import annotations

import time
from dataclasses import replace
from typing import Dict, List, Sequence, Tuple

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r912.jet_recovery import JetRecovery
from veritas.research.parent_child_r912.routes import Route, contract_routed
from veritas.research.parent_child_r913.algebraic_resummation import RowFactor
from veritas.research.parent_child_r913.coefficient_extraction import (
    estimate_extraction_state,
    target_coefficient_by_separator_elimination,
)
from veritas.research.parent_child_r98.model import Budget, PacketLayout, ParentCall
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r99.support_circuit import SupportCircuit, affine_incidence
from veritas.research.tapered_v4.source_recipes import Arithmetic, EntryBudget, EntryLimits


def row_factors_from_mode_certificate(
    modes: Sequence[dict],
    ar: Arithmetic,
    *,
    row_certificate: dict | None = None,
) -> Tuple[RowFactor, ...]:
    """Build row product factors from a ``build_packet_modes`` certificate (no child ctor)."""
    incidence = affine_incidence(modes, row_certificate)
    mode_count = len(modes)
    zero = ar.ring.zero
    one = ar.ring.one
    factors: List[RowFactor] = []
    for packet, row in sorted(incidence):
        mode_row: List[object] = [zero] * mode_count
        for mid in incidence[(packet, row)]:
            mode = modes[mid]
            for port, coeff in mode["rows"]:
                if port != row or mode["packet"] != packet:
                    continue
                if coeff is None:
                    mode_row[mid] = one
                else:
                    mode_row[mid] = ar.ring.elem(coeff)
        factors.append(RowFactor(one, tuple(mode_row)))
    return tuple(factors)


def independent_row_product_reference(
    factors: Sequence[RowFactor],
    target_beta: Tuple[int, ...],
    ar: Arithmetic,
) -> object:
    """Exact A_beta when each row has at most one active mode (interaction shape)."""
    zero = ar.ring.zero
    total = ar.ring.one
    for factor in factors:
        active = [
            mid
            for mid, coeff in enumerate(factor.mode_coefficients)
            if coeff != zero
        ]
        if len(active) > 1:
            raise ValueError("independent reference requires ≤1 active mode per row")
        if not active:
            if any(target_beta):
                return zero
            total = ar.mul(total, factor.constant)
            continue
        mid = active[0]
        need = target_beta[mid]
        if need == 0:
            total = ar.mul(total, factor.constant)
        elif need == 1:
            total = ar.mul(total, factor.mode_coefficients[mid])
        else:
            return zero
    return total


def packet_modes_at_jet_point(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    max_points: int | None = None,
) -> Tuple[dict, dict, int, Tuple[int, ...], Tuple[int, ...]]:
    """Return modes certificate, row certificate, jet index, node, zeta."""
    row_certificate = certify_row_degree(parent, layout.a, budget=budget)
    if max_points is None:
        degree_cap = int(row_certificate["degree_bound"]) + 1
        max_points = min(4096, max(256, degree_cap))
    recovery = JetRecovery(
        parent,
        layout,
        row_certificate,
        budget=budget,
        max_points=max_points,
    )
    for index, (node, zeta, _residue) in enumerate(recovery.points()):
        if index != point_index:
            continue
        modes = build_packet_modes(
            parent,
            layout,
            node,
            zeta,
            budget=budget,
            row_certificate=row_certificate,
        )
        return modes.certificate, row_certificate, index, node, tuple(zeta)
    raise ValueError("jet recovery produced no point at the requested index")


def interaction_coefficient_end_to_end(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    shrink_budget: Budget | None = None,
    elimination_budget: EliminationBudget | None = None,
    point_index: int = 1,
    target_beta: Tuple[int, ...] | None = None,
) -> Dict[str, object]:
    """Run wire elimination + separator child coefficient with explicit telemetry."""
    elimination_budget = elimination_budget or EliminationBudget(max_width=20)
    shrink_budget = shrink_budget or Budget(
        replace(DEFAULT_SHRINKING_POLICY, max_work=8_000_000, max_edges=128, max_precision=16384)
    )

    t_parent = time.perf_counter()
    parent_report = contract_routed(
        parent,
        route=Route.ELIMINATION,
        elimination_budget=elimination_budget,
    )
    parent_elapsed = time.perf_counter() - t_parent

    modes_certificate, row_certificate, jet_index, jet_node, zeta = packet_modes_at_jet_point(
        parent,
        layout,
        budget=shrink_budget,
        point_index=point_index,
    )
    modes = modes_certificate["modes"]
    precision = int(modes_certificate["precision"])
    mode_count = len(modes)
    if target_beta is None:
        target_beta = tuple(1 for _ in range(mode_count))

    limits = EntryLimits(max_work=10_000_000, max_precision_bits=max(precision, parent.precision))
    entry_budget = EntryBudget(limits)
    degree = parent.defining_polynomial.bit_length() - 1
    ring = JetRing(
        ExtensionRing(precision, parent.defining_polynomial, max_precision_bits=limits.max_precision_bits),
        parent.jet_length,
    )
    ar = Arithmetic(ring, entry_budget)

    t_child = time.perf_counter()
    factors = row_factors_from_mode_certificate(modes, ar, row_certificate=row_certificate)
    incidence = affine_incidence(modes, row_certificate)
    circuit = SupportCircuit(
        modes,
        precision,
        budget=shrink_budget,
        row_certificate=row_certificate,
    )
    state_estimate = estimate_extraction_state(
        modes,
        target_beta,
        row_certificate=row_certificate,
        budget=elimination_budget,
    )
    extracted = target_coefficient_by_separator_elimination(
        factors,
        target_beta,
        ar,
        budget=elimination_budget,
    )
    reference = independent_row_product_reference(factors, target_beta, ar)
    child_elapsed = time.perf_counter() - t_child

    parent_ok = parent_report.get("status") == "PASS_EXACT_BOUNDED_WIDTH_ELIMINATION"
    matches_reference = extracted.value == reference
    rows_one_mode = all(len(v) == 1 for v in incidence.values())

    return {
        "schema": "VERITAS_R912_INTERACTION_COEFFICIENT_E2E_V1",
        "wires": parent.edge_count,
        "jet_point_index": jet_index,
        "jet_node": jet_node,
        "mode_count": mode_count,
        "packet_precision": precision,
        "target_beta_ones": sum(target_beta),
        "parent_wire_elimination": {
            "status": parent_report.get("status"),
            "elimination_width": parent_report.get("elimination_width"),
            "elapsed_seconds": parent_elapsed,
            "result_low_word": parent_report.get("result", [[None]])[0][0],
            "matches_budget": parent_ok,
        },
        "child_target_coefficient": {
            "separator_agrees_with_independent_reference": matches_reference,
            "independent_row_shape": rows_one_mode,
            "support_circuit_components": circuit.summary()["components"],
            "largest_local_support": circuit.summary()["largest_local_support"],
            "separator_max_monomial_table": extracted.stats.max_monomial_table,
            "separator_join_count": extracted.stats.join_count,
            "separator_elimination_width": extracted.stats.elimination_width,
            "mode_graph_elimination_width": state_estimate.elimination_width,
            "effective_state_upper_bound": (
                state_estimate.boolean_separator_states
                * state_estimate.exponent_tracking_multiplier
            ),
            "entry_work_units": entry_budget.used,
            "elapsed_seconds": child_elapsed,
        },
        "resource_budget": {
            "elimination_budget": elimination_budget.record(),
            "shrink_max_work": shrink_budget.policy.max_work,
            "entry_limits_max_work": limits.max_work,
        },
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "qualification": (
            "parent_contraction_and_child_A_beta_are_different_quantities; "
            "reference_is_independent_row_product_not_parent_integer"
        ),
    }
