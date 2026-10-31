"""Generic exact shared-measurement factorization engine."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Callable, Iterable, Sequence

from .model import CNF

FactorEvaluator = Callable[
    [tuple[int, ...], tuple[tuple[int, ...], ...]], object
]


@dataclass(frozen=True, slots=True)
class LinearMeasurements:
    """Integer linear forms on one variable group."""

    rows: tuple[tuple[int, ...], ...]
    num_columns: int | None = None

    def __post_init__(self) -> None:
        normalized_rows = []
        for row in self.rows:
            normalized_row = []
            for value in row:
                integer = int(value)
                if Fraction(value) != integer:
                    raise ValueError("measurement coefficients must be integers")
                normalized_row.append(integer)
            normalized_rows.append(tuple(normalized_row))
        normalized = tuple(normalized_rows)
        if normalized and any(len(row) != len(normalized[0]) for row in normalized):
            raise ValueError("measurement rows must have equal width")
        inferred_width = len(normalized[0]) if normalized else 0
        width = inferred_width if self.num_columns is None else self.num_columns
        if width < 0 or (normalized and width != inferred_width):
            raise ValueError("measurement matrix column count is inconsistent")
        object.__setattr__(self, "num_columns", width)
        object.__setattr__(self, "rows", normalized)

    @property
    def width(self) -> int:
        return int(self.num_columns)

    def measure(self, assignment: Sequence[int]) -> tuple[int, ...]:
        if len(assignment) != self.width:
            raise ValueError("assignment width does not match measurement matrix")
        if any(bit not in (0, 1) for bit in assignment):
            raise ValueError("measurement assignment must be Boolean")
        return tuple(sum(a * b for a, b in zip(row, assignment)) for row in self.rows)


@dataclass(frozen=True, slots=True)
class Factor:
    """A factor owned by one group, evaluated from its bits and all summaries."""

    owner: int
    evaluate: FactorEvaluator


@dataclass(frozen=True, slots=True)
class SharedMeasurementProblem:
    num_variables: int
    groups: tuple[tuple[int, ...], ...]
    measurements: tuple[LinearMeasurements, ...]
    factors: tuple[Factor, ...]

    def __post_init__(self) -> None:
        if self.num_variables < 0:
            raise ValueError("num_variables must be nonnegative")
        if not self.groups or len(self.groups) != len(self.measurements):
            raise ValueError("each nonempty group list needs a measurement matrix")
        flattened = [variable for group in self.groups for variable in group]
        if sorted(flattened) != list(range(self.num_variables)):
            raise ValueError("groups must partition variable indices 0..n-1")
        for group, matrix in zip(self.groups, self.measurements):
            if matrix.width != len(group):
                raise ValueError("measurement matrix width must equal its group size")
        if any(factor.owner < 0 or factor.owner >= len(self.groups) for factor in self.factors):
            raise ValueError("factor owner is outside group range")


def shared_measurement_sum(
    problem: SharedMeasurementProblem,
    *,
    fixed_ones: Iterable[int] = (),
    max_measurement_tuples: int | None = 1_000_000,
) -> object:
    """Sum factors over assignments using exact shared-measurement separation.

    Correctness requires each factor to depend only on its owner group's local
    assignment and the supplied measurement tuple. The verifier can check
    linear-form instances of this condition exactly. Factor values may belong
    to any ring supporting exact addition and multiplication, including the
    truncated-polynomial ring used by Taylor-jet evaluation.
    """
    fixed = frozenset(fixed_ones)
    if any(variable < 0 or variable >= problem.num_variables for variable in fixed):
        raise ValueError("fixed variable index is outside the problem")
    if max_measurement_tuples is not None and max_measurement_tuples < 1:
        raise ValueError("max_measurement_tuples must be positive or None")
    fixed_positions = tuple(
        {index for index, variable in enumerate(group) if variable in fixed}
        for group in problem.groups
    )
    signature_ranges: list[tuple[range, ...]] = []
    tuple_count = 1
    for matrix in problem.measurements:
        group_ranges = []
        for row in matrix.rows:
            lower = sum(min(0, value) for value in row)
            upper = sum(max(0, value) for value in row)
            group_ranges.append(range(lower, upper + 1))
            tuple_count *= upper - lower + 1
        signature_ranges.append(tuple(group_ranges))
    if max_measurement_tuples is not None and tuple_count > max_measurement_tuples:
        raise ValueError(
            f"measurement enumeration needs {tuple_count} tuples, above the "
            f"limit {max_measurement_tuples}"
        )

    factors_by_owner: list[list[Factor]] = [
        [] for _ in range(len(problem.groups))
    ]
    for factor in problem.factors:
        factors_by_owner[factor.owner].append(factor)

    total: object = 0
    for signatures in _signature_tuples(signature_ranges):
        representatives: list[tuple[int, ...]] = []
        for group_index, (group, matrix) in enumerate(
            zip(problem.groups, problem.measurements)
        ):
            representative = None
            for state in product((0, 1), repeat=len(group)):
                if matrix.measure(state) == signatures[group_index]:
                    representative = tuple(state)
                    break
            if representative is None:
                break
            representatives.append(representative)
        if len(representatives) != len(problem.groups):
            continue

        contribution: object = 1
        for group_index, (group, matrix) in enumerate(
            zip(problem.groups, problem.measurements)
        ):
            subtotal: object = 0
            for local_assignment in product((0, 1), repeat=len(group)):
                if matrix.measure(local_assignment) != signatures[group_index]:
                    continue
                if any(
                    local_assignment[position] != 1
                    for position in fixed_positions[group_index]
                ):
                    continue
                term: object = 1
                for factor in factors_by_owner[group_index]:
                    term = term * factor.evaluate(local_assignment, signatures)
                    if not term:
                        break
                subtotal = subtotal + term
            contribution = contribution * subtotal
            if not contribution:
                break
        total = total + contribution
    return total


def _signature_tuples(ranges_by_group: Sequence[tuple[range, ...]]):
    """Yield all group measurement signatures without materializing a table."""
    def visit(group_index: int, prefix: list[tuple[int, ...]]):
        if group_index == len(ranges_by_group):
            yield tuple(prefix)
            return
        ranges = ranges_by_group[group_index]
        for signature in product(*ranges):
            prefix.append(tuple(signature))
            yield from visit(group_index + 1, prefix)
            prefix.pop()

    yield from visit(0, [])


def shared_measurement_count(problem: SharedMeasurementProblem) -> Fraction:
    """Rational-valued wrapper around :func:`shared_measurement_sum`."""
    return Fraction(shared_measurement_sum(problem))


def cnf_shared_measurement_count(formula: CNF, group_size: int = 4) -> int:
    """Compile a CNF to factors using unit summaries for external literals.

    This exact baseline exposes the shared-summary interface. Its summaries
    retain external bits explicitly and therefore do not give the paper's
    asymptotic speedup.
    """
    if group_size < 1:
        raise ValueError("group_size must be positive")
    n = formula.num_variables
    groups = tuple(
        tuple(range(start, min(start + group_size, n)))
        for start in range(0, n, group_size)
    )
    if not groups:
        groups = (tuple(),)
    group_of = {
        variable: group_index
        for group_index, group in enumerate(groups)
        for variable in group
    }
    clause_owners = [
        group_of[clause[0].variable - 1] if clause else 0
        for clause in formula.clauses
    ]
    needed: list[set[int]] = [set() for _ in groups]
    for clause, owner in zip(formula.clauses, clause_owners):
        for literal in clause:
            variable = literal.variable - 1
            external_group = group_of[variable]
            if external_group != owner:
                needed[external_group].add(variable)
    ordered_needed = [tuple(sorted(group)) for group in needed]
    measurements = []
    measurement_row: list[dict[int, int]] = []
    for group, variables in zip(groups, ordered_needed):
        positions = {variable: index for index, variable in enumerate(group)}
        rows = []
        for variable in variables:
            row = [0] * len(group)
            row[positions[variable]] = 1
            rows.append(tuple(row))
        measurements.append(LinearMeasurements(tuple(rows), len(group)))
        measurement_row.append({variable: index for index, variable in enumerate(variables)})

    factors: list[Factor] = []
    for clause, owner in zip(formula.clauses, clause_owners):
        owner_positions = {
            variable: index for index, variable in enumerate(groups[owner])
        }
        references = tuple(
            (literal.variable - 1, literal.negated) for literal in clause
        )

        def evaluate_clause(
            local_assignment: tuple[int, ...],
            signatures: tuple[tuple[int, ...], ...],
            *,
            clause_refs: tuple[tuple[int, bool], ...] = references,
            factor_owner: int = owner,
            positions: dict[int, int] = owner_positions,
            group_lookup: dict[int, int] = group_of,
            row_lookup: list[dict[int, int]] = measurement_row,
        ) -> int:
            for variable, negated in clause_refs:
                source_group = group_lookup[variable]
                if source_group == factor_owner:
                    bit = local_assignment[positions[variable]]
                else:
                    bit = signatures[source_group][row_lookup[source_group][variable]]
                if bool(bit) != negated:
                    return 1
            return 0

        factors.append(Factor(owner, evaluate_clause))

    problem = SharedMeasurementProblem(
        n, groups, tuple(measurements), tuple(factors)
    )
    result = shared_measurement_count(problem)
    if result.denominator != 1:
        raise ArithmeticError("CNF shared-measurement count is not integral")
    return int(result)
