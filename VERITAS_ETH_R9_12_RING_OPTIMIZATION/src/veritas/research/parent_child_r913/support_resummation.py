"""Support-aware packet resummation experiments (bounded fixtures only).

Compares three values at fixed Boolean row bits and mode weights ``s``:

1. **enumerated_supported** — expand ``P(z)``, keep monomials whose exponent
   lies in the affine-row support (same incidence rule as ``build_support``),
   then apply ``Σ_β A_β Π s^β``.
2. **full_substitution** — ``∏_r (c_r + Σ_j a_{rj} s_j)`` (no support cut).
3. **hybrid_component** — when ``SupportCircuit`` splits into disjoint mode
   components, apply substitution on each component's rows and multiply; this
   matches (1) for independent components but is not certified globally.

Conditions not proved (same caveats as ``algebraic_resummation``)
-----------------------------------------------------------------
- Support is the R9.99/R9.12 affine-row support with a weight cutoff; it does
  not re-prove packet recipe semantics or child shrink obligations.
- Component hybrid is exact only when components act on disjoint coordinates;
  shared rows make (1) the reference cross-check.
- No ETH, subexponential, or source-qualification claim follows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r99.support_circuit import SupportCircuit, affine_incidence
from veritas.research.tapered_v4.source_recipes import CompiledEntry, EntryBudget, EntryLimits

from .algebraic_resummation import (
    Exponent,
    PacketPoly,
    RowFactor,
    _jet_ring_and_arithmetic,
    _packet_row_factors,
    expand_packet_polynomial,
    explicit_monomial_resummation,
    substitution_resummation,
)

ModeWeights = Tuple[int, ...]


@dataclass(frozen=True)
class SupportResummationResult:
    """Comparison of support-filtered, full, and component-hybrid resummation."""

    enumerated_supported: object
    full_substitution: object
    hybrid_component: object
    supported_monomial_count: int
    total_monomial_count: int
    support_tuple_count: int
    component_count: int
    enumerate_agrees_with_hybrid: bool
    full_agrees_with_enumerated: bool
    precision: int


def _target_weights(compiled: CompiledEntry) -> ModeWeights:
    rows, _cols, _local, targets, _sources = compiled.data
    selected = [(beta, coeffs) for beta, coeffs in targets if beta]
    return tuple(int(beta) for beta, _ in selected)


def modes_from_packet_rows(
    factors: Sequence[RowFactor],
    weights: ModeWeights,
    *,
    zero,
    packet: int = 0,
) -> List[dict]:
    """R9.99-style mode list from row factors (constructor path, not sampling)."""
    modes: List[dict] = []
    for mid, weight in enumerate(weights):
        active_rows = [
            row
            for row, factor in enumerate(factors)
            if mid < len(factor.mode_coefficients)
            and factor.mode_coefficients[mid] != zero
        ]
        modes.append(
            {
                "packet": packet,
                "weight": int(weight),
                "rows": [[row, None] for row in active_rows],
            }
        )
    return modes


def filter_polynomial_by_support(
    poly: PacketPoly,
    circuit: SupportCircuit,
) -> PacketPoly:
    """Drop monomials outside the affine-row support representation."""
    filtered: PacketPoly = {}
    for beta, coeff in poly.items():
        if circuit.contains(beta):
            filtered[beta] = coeff
    return filtered


def _rows_for_coordinates(
    factors: Sequence[RowFactor],
    coordinates: Sequence[int],
    weights: ModeWeights,
    zero,
) -> Tuple[RowFactor, ...]:
    """Restrict factors to rows touching the given mode indices."""
    subset = set(coordinates)
    restricted: List[RowFactor] = []
    local_weights = list(weights)
    for row_index, factor in enumerate(factors):
        touches = any(
            j < len(factor.mode_coefficients)
            and factor.mode_coefficients[j] != zero
            and j in subset
            for j in range(len(local_weights))
        )
        if not touches:
            continue
        mode_row = []
        for j in range(len(local_weights)):
            if j in subset and j < len(factor.mode_coefficients):
                mode_row.append(factor.mode_coefficients[j])
            else:
                mode_row.append(zero)
        restricted.append(RowFactor(factor.constant, tuple(mode_row)))
    return tuple(restricted)


def hybrid_component_substitution(
    factors: Sequence[RowFactor],
    weights: Sequence[object],
    circuit: SupportCircuit,
    ar,
    *,
    zero,
) -> object:
    """Multiply per-component substitution values on disjoint coordinates."""
    if not factors:
        return ar.ring.one
    product = ar.ring.one
    for coordinates, _nodes, _local in circuit.components:
        sub_factors = _rows_for_coordinates(
            factors,
            coordinates,
            tuple(range(len(weights))),
            zero,
        )
        if not sub_factors:
            continue
        sub_weights = tuple(weights[j] for j in coordinates)
        product = ar.mul(
            product,
            substitution_resummation(sub_factors, sub_weights, ar),
        )
    return product


def compare_support_aware_resummation(
    compiled: CompiledEntry,
    bits: Tuple[int, ...],
    weights: Sequence[object],
    *,
    precision: int | None = None,
    limits: EntryLimits = EntryLimits(),
    row_certificate: dict | None = None,
) -> SupportResummationResult:
    """Compare supported enumeration, full substitution, and component hybrid."""
    budget_ring = EntryBudget(limits)
    _ring, ar = _jet_ring_and_arithmetic(compiled, budget_ring)
    factors = _packet_row_factors(compiled, bits, ar)
    mode_weights = _target_weights(compiled)
    if len(weights) != len(mode_weights):
        raise ValueError("weight vector length mismatch")
    if precision is None:
        precision = max(sum(mode_weights), max(mode_weights, default=0)) + len(mode_weights)

    modes = modes_from_packet_rows(factors, mode_weights, zero=ar.ring.zero)
    circuit = SupportCircuit(
        modes,
        precision,
        budget=Budget(),
        row_certificate=row_certificate,
    )
    poly = expand_packet_polynomial(factors, ar)
    supported_poly = filter_polynomial_by_support(poly, circuit)

    enumerated = explicit_monomial_resummation(supported_poly, weights, ar)
    full = substitution_resummation(factors, weights, ar)
    hybrid = hybrid_component_substitution(
        factors, weights, circuit, ar, zero=ar.ring.zero
    )

    return SupportResummationResult(
        enumerated_supported=enumerated,
        full_substitution=full,
        hybrid_component=hybrid,
        supported_monomial_count=len(supported_poly),
        total_monomial_count=len(poly),
        support_tuple_count=circuit.count(),
        component_count=len(circuit.components),
        enumerate_agrees_with_hybrid=enumerated == hybrid,
        full_agrees_with_enumerated=full == enumerated,
        precision=precision,
    )


def support_condition_report(result: SupportResummationResult) -> Dict[str, object]:
    """Human-readable status block for tests and logs."""
    return {
        "schema": "VERITAS_R913_SUPPORT_RESUMMATION_V1",
        "supported_monomials": result.supported_monomial_count,
        "total_monomials": result.total_monomial_count,
        "support_tuples": result.support_tuple_count,
        "components": result.component_count,
        "precision": result.precision,
        "enumerate_agrees_with_hybrid": result.enumerate_agrees_with_hybrid,
        "full_agrees_with_enumerated": result.full_agrees_with_enumerated,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "qualification": "experimental_support_filter_only",
    }
