"""End-to-end exact counting via shared linear summaries.

Paper objects (vendored in `paper/`):

* `eq:general-count-polynomial` (l. 1700) -- `H(T)` and `H(0) = Z`.
* `subsec:fixed-boolean-substitutions` (l. 1886-1998) -- the Taylor data.
* `eq:hasse-order` and the Hermite remark (l. 1858-1880) -- `q`, `J`, and
  "Hermite interpolation recovers `H`, and hence `Z = H(0)`".

The pipeline is exactly the paper's:

1. choose schedules (`lem:incidence-labels`);
2. build the auxiliary swap matrix and measurements (`lem:swaps-matrix`);
3. place incidences in copies and push rows to the original variables
   (`subsec:embedding`);
4. verify `def:layout` (in particular its kernel condition);
5. at each `t in [Q]`, compute `H(t+z) mod z^J` by `eq:full-taylor-sum`;
6. solve the resulting rational linear system for the coefficients of `H`.

The count is exact over `Q`. Nothing here establishes the paper's running-time
bound: the parameters a finite reference can execute fail most of the numerical
hypotheses, and `FormParameters.summary()` reports which.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .auxiliary import build_auxiliary_layout
from .embedding import build_embedded_forms
from .instance import cnf_instance
from .labels import build_schedules
from .layout import verify_layout
from .parameters import scaled_parameters
from .taylor import taylor_series


class CountingBudgetExceeded(RuntimeError):
    pass


class CountingFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class CountingResult:
    value: int
    degree_bound: int
    points: int
    truncation: int
    pairs_per_point: int
    measurement_tuples: int
    assignments_examined: int
    layout: dict
    parameters: dict
    schedules: dict


def _binomial(n, k):
    if k < 0 or k > n:
        return 0
    value = 1
    for i in range(k):
        value = value * (n - i) // (i + 1)
    return value


def taylor_equations(points, truncation, degree):
    """Rows of the linear system `[z^j] H(t+z) = data`.

    Row `(t, j)` has coefficient `C(k, j) t**(k-j)` on `h_k`, for `k >= j`.
    """
    rows = []
    for point in points:
        for order in range(truncation):
            row = [Fraction(0)] * (degree + 1)
            for k in range(order, degree + 1):
                row[k] = Fraction(_binomial(k, order) * point ** (k - order))
            rows.append((point, order, row))
    return rows


def solve_exact(rows, rhs, variables):
    """Solve a consistent full-rank rational system, or raise."""
    matrix = [[Fraction(value) for value in row] + [Fraction(value)]
              for row, value in zip(rows, rhs)]
    pivot_row = 0
    pivots = []
    for column in range(variables):
        selected = None
        for candidate in range(pivot_row, len(matrix)):
            if matrix[candidate][column]:
                selected = candidate
                break
        if selected is None:
            continue
        matrix[pivot_row], matrix[selected] = matrix[selected], matrix[pivot_row]
        scale = matrix[pivot_row][column]
        matrix[pivot_row] = [value / scale for value in matrix[pivot_row]]
        for other in range(len(matrix)):
            if other == pivot_row or not matrix[other][column]:
                continue
            factor = matrix[other][column]
            matrix[other] = [a - factor * b
                             for a, b in zip(matrix[other], matrix[pivot_row])]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    for row in matrix[pivot_row:]:
        if any(row[:variables]) or not row[variables]:
            continue
    for row in matrix:
        if not any(row[:variables]) and row[variables]:
            raise CountingFailure('the Taylor data are inconsistent')
    if len(pivots) < variables:
        raise CountingFailure('the Taylor data do not determine the polynomial')
    solution = [Fraction(0)] * variables
    for index, column in enumerate(pivots):
        solution[column] = matrix[index][variables]
    return solution


def count_instance(instance, parameters, *, max_work=2_000_000,
                   max_pairs=200_000) -> CountingResult:
    """Count `Z` for a `FactorInstance` under one parameter set."""
    if instance.constant_zero:
        return CountingResult(value=0, degree_bound=parameters.degree_bound,
                              points=parameters.Q, truncation=parameters.J,
                              pairs_per_point=0, measurement_tuples=0,
                              assignments_examined=0, layout={},
                              parameters=parameters.summary(), schedules={})
    schedules = build_schedules(instance, parameters, max_work=max_work)
    auxiliary = build_auxiliary_layout(parameters)
    forms = build_embedded_forms(instance, parameters, schedules, auxiliary)
    report = verify_layout(forms)
    if not report.valid_identity:
        raise CountingFailure('the constructed rows violate the def:layout kernel condition')
    degree = parameters.degree_bound
    points = tuple(range(1, parameters.Q + 1))
    data = []
    tuples = examined = pairs = 0
    for point in points:
        series = taylor_series(forms, point, J=parameters.J,
                               max_work=max_work, max_pairs=max_pairs)
        data.append(series.series)
        tuples += series.measurement_tuples
        examined += series.assignments_examined
        pairs = series.pairs
    rows, rhs = [], []
    for point, order, row in taylor_equations(points, parameters.J, degree):
        rows.append(row)
        rhs.append(data[point - 1][order])
    solution = solve_exact(rows, rhs, degree + 1)
    value = solution[0]
    if value.denominator != 1:
        raise CountingFailure('the recovered constant coefficient is not an integer')
    stats = schedules.statistics(instance.incidence_list())
    return CountingResult(
        value=int(value), degree_bound=degree, points=parameters.Q,
        truncation=parameters.J, pairs_per_point=pairs,
        measurement_tuples=tuples, assignments_examined=examined,
        layout=report.summary(), parameters=parameters.summary(),
        schedules={'h': stats['h'], 'max_group': stats['max_group'],
                   'phi': str(stats['phi']), 'xi': str(stats['xi']),
                   'h_bound_met': stats['h_bound_met'],
                   'group_bound_met': stats['group_bound_met']})


def count_cnf(clauses, n, *, r=2, Q=2, R=2, max_width=3,
              max_occurrences=3, max_work=2_000_000,
              max_pairs=200_000) -> CountingResult:
    """Count the satisfying assignments of a bounded-occurrence CNF."""
    instance = cnf_instance(clauses, n, max_width=max_width,
                            max_occurrences=max_occurrences)
    parameters = scaled_parameters(instance.n, instance.b, instance.w,
                                   instance.M, instance.d, r=r, Q=Q, R=R)
    return count_instance(instance, parameters, max_work=max_work,
                          max_pairs=max_pairs)
