"""Experimental algebraic resummation for tapered packet source recipes.

Verified identity (finite exact arithmetic, bounded mode/row caps)
--------------------------------------------------------------------
Fix Boolean port bits and compile a ``packet`` recipe.  For each row *r* the
streaming evaluator exposes one affine row factor

    F_r(z) = c_r + sum_j a_{rj} z_j

where ``z_j`` is a formal indeterminate for target mode *j* (modes with positive
recipe exponent only) and ``c_r``, ``a_{rj}`` are creation-precision jets.
Define the row product generating function

    P(z) = prod_r F_r(z).

On commutative jet arithmetic, multilinear expansion gives

    P(z) = sum_{beta} A_beta prod_j z_j^{beta_j},

and substitution at mode weights ``s = (s_1, ..., s_m)`` satisfies

    sum_beta A_beta prod_j s_j^{beta_j}  =  prod_r (c_r + sum_j a_{rj} s_j).

This module computes the left-hand side by explicit monomial accumulation and
the right-hand side by direct factor substitution, then compares them.

Production ``evaluate_compiled`` returns the single coefficient ``A_beta`` at the
recipe's declared exponent vector ``beta`` (times source-column power factors),
not the full resummed sum.  Tests cross-check that coefficient against the
polynomial oracle and that resummation agrees with substitution.

Conditions not proved here (full VERITAS R9.12)
-----------------------------------------------
- Support set ``S``: only exponents realizable by one mode per row are retained;
  tensor reconnection and contracted parent support can delete monomials.
- Precision: coefficients are exact in ``(Z/2^p Z)[U]/(f(U))[V]/(V^ell)`` at
  creation precision ``p``; lifting to larger ``p`` or recursive children is not
  certified by these experiments.
- Source modes: column power factors are applied after the target polynomial;
  overlapping row/column ports are rejected at recipe compile time.

This is an **experimental** reference only.  No ETH theorem, subexponential
bound, or active recursion qualification is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.tapered_v4.source_recipes import (
    Arithmetic,
    CompiledEntry,
    EntryBudget,
    EntryLimits,
    compile_entry,
    evaluate_compiled,
    make_reference,
)

Exponent = Tuple[int, ...]
PacketPoly = Dict[Exponent, object]


@dataclass(frozen=True)
class RowFactor:
    """Affine jet factor for one packet row at fixed Boolean bits."""

    constant: object
    mode_coefficients: Tuple[object, ...]


@dataclass(frozen=True)
class ResummationResult:
    """Comparison of explicit monomial sum against factor substitution."""

    explicit_sum: object
    substitution_value: object
    agree: bool
    monomial_count: int
    row_count: int
    mode_count: int


def _jet_ring_and_arithmetic(entry: CompiledEntry, budget: EntryBudget):
    ref = entry.reference
    ring = JetRing(
        ExtensionRing(
            ref.creation_precision,
            ref.defining_polynomial,
            max_precision_bits=budget.limits.max_precision_bits,
        ),
        ref.jet_length,
    )
    return ring, Arithmetic(ring, budget)


def _packet_row_factors(
    entry: CompiledEntry,
    bits: Tuple[int, ...],
    ar: Arithmetic,
) -> Tuple[RowFactor, ...]:
    if entry.kind != "packet":
        raise ValueError("packet recipe required")
    ref = entry.reference
    if len(bits) != ref.arity:
        raise ValueError("Boolean index has wrong shape")
    rows, cols, local, targets, _sources = entry.data
    selected = [(beta, coeffs) for beta, coeffs in targets if beta]
    factors: List[RowFactor] = []
    for row_index, pos in enumerate(rows):
        ar.budget.tick()
        local_value = ar.ring.zero
        for col_pos, coeff_jet in zip(cols, local[row_index]):
            if bits[col_pos]:
                local_value = ar.add(local_value, coeff_jet)
        constant = (
            local_value
            if bits[pos]
            else ar.add(ar.ring.one, ar.neg(local_value))
        )
        mode_row: List[object] = []
        for _, coeffs in selected:
            coeff = coeffs[row_index]
            mode_row.append(coeff if bits[pos] else ar.neg(coeff))
        factors.append(RowFactor(constant, tuple(mode_row)))
    return tuple(factors)


def build_packet_reference(
    *,
    arity: int,
    data,
    creation_precision: int = 7,
    defining_polynomial: int = 7,
    jet_length: int = 2,
    limits: EntryLimits = EntryLimits(),
):
    """Construct and compile a small packet recipe via ``make_reference``."""
    ref = make_reference(
        kind="packet",
        arity=arity,
        creation_precision=creation_precision,
        defining_polynomial=defining_polynomial,
        jet_length=jet_length,
        data=data,
        limits=limits,
    )
    compiled = compile_entry(ref, EntryBudget(limits))
    return ref, compiled


def expand_packet_polynomial(
    factors: Sequence[RowFactor],
    ar: Arithmetic,
    *,
    max_monomials: int = 50_000,
) -> PacketPoly:
    """Multilinear convolution ∏_r (c_r + Σ_j z_j a_{rj}) in exponent space."""
    if not factors:
        return {(): ar.ring.one}
    dim = len(factors[0].mode_coefficients)
    poly: PacketPoly = {tuple(0 for _ in range(dim)): ar.ring.one}
    unit = tuple(0 for _ in range(dim))

    def add_exponent(left: Exponent, right: Exponent) -> Exponent:
        return tuple(a + b for a, b in zip(left, right))

    def bump(exp: Exponent, index: int) -> Exponent:
        return tuple(
            value + (1 if j == index else 0) for j, value in enumerate(exp)
        )

    for factor in factors:
        row_poly: PacketPoly = {unit: factor.constant}
        for index, coeff in enumerate(factor.mode_coefficients):
            if coeff != ar.ring.zero:
                row_poly[bump(unit, index)] = coeff
        merged: PacketPoly = {}
        for left_exp, left_val in poly.items():
            for right_exp, right_val in row_poly.items():
                ar.budget.tick(len(row_poly))
                exp = add_exponent(left_exp, right_exp)
                merged[exp] = ar.add(
                    merged.get(exp, ar.ring.zero),
                    ar.mul(left_val, right_val),
                )
        if len(merged) > max_monomials:
            raise ValueError("packet polynomial monomial cap exceeded")
        poly = merged
    return poly


def explicit_monomial_resummation(
    poly: PacketPoly,
    weights: Sequence[object],
    ar: Arithmetic,
) -> object:
    """Compute Σ_β A_β ∏_j s_j^{β_j} from an expanded polynomial."""
    if not poly:
        return ar.ring.zero
    dim = len(next(iter(poly)))
    if len(weights) != dim:
        raise ValueError("weight vector length mismatch")
    total = ar.ring.zero
    for beta, coeff in poly.items():
        ar.budget.tick()
        if coeff == ar.ring.zero:
            continue
        term = coeff
        for exponent, weight in zip(beta, weights):
            if exponent:
                term = ar.mul(term, ar.power(weight, exponent))
        total = ar.add(total, term)
    return total


def substitution_resummation(
    factors: Sequence[RowFactor],
    weights: Sequence[object],
    ar: Arithmetic,
) -> object:
    """Compute ∏_r (c_r + Σ_j a_{rj} s_j) without expanding monomials."""
    if not factors:
        return ar.ring.one
    if len(weights) != len(factors[0].mode_coefficients):
        raise ValueError("weight vector length mismatch")
    product = ar.ring.one
    for factor in factors:
        ar.budget.tick()
        affine = factor.constant
        for coeff, weight in zip(factor.mode_coefficients, weights):
            if coeff != ar.ring.zero and weight != ar.ring.zero:
                affine = ar.add(affine, ar.mul(coeff, weight))
        product = ar.mul(product, affine)
    return product


def compare_resummation_methods(
    compiled: CompiledEntry,
    bits: Tuple[int, ...],
    weights: Sequence[object],
    *,
    limits: EntryLimits = EntryLimits(),
) -> ResummationResult:
    """Compare explicit monomial sum and substitution for fixed bits and weights."""
    budget = EntryBudget(limits)
    _ring, ar = _jet_ring_and_arithmetic(compiled, budget)
    factors = _packet_row_factors(compiled, bits, ar)
    poly = expand_packet_polynomial(factors, ar)
    explicit = explicit_monomial_resummation(poly, weights, ar)
    subst = substitution_resummation(factors, weights, ar)
    return ResummationResult(
        explicit_sum=explicit,
        substitution_value=subst,
        agree=explicit == subst,
        monomial_count=len(poly),
        row_count=len(factors),
        mode_count=len(weights),
    )


def production_packet_value(
    compiled: CompiledEntry,
    bits: Tuple[int, ...],
    *,
    precision: int | None = None,
    limits: EntryLimits = EntryLimits(),
):
    """Evaluate via the production streaming packet implementation."""
    ref = compiled.reference
    precision = precision or ref.creation_precision
    budget = EntryBudget(limits)
    return evaluate_compiled(compiled, bits, precision, budget)


def polynomial_target_value(
    compiled: CompiledEntry,
    bits: Tuple[int, ...],
    *,
    limits: EntryLimits = EntryLimits(),
):
    """Target-mode coefficient from expanded P(z), then source column powers."""
    budget = EntryBudget(limits)
    ring, ar = _jet_ring_and_arithmetic(compiled, budget)
    rows, cols, _local, targets, sources = compiled.data
    selected = [(beta, coeffs) for beta, coeffs in targets if beta]
    desired = tuple(beta for beta, _ in selected)
    factors = _packet_row_factors(compiled, bits, ar)
    poly = expand_packet_polynomial(factors, ar)
    coeff = poly.get(desired, ring.zero)

    for beta, col_coeffs in sources:
        if not beta:
            continue
        source = ring.zero
        for pos, scalar in zip(cols, col_coeffs):
            if bits[pos]:
                source = ring.add(source, ring.elem([[scalar]]))
        coeff = ar.mul(coeff, ar.power(source, beta))
    return coeff


def sketch_child_mode_dependencies(
    factors: Sequence[RowFactor],
    desired: Exponent,
    *,
    zero,
) -> Dict[str, object]:
    """Minimal dependency sketch for factorized child-sum (unverified).

    Lists, per mode index, which rows carry a nonzero target coefficient and
    which rows still have a nonzero constant.  Intended as a placeholder for a
    certified elimination-width analyzer; no graph elimination is performed.
    """
    if not factors:
        return {"rows": 0, "modes": 0, "row_support": [], "status": "STUB_ONLY"}
    row_support = []
    for row_index, factor in enumerate(factors):
        modes = [
            j
            for j, coeff in enumerate(factor.mode_coefficients)
            if coeff != zero
        ]
        row_support.append(
            {
                "row": row_index,
                "modes": modes,
                "has_constant": factor.constant != zero,
            }
        )
    return {
        "rows": len(factors),
        "modes": len(factors[0].mode_coefficients),
        "desired_exponents": desired,
        "positive_degree_rows_needed": sum(desired),
        "row_support": row_support,
        "status": "STUB_ONLY",
        "qualification": "no_width_certificate",
    }
