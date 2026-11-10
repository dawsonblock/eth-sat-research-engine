"""Precision-truncated weighted packet aggregate via a generating-function DP.

Computes the exact sum of monomial contributions with total mode weight
strictly below ``precision``, for row products

    P = prod_r (c_r + sum_j a_{rj} z_j)

at substitutions s_j, without enumerating exponent vectors. Equivalently the
coefficient sum of

    Q(t) = prod_r (c_r + sum_j a_{rj} s_j t^{w_j})  mod t^precision

for mode integer weights ``w_j``. This respects the **global** precision cutoff;
unlike per-component full substitution, it does not reintroduce forbidden terms.

No ETH theorem or subexponential bound is claimed.

**Proof sketch (row induction).** Let D_r[d] denote the sum of contributions with
total t-degree d after processing rows 1..r.  Start D_0[0]=1.  One row updates
D_{r+1}[d] = c_r D_r[d] + Σ_{j: w_j≤d} a_{rj} s_j D_r[d-w_j], which is exactly
the convolution form of multiplying by (c_r + Σ_j a_{rj} s_j t^{w_j}) in the
ring modulo t^P.  The returned value is Σ_{d<P} D_R[d].

This proves **problem A** only.  It does not extract a single A_β (**problem B**).
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

from .algebraic_resummation import RowFactor

ModeWeights = Tuple[int, ...]


def truncated_weighted_resummation(
    factors: Sequence[RowFactor],
    weights: Sequence[object],
    mode_weights: ModeWeights,
    precision: int,
    ar,
) -> object:
    """Sum contributions with Σ_j w_j β_j < precision using row-wise DP."""
    if type(precision) is not int or precision < 1:
        raise ValueError("positive precision required")
    if len(mode_weights) != len(weights):
        raise ValueError("weight vector length mismatch")
    if factors and len(factors[0].mode_coefficients) != len(weights):
        raise ValueError("weight vector length mismatch")
    zero = ar.ring.zero
    one = ar.ring.one
    cap = precision
    state: List[object] = [zero for _ in range(cap)]
    state[0] = one
    for factor in factors:
        nxt: List[object] = [zero for _ in range(cap)]
        if getattr(ar, "budget", None) is not None:
            ar.budget.tick(cap)
        for degree in range(cap):
            nxt[degree] = ar.add(nxt[degree], ar.mul(factor.constant, state[degree]))
            for index, coeff in enumerate(factor.mode_coefficients):
                weight = mode_weights[index]
                if coeff == zero or weight < 0 or weight > degree:
                    continue
                term = ar.mul(ar.mul(coeff, weights[index]), state[degree - weight])
                nxt[degree] = ar.add(nxt[degree], term)
        state = nxt
    total = zero
    for degree in range(cap):
        total = ar.add(total, state[degree])
    return total


def truncated_weighted_resummation_int(
    constants: Sequence[int],
    coefficients: Sequence[Sequence[int]],
    substitutions: Sequence[int],
    mode_weights: ModeWeights,
    precision: int,
    modulus: int,
) -> int:
    """Independent integer DP oracle for randomized differential tests."""
    if precision < 1:
        raise ValueError("positive precision required")
    cap = precision
    state = [0] * cap
    state[0] = 1 % modulus
    for row, constant in enumerate(constants):
        nxt = [0] * cap
        coeffs = coefficients[row]
        for degree in range(cap):
            nxt[degree] = (nxt[degree] + constant * state[degree]) % modulus
            for index, coeff in enumerate(coeffs):
                weight = mode_weights[index]
                if not coeff or weight < 0 or weight > degree:
                    continue
                nxt[degree] = (
                    nxt[degree] + coeff * substitutions[index] * state[degree - weight]
                ) % modulus
        state = nxt
    return sum(state) % modulus


def explicit_enumeration_int(
    constants: Sequence[int],
    coefficients: Sequence[Sequence[int]],
    substitutions: Sequence[int],
    mode_weights: ModeWeights,
    precision: int,
    modulus: int,
) -> int:
    """Independent oracle: enumerate beta with explicit row-product coefficients."""
    from itertools import product

    modes = len(substitutions)
    rows = len(constants)
    total = 0
    for beta in product(range(rows + 1), repeat=modes):
        if sum(beta) > rows:
            continue
        weight = sum(mode_weights[j] * beta[j] for j in range(modes))
        if weight >= precision:
            continue
        coef = _coefficient_at_beta(constants, coefficients, beta)
        term = coef
        for index, exponent in enumerate(beta):
            for _ in range(exponent):
                term = (term * substitutions[index]) % modulus
        total = (total + term) % modulus
    return total


def _coefficient_at_beta(
    constants: Sequence[int],
    coefficients: Sequence[Sequence[int]],
    beta: Tuple[int, ...],
) -> int:
    """Coefficient of prod_j z_j^{beta_j} in prod_r (c_r + sum_j a_{rj} z_j)."""
    from functools import lru_cache

    modes = len(beta)
    rows = len(constants)

    @lru_cache(maxsize=None)
    def recurse(row_index: int, remaining: Tuple[int, ...]) -> int:
        if row_index == rows:
            return 1 if all(x == 0 for x in remaining) else 0
        total = constants[row_index] * recurse(row_index + 1, remaining)
        for mode_index, count in enumerate(remaining):
            if count <= 0:
                continue
            next_remaining = list(remaining)
            next_remaining[mode_index] -= 1
            total += coefficients[row_index][mode_index] * recurse(
                row_index + 1, tuple(next_remaining)
            )
        return total

    return recurse(0, beta)
