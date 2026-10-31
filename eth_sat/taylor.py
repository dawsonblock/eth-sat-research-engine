"""Small-instance Taylor-jet evaluation through shared measurements."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb
from typing import Callable, Sequence

from .layout import SpectralCNFLayout
from .measurements import (
    Factor,
    SharedMeasurementProblem,
    shared_measurement_sum,
)
from .model import Literal
from .polynomial import (
    Poly,
    add,
    constant,
    hermite_interpolate,
    multiply,
    subtract,
    taylor_coefficients,
)
from .truncated import TruncatedPolynomial as ZPoly
from .verifier import row_space_coordinates


@dataclass(frozen=True, slots=True)
class TaylorCountResult:
    count: int
    reconstructed_polynomial: Poly
    nodes: tuple[int, ...]
    jets: tuple[tuple[Fraction, ...], ...]
    degree_bound: int
    jet_order: int
    substitution_pairs: int


@dataclass(frozen=True, slots=True)
class TaylorJetData:
    """Taylor data before interpolation, with coefficients in a caller ring."""

    nodes: tuple[int, ...]
    jets: tuple[object, ...]
    degree_bound: int
    jet_order: int
    substitution_pairs: int


@dataclass(frozen=True, slots=True)
class _OccurrenceData:
    local_coefficients: tuple[Fraction, ...]
    remote_measurements: tuple[tuple[Fraction, ...] | None, ...]
    coordinate_jets: tuple[ZPoly, ...]


def spectral_taylor_count(
    layout: SpectralCNFLayout,
    *,
    max_substitution_pairs: int | None = 100_000,
) -> TaylorCountResult:
    """Recover #SAT using fixed-Boolean substitutions and Hermite jets.

    This follows the manuscript's exact Taylor/measurement identities, but is
    intended only for small instances: all subsets ``E`` up to the Taylor
    cutoff and all ``U subset E`` are explicitly visited.
    """
    if layout.factor_literals is None:
        raise ValueError("CNF Taylor counter requires a CNF-backed spectral layout")
    factor_evaluators = tuple(
        _clause_evaluator(literals, scope)
        for literals, scope in zip(layout.factor_literals, layout.scopes)
    )
    degree_bound = (
        sum(len(scope) for scope in layout.scopes)
        * layout.spectral.parameters.degree_window
    )
    data = spectral_taylor_data(
        layout,
        factor_evaluators=factor_evaluators,
        degree_bound=degree_bound,
        ring_zero=ZPoly.zero,
        ring_coerce=_coerce_zpoly,
        max_substitution_pairs=max_substitution_pairs,
    )
    all_jets = tuple(jet.coefficients for jet in data.jets)
    reconstructed = hermite_interpolate(data.nodes, all_jets)
    count = reconstructed[0]
    if count.denominator != 1:
        raise ArithmeticError("Taylor/Hermite reconstruction returned a noninteger count")
    return TaylorCountResult(
        count=int(count),
        reconstructed_polynomial=reconstructed,
        nodes=data.nodes,
        jets=all_jets,
        degree_bound=data.degree_bound,
        jet_order=data.jet_order,
        substitution_pairs=data.substitution_pairs,
    )


def spectral_taylor_data(
    layout: SpectralCNFLayout,
    *,
    factor_evaluators: Sequence[Callable[[tuple[ZPoly, ...], int], object]],
    degree_bound: int,
    ring_zero: Callable[[int], object],
    ring_coerce: Callable[[object, int], object],
    max_substitution_pairs: int | None = 100_000,
    max_measurement_tuples: int | None = 1_000_000,
) -> TaylorJetData:
    """Compute Taylor jets for arbitrary local factors over a coefficient ring.

    Each factor evaluator receives its transformed input tuple as rational
    Taylor polynomials and the common truncation order. Its return values must
    live in a commutative ring supporting exact addition and multiplication.
    """
    if max_substitution_pairs is not None and max_substitution_pairs < 1:
        raise ValueError("max_substitution_pairs must be positive")
    if degree_bound < 0:
        raise ValueError("degree_bound must be nonnegative")
    if len(factor_evaluators) != len(layout.scopes):
        raise ValueError("one factor evaluator is required for each scope")
    layout_issues = verify_layout_for_taylor(layout)
    if layout_issues:
        raise ValueError("spectral layout failed verification: " + layout_issues[0])

    n = layout.num_variables
    q_points = layout.spectral.parameters.q
    taylor_cutoff = min(n, degree_bound // q_points)
    substitution_pairs = sum(
        comb(n, size) * (1 << size) for size in range(taylor_cutoff + 1)
    )
    if max_substitution_pairs is not None and substitution_pairs > max_substitution_pairs:
        raise ValueError(
            f"Taylor identity needs {substitution_pairs} (E,U) pairs, above "
            f"the limit {max_substitution_pairs}"
        )
    jet_order = degree_bound // q_points + 1
    nodes = tuple(range(1, q_points + 1))
    all_jets: list[object] = []

    for point_index, point in enumerate(nodes):
        occurrence_data = _prepare_occurrences(layout, point_index, point, jet_order)
        total = ring_zero(jet_order)
        for fixed_set in _subsets_up_to(n, taylor_cutoff):
            for chosen_set in _subsets(fixed_set):
                problem = _build_taylor_problem(
                    layout,
                    point_index,
                    jet_order,
                    chosen_set,
                    occurrence_data,
                    factor_evaluators,
                )
                contribution = shared_measurement_sum(
                    problem,
                    fixed_ones=fixed_set,
                    max_measurement_tuples=max_measurement_tuples,
                )
                contribution = ring_coerce(contribution, jet_order)
                sign = -1 if (len(fixed_set) - len(chosen_set)) % 2 else 1
                total = total + sign * contribution
        all_jets.append(total)
    return TaylorJetData(
        nodes=nodes,
        jets=tuple(all_jets),
        degree_bound=degree_bound,
        jet_order=jet_order,
        substitution_pairs=substitution_pairs,
    )


def _coerce_zpoly(value: object, order: int) -> ZPoly:
    return value if isinstance(value, ZPoly) else ZPoly.constant(value, order)  # type: ignore[arg-type]


def _clause_evaluator(
    literals: tuple[Literal, ...] | None, scope: tuple[int, ...]
) -> Callable[[tuple[ZPoly, ...], int], ZPoly]:
    if literals is None:
        return lambda _inputs, order: ZPoly.one(order)
    index = {variable: position for position, variable in enumerate(scope)}

    def evaluate_clause(inputs: tuple[ZPoly, ...], order: int) -> ZPoly:
        false_product = ZPoly.one(order)
        for literal in literals:
            value = inputs[index[literal.variable - 1]]
            literal_value = 1 - value if literal.negated else value
            false_product = false_product * (1 - literal_value)
        return ZPoly.one(order) - false_product

    return evaluate_clause


def verify_layout_for_taylor(layout: SpectralCNFLayout) -> tuple[str, ...]:
    """Local import wrapper to keep layout construction independent of Taylor code."""
    from .layout import verify_spectral_cnf_layout

    return verify_spectral_cnf_layout(layout)


def _prepare_occurrences(
    layout: SpectralCNFLayout,
    point_index: int,
    point: int,
    order: int,
) -> tuple[dict[int, _OccurrenceData], ...]:
    groups = layout.groups_by_point[point_index]
    measurements = layout.measurements_by_point[point_index]
    output: list[dict[int, _OccurrenceData]] = []
    for factor_index, factor_rows in enumerate(layout.replacements):
        owner = layout.owners_by_point[point_index][factor_index]
        owner_variables = groups[owner]
        factor_data: dict[int, _OccurrenceData] = {}
        for variable, row in factor_rows:
            coordinate_jets = tuple(
                ZPoly.from_coefficients(taylor_coefficients(coefficient, point, order), order)
                for coefficient in row
            )
            at_point = tuple(jet.coefficient(0) for jet in coordinate_jets)
            remote: list[tuple[Fraction, ...] | None] = []
            for group_index, group_variables in enumerate(groups):
                if group_index == owner:
                    remote.append(None)
                    continue
                restricted = tuple(at_point[index] for index in group_variables)
                coordinates = row_space_coordinates(
                    measurements[group_index].rows, restricted
                )
                if coordinates is None:
                    raise ValueError(
                        f"factor {factor_index}, variable {variable}: point {point} "
                        f"restriction is not represented by group {group_index} measurements"
                    )
                remote.append(coordinates)
            factor_data[variable] = _OccurrenceData(
                local_coefficients=tuple(at_point[index] for index in owner_variables),
                remote_measurements=tuple(remote),
                coordinate_jets=coordinate_jets,
            )
        output.append(factor_data)
    return tuple(output)


def _build_taylor_problem(
    layout: SpectralCNFLayout,
    point_index: int,
    order: int,
    chosen_set: tuple[int, ...],
    occurrence_data: tuple[dict[int, _OccurrenceData], ...],
    factor_evaluators: Sequence[Callable[[tuple[ZPoly, ...], int], object]],
) -> SharedMeasurementProblem:
    groups = layout.groups_by_point[point_index]
    owners = layout.owners_by_point[point_index]
    measurements = layout.measurements_by_point[point_index]
    factors: list[Factor] = []
    for factor_index, (scope, evaluator) in enumerate(
        zip(layout.scopes, factor_evaluators)
    ):
        owner = owners[factor_index]
        delta_by_variable = {
            variable: _delta_for_subset(data.coordinate_jets, chosen_set, order)
            for variable, data in occurrence_data[factor_index].items()
        }
        data_by_variable = occurrence_data[factor_index]

        def evaluate_factor(
            local_assignment: tuple[int, ...],
            summaries: tuple[tuple[int, ...], ...],
            *,
            factor_scope: tuple[int, ...] = scope,
            factor_owner: int = owner,
            factor_data: dict[int, _OccurrenceData] = data_by_variable,
            factor_delta: dict[int, ZPoly] = delta_by_variable,
            factor_evaluator: Callable[[tuple[ZPoly, ...], int], object] = evaluator,
            polynomial_order: int = order,
        ) -> object:
            transformed_inputs: list[ZPoly] = []
            for variable in factor_scope:
                data = factor_data[variable]
                base = sum(
                    (coefficient * bit for coefficient, bit in zip(data.local_coefficients, local_assignment)),
                    Fraction(0),
                )
                for group_index, coordinates in enumerate(data.remote_measurements):
                    if group_index == factor_owner or coordinates is None:
                        continue
                    base += sum(
                        (coefficient * measurement for coefficient, measurement in zip(coordinates, summaries[group_index])),
                        Fraction(0),
                    )
                transformed_inputs.append(
                    ZPoly.constant(base, polynomial_order) + factor_delta[variable]
                )
            return factor_evaluator(tuple(transformed_inputs), polynomial_order)

        factors.append(Factor(owner, evaluate_factor))
    return SharedMeasurementProblem(
        num_variables=layout.num_variables,
        groups=groups,
        measurements=measurements,
        factors=tuple(factors),
    )


def _delta_for_subset(
    coordinate_jets: Sequence[ZPoly],
    chosen_set: tuple[int, ...],
    order: int,
) -> ZPoly:
    delta = ZPoly.zero(order)
    for variable in chosen_set:
        coefficients = list(coordinate_jets[variable].coefficients)
        coefficients[0] = Fraction(0)
        delta = delta + ZPoly(tuple(coefficients), order)
    return delta


def _subsets_up_to(n: int, maximum_size: int):
    for size in range(maximum_size + 1):
        yield from combinations(range(n), size)


def _subsets(values: tuple[int, ...]):
    for mask in range(1 << len(values)):
        yield tuple(value for index, value in enumerate(values) if mask & (1 << index))


def direct_spectral_sum_polynomial(layout: SpectralCNFLayout) -> Poly:
    """Exhaustive oracle for H(T) from the layout's actual replacement rows."""
    if layout.factor_literals is None:
        raise ValueError("direct polynomial oracle requires a CNF-backed layout")
    n = layout.num_variables
    total = constant(0)
    rows_by_factor = [dict(rows) for rows in layout.replacements]
    for mask in range(1 << n):
        assignment = tuple((mask >> variable) & 1 for variable in range(n))
        term = constant(1)
        for factor_index, literals in enumerate(layout.factor_literals):
            if literals is None:
                continue
            false_product = constant(1)
            for literal in literals:
                row = rows_by_factor[factor_index][literal.variable - 1]
                value = constant(0)
                for coefficient, bit in zip(row, assignment):
                    if bit:
                        value = add(value, coefficient)
                if literal.negated:
                    value = subtract(constant(1), value)
                false_product = multiply(
                    false_product, subtract(constant(1), value)
                )
            term = multiply(term, subtract(constant(1), false_product))
            if term == constant(0):
                break
        total = add(total, term)
    return total
