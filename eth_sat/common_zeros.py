"""Exact counting for small sparse polynomial systems over F2."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from fractions import Fraction
from itertools import product
from math import comb, isqrt
from collections import Counter
from typing import Callable

from .bivariate import BivariateTruncatedPolynomial as BiPoly
from .layout import build_spectral_factor_layout
from .parameters import choose_design_parameters
from .polynomial import hermite_interpolate
from .sparse import F2Polynomial, SparsePolynomialSystem
from .taylor import TaylorJetData, spectral_taylor_data
from .truncated import TruncatedPolynomial as ZPoly


@dataclass(frozen=True, slots=True)
class CommonZeroResult:
    count: int
    residue: int
    modulus_exponent: int
    degree_bound: int
    jet_order: int
    substitution_pairs: int
    coefficient_values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SparseSystemCountResult:
    count: int
    used_exhaustive_fallback: bool
    branches_processed: int
    branch_variables: tuple[int, ...]
    designs_checked: int


@lru_cache(maxsize=None)
def parity_indicator_components(ell: int) -> tuple[tuple[int, int], ...]:
    """Return integer ``e_j(Y)=a_j+b_jY`` with p_ell=sum e_j(Y)(Y²-Y)^j."""
    if ell < 1:
        raise ValueError("ell must be positive")
    one_minus_y = [(-1) ** degree * comb(ell, degree) for degree in range(ell + 1)]
    truncated_inverse = [comb(ell + degree - 1, degree) for degree in range(ell)]
    p = [0] * (len(one_minus_y) + len(truncated_inverse) - 1)
    for left_degree, left_value in enumerate(one_minus_y):
        for right_degree, right_value in enumerate(truncated_inverse):
            p[left_degree + right_degree] += left_value * right_value
    p = _trim(p)

    components: list[tuple[int, int]] = []
    current = p
    for _ in range(ell):
        quotient, remainder = _divide_by_y_squared_minus_y(current)
        components.append(
            (remainder[0] if remainder else 0, remainder[1] if len(remainder) > 1 else 0)
        )
        current = quotient
    if any(current):
        raise ArithmeticError("parity indicator decomposition left a nonzero quotient")
    return tuple(components)


def _trim(values: list[int]) -> list[int]:
    while len(values) > 1 and values[-1] == 0:
        values.pop()
    return values


def _divide_by_y_squared_minus_y(poly: list[int]) -> tuple[list[int], list[int]]:
    work = list(poly)
    quotient = [0] * max(1, len(work) - 2)
    for degree in range(len(work) - 1, 1, -1):
        coefficient = work[degree]
        quotient[degree - 2] = coefficient
        work[degree] = 0
        work[degree - 1] += coefficient
    remainder = _trim(work[:2] or [0])
    return _trim(quotient), remainder


def _equation_evaluator(
    equation: F2Polynomial, ell: int
) -> Callable[[tuple[ZPoly, ...], int], BiPoly]:
    components = parity_indicator_components(ell)
    input_index = {variable: index for index, variable in enumerate(equation.scope)}

    def evaluate_equation(inputs: tuple[ZPoly, ...], order: int) -> BiPoly:
        lifted = ZPoly.zero(order)
        for monomial in equation.monomials:
            term = ZPoly.one(order)
            for variable in monomial:
                term = term * inputs[input_index[variable]]
            lifted = lifted + term

        h_value = lifted * (lifted - 1)
        power = ZPoly.one(order)
        result = BiPoly.zero(order, ell)
        for v_degree, (constant_term, linear_term) in enumerate(components):
            affine = constant_term + linear_term * lifted
            coefficient = affine * power
            result = result + BiPoly.from_z_polynomial(
                coefficient, ell, v_degree=v_degree
            )
            power = power * h_value
        return result

    return evaluate_equation


def _one_factor(ell: int) -> Callable[[tuple[ZPoly, ...], int], BiPoly]:
    return lambda _inputs, order: BiPoly.one(order, ell)


def _coerce_bipoly(value: object, order: int, ell: int) -> BiPoly:
    if isinstance(value, BiPoly):
        if (value.z_order, value.v_order) != (order, ell):
            raise ValueError("factor returned a polynomial with mismatched truncation orders")
        return value
    if isinstance(value, (int, Fraction)):
        return BiPoly.constant(value, order, ell)
    raise TypeError("sparse polynomial factor returned a value outside the coefficient ring")


def common_zero_count(
    system: SparsePolynomialSystem,
    *,
    r: int = 2,
    q_points: int = 3,
    degree_window: int = 2,
    max_auxiliary_dimension: int | None = 64,
    max_substitution_pairs: int | None = 100_000,
    max_measurement_tuples: int | None = 1_000_000,
    max_schedule_work: int | None = 5_000_000,
) -> CommonZeroResult:
    """Count common zeros exactly using the manuscript's shared-measurement core.

    Optional guards bound the dense auxiliary dimension, Taylor subset sum,
    measurement signatures, and schedule search. With guards disabled, this
    follows the exact parameterized construction and may require substantial
    time and memory even though the paper bounds them asymptotically.
    """
    n = system.num_variables
    if not system.equations:
        return CommonZeroResult(1 << n, 1 << n, n + 1, 0, 1, 1, (1 << n,))
    if any(equation.monomials == ((),) for equation in system.equations):
        return CommonZeroResult(0, 0, n + 1, 0, 1, 1, (0,))

    active = tuple(
        equation for equation in system.equations if equation.monomials
    )
    if not active:
        return CommonZeroResult(1 << n, 1 << n, n + 1, 0, 1, 1, (1 << n,))

    scopes = [equation.scope for equation in active]
    evaluators = [_equation_evaluator(equation, n + 1) for equation in active]
    neutral = _one_factor(n + 1)
    for variable in range(n):
        scopes.append((variable,))
        evaluators.append(neutral)

    layout = build_spectral_factor_layout(
        n,
        tuple(scopes),
        r=r,
        q=q_points,
        degree_window=degree_window,
        max_auxiliary_dimension=max_auxiliary_dimension,
        max_schedule_work=max_schedule_work,
    )
    ell = n + 1
    maximum_factor_degree = max(equation.degree for equation in active)
    input_degree = sum(equation.degree for equation in active) + 2 * n * maximum_factor_degree
    degree_bound = input_degree * degree_window
    data = spectral_taylor_data(
        layout,
        factor_evaluators=tuple(evaluators),
        degree_bound=degree_bound,
        ring_zero=lambda order: BiPoly.zero(order, ell),
        ring_coerce=lambda value, order: _coerce_bipoly(value, order, ell),
        max_substitution_pairs=max_substitution_pairs,
        max_measurement_tuples=max_measurement_tuples,
    )
    coefficient_values = _interpolate_v_coefficients(data, ell)
    modulus = 1 << ell
    residue = sum(coefficient_values) % modulus
    if residue > (1 << n):
        raise ArithmeticError("common-zero residue exceeds the Boolean cube size")
    return CommonZeroResult(
        count=residue,
        residue=residue,
        modulus_exponent=ell,
        degree_bound=data.degree_bound,
        jet_order=data.jet_order,
        substitution_pairs=data.substitution_pairs,
        coefficient_values=coefficient_values,
    )


def _interpolate_v_coefficients(data: TaylorJetData, ell: int) -> tuple[int, ...]:
    values: list[int] = []
    for v_degree in range(ell):
        jets = tuple(
            tuple(jet.coefficient(z_degree, v_degree) for z_degree in range(data.jet_order))
            for jet in data.jets
        )
        polynomial = hermite_interpolate(data.nodes, jets)
        origin = polynomial[0]
        if origin.denominator != 1:
            raise ArithmeticError(
                f"interpolated V^{v_degree} coefficient at zero is not integral"
            )
        values.append(origin.numerator)
    return tuple(values)


def exhaustive_common_zero_count(system: SparsePolynomialSystem) -> int:
    """Independent truth-table reference for sparse equation systems."""
    total = 0
    for mask in range(1 << system.num_variables):
        assignment = tuple((mask >> variable) & 1 for variable in range(system.num_variables))
        if system.evaluate(assignment):
            total += 1
    return total


def count_sparse_polynomial_zeros(
    system: SparsePolynomialSystem,
    *,
    max_fallback_variables: int | None = 24,
    max_auxiliary_dimension: int | None = None,
    max_substitution_pairs: int | None = None,
    max_measurement_tuples: int | None = None,
    max_schedule_work: int | None = None,
) -> SparseSystemCountResult:
    """Count a sparse F2 system using the paper's high-incidence branching.

    When the exact finite-size design checks do not pass, the paper uses direct
    enumeration. ``max_fallback_variables`` is a practical guard for that
    exponential fallback; set it to ``None`` to request the unbounded fallback.
    """
    n = system.num_variables

    def fallback() -> SparseSystemCountResult:
        if max_fallback_variables is not None and n > max_fallback_variables:
            raise ValueError(
                "layout parameter checks failed; exhaustive fallback needs "
                f"2^{n} assignments, above the configured {max_fallback_variables}-"
                "variable limit"
            )
        return SparseSystemCountResult(
            exhaustive_common_zero_count(system), True, 0, (), 0
        )

    if not system.equations:
        return SparseSystemCountResult(1 << n, False, 0, (), 0)
    if any(equation.monomials == ((),) for equation in system.equations):
        return SparseSystemCountResult(0, False, 0, (), 0)
    active = tuple(equation for equation in system.equations if equation.monomials)
    if not active:
        return SparseSystemCountResult(1 << n, False, 0, (), 0)
    if n < 20:
        return fallback()

    initial_scopes = tuple(equation.scope for equation in active)
    total_incidence = n + sum(len(scope) for scope in initial_scopes)
    lam = (n - 1).bit_length()
    ceil_sqrt_lam = isqrt(lam) + (isqrt(lam) ** 2 < lam)
    occurrence_counts: Counter[int] = Counter()
    for scope in initial_scopes:
        occurrence_counts.update(scope)
    for variable in range(n):
        occurrence_counts[variable] += 1  # one neutral unary factor per variable
    incidence_average = (total_incidence + n - 1) // n
    heavy_limit = incidence_average * ceil_sqrt_lam
    branch_variables = tuple(
        variable for variable in range(n) if occurrence_counts[variable] > heavy_limit
    )

    total_count = 0
    designs_checked = 0
    branches = 0
    for branch_bits in product((0, 1), repeat=len(branch_variables)):
        fixed = dict(zip(branch_variables, branch_bits))
        branch = system.restrict(fixed)
        branches += 1
        if any(equation.monomials == ((),) for equation in branch.equations):
            continue
        branch_active = tuple(equation for equation in branch.equations if equation.monomials)
        if not branch_active:
            total_count += 1 << branch.num_variables
            continue
        scopes = tuple(equation.scope for equation in branch_active)
        frequencies: Counter[int] = Counter()
        for scope in scopes:
            frequencies.update(scope)
        max_factor_incidence = max(
            (frequencies[variable] + 1 for variable in range(branch.num_variables)),
            default=1,
        )
        max_scope = max((len(scope) for scope in scopes), default=1)
        max_scope = max(max_scope, 1)
        branch_incidence = branch.num_variables + sum(len(scope) for scope in scopes)
        params = choose_design_parameters(
            branch.num_variables,
            branch_incidence,
            max_factor_incidence,
            max_scope,
        )
        if params is None:
            return fallback()
        designs_checked += 1
        counted = common_zero_count(
            branch,
            r=params.r,
            q_points=params.q_points,
            degree_window=params.degree_window,
            max_auxiliary_dimension=max_auxiliary_dimension,
            max_substitution_pairs=max_substitution_pairs,
            max_measurement_tuples=max_measurement_tuples,
            max_schedule_work=max_schedule_work,
        )
        total_count += counted.count

    return SparseSystemCountResult(
        total_count,
        False,
        branches,
        branch_variables,
        designs_checked,
    )

