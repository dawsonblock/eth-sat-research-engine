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
from veritas.research.parent_child_r912.interaction_jet_point import packet_modes_at_jet_point
from veritas.research.parent_child_r912.routes import Route, contract_routed
from veritas.research.parent_child_r913.algebraic_resummation import RowFactor
from veritas.research.parent_child_r913.coefficient_extraction import (
    estimate_extraction_state,
    target_coefficient_by_separator_elimination,
)
from veritas.research.parent_child_r98.model import Budget, PacketLayout, ParentCall
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
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


def interaction_coefficient_end_to_end(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    shrink_budget: Budget | None = None,
    elimination_budget: EliminationBudget | None = None,
    point_index: int = 1,
    target_beta: Tuple[int, ...] | None = None,
    include_wire_elimination: bool = False,
) -> Dict[str, object]:
    """Run fast parent-child solve plus separator child coefficient; wire elimination optional."""
    elimination_budget = elimination_budget or EliminationBudget(max_width=20)
    shrink_budget = shrink_budget or Budget(
        replace(DEFAULT_SHRINKING_POLICY, max_work=8_000_000, max_edges=128, max_precision=16384)
    )

    parent_report: Dict[str, object]
    parent_elapsed: float
    t_parent = time.perf_counter()
    if include_wire_elimination:
        parent_report = contract_routed(
            parent,
            route=Route.ELIMINATION,
            elimination_budget=elimination_budget,
        )
        parent_elapsed = time.perf_counter() - t_parent
    else:
        parent_report = {
            "status": "SKIPPED_FAST_UNIVERSAL_SOLVER",
            "elimination_width": None,
            "result": None,
            "reason": "wire elimination omitted; use fast_universal_parent_jet_solve",
        }
        parent_elapsed = 0.0

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

    parent_ok = (
        include_wire_elimination
        and parent_report.get("status") == "PASS_EXACT_BOUNDED_WIDTH_ELIMINATION"
    )
    matches_reference = extracted.value == reference
    rows_one_mode = all(len(v) == 1 for v in incidence.values())

    from veritas.research.parent_child_r913.coefficient_reconstruction import (
        ParentChildReconstructionResult,
        wire_elimination_vs_parent_coefficient,
    )
    from veritas.research.parent_child_r913.fast_universal_solver import (
        fast_universal_parent_jet_solve,
    )

    t_reconstruct = time.perf_counter()
    universal = fast_universal_parent_jet_solve(
        parent,
        layout,
        budget=shrink_budget,
        point_index=point_index,
        beta_values=tuple(0 for _ in range(mode_count)),
    )
    reconstruct_elapsed = time.perf_counter() - t_reconstruct
    parent_child_block = {
        "schema": "VERITAS_R913_PARENT_CHILD_RECONSTRUCT_V1",
        "active_levels": 1,
        "beta": list(universal.beta),
        "child_group_count": universal.child_group_count,
        "reconstruction_equals_oracle": universal.reconstruction_equals_oracle,
        "parent_child_reconstruction_proved": universal.reconstruction_equals_oracle,
        "elapsed_seconds": reconstruct_elapsed,
        "solver_method": universal.method.value,
        "qualification": universal.qualification,
    }

    proved = universal.reconstruction_equals_oracle

    recon_for_wire = ParentChildReconstructionResult(
        schema="VERITAS_R913_PARENT_CHILD_RECONSTRUCT_V1",
        active_levels=1,
        beta=universal.beta,
        child_group_count=universal.child_group_count,
        child_values=(),
        reconstructed=universal.reconstructed,
        parent_oracle=universal.parent_oracle,
        reconstruction_equals_oracle=universal.reconstruction_equals_oracle,
        qualification=universal.qualification,
    )
    if include_wire_elimination:
        wire_vs_coeff = wire_elimination_vs_parent_coefficient(
            parent,
            layout,
            budget=shrink_budget,
            elimination_budget=elimination_budget,
            point_index=point_index,
            beta_values=tuple(0 for _ in range(mode_count)),
            reconstruction=recon_for_wire,
        )
    else:
        wire_vs_coeff = {
            "schema": "VERITAS_R913_WIRE_VS_DEFORMATION_COEFF_V1",
            "wire_elimination_status": parent_report.get("status"),
            "wire_elimination_equals_parent_coefficient": False,
            "reconstruction_equals_oracle": universal.reconstruction_equals_oracle,
            "qualification": "wire elimination skipped; fast universal parent-child product",
        }

    wire_result = parent_report.get("result")
    wire_low = None
    if wire_result is not None:
        try:
            wire_low = wire_result[0][0]
        except (TypeError, IndexError, KeyError):
            wire_low = None

    return {
        "schema": "VERITAS_R912_INTERACTION_PARALLEL_DIAG_V2",
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
            "result_low_word": wire_low,
            "matches_budget": parent_ok,
        },
        "fast_universal_solver": {
            "method": parent_child_block.get("solver_method"),
            "elapsed_seconds": reconstruct_elapsed,
            "reconstruction_equals_oracle": proved,
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
        "parent_child_reconstruction": parent_child_block,
        "wire_vs_parent_coefficient": wire_vs_coeff,
        "qualification": (
            "parent_wire_elimination_and_independent_row_A_beta_remain_parallel_diagnostics; "
            "C_parent_beta_from_constructor_children_proved_at_jet_point"
            if proved
            else (
                "parent wire elimination and row-product A_beta are parallel; "
                "parent-to-child product reconstruction not established"
            )
        ),
        "parent_child_reconstruction_proved": proved,
        "wire_elimination_equals_C_parent_beta": False,
    }
