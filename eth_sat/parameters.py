"""Exact integer parameter selection for the manuscript's layout lemma."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import comb, isqrt


@dataclass(frozen=True, slots=True)
class DesignParameters:
    num_variables: int
    incidence_count: int
    max_factor_incidence: int
    max_scope: int
    beta: int
    lam: int
    nu: int
    r: int
    q_points: int
    degree_window: int
    tau: Fraction
    epsilon: Fraction
    auxiliary_dimension: int
    interval_start: int

    @property
    def interval(self) -> tuple[int, ...]:
        return tuple(
            range(self.interval_start, self.interval_start + self.degree_window)
        )


def choose_design_parameters(
    num_variables: int,
    incidence_count: int,
    max_factor_incidence: int,
    max_scope: int,
) -> DesignParameters | None:
    """Return certified theorem parameters, or None when finite-size guards fail."""
    if num_variables < 20 or incidence_count < num_variables:
        return None
    if max_factor_incidence < 1 or max_scope < 1:
        return None
    lam = (num_variables - 1).bit_length()
    nu = (lam - 1).bit_length()
    if nu < 1:
        return None
    sqrt_lam = isqrt(lam)
    r = sqrt_lam // (nu * nu)
    q_points = lam // (128 * nu)
    beta = 1
    scope_or_incidence = max(max_factor_incidence, max_scope)
    while lam**beta < scope_or_incidence:
        beta += 1
    degree_window = (beta + 3) * (sqrt_lam + (sqrt_lam * sqrt_lam < lam))
    if r < 2 or q_points <= degree_window:
        return None
    if degree_window < 32 or 6 * degree_window > q_points:
        return None

    epsilon = Fraction(1, max_factor_incidence * r * r * lam)
    tau = Fraction(1, r * lam)
    dimension = r ** (2 * q_points)
    if 2 * (max_factor_incidence + max_scope) * dimension * dimension > incidence_count:
        return None
    if 2 * q_points * r * r > num_variables:
        return None

    mean = Fraction(q_points * (r - 1), 2 * r)
    start_fraction = mean - Fraction(degree_window - 1, 2)
    interval_start = start_fraction.numerator // start_fraction.denominator
    if interval_start < 0 or interval_start + degree_window - 1 > q_points:
        return None

    denominator = (2 * r) ** q_points
    inside_numerator = sum(
        comb(q_points, weight)
        * (r - 1) ** weight
        * (r + 1) ** (q_points - weight)
        for weight in range(interval_start, interval_start + degree_window)
        if 0 <= weight <= q_points
    )
    tail_numerator = denominator - inside_numerator
    if tail_numerator * epsilon.denominator > denominator * epsilon.numerator:
        return None

    return DesignParameters(
        num_variables=num_variables,
        incidence_count=incidence_count,
        max_factor_incidence=max_factor_incidence,
        max_scope=max_scope,
        beta=beta,
        lam=lam,
        nu=nu,
        r=r,
        q_points=q_points,
        degree_window=degree_window,
        tau=tau,
        epsilon=epsilon,
        auxiliary_dimension=dimension,
        interval_start=interval_start,
    )

