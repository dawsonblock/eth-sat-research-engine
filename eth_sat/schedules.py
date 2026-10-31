"""Deterministic conditional-expectation schedules for factor incidences."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Iterable, Sequence

ScheduleKey = tuple[str, int]
Schedule = tuple[int, ...]
Incidence = tuple[int, int]  # (factor index, zero-based variable index)
Label = tuple[tuple[int, int], ...]
_MAX_SCHEDULE_WORK = 5_000_000


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    """Schedules and exact diagnostics for a finite incidence system."""

    variable_schedules: tuple[Schedule, ...]
    factor_schedules: tuple[Schedule, ...]
    label_counts: tuple[tuple[Label, int], ...]
    group_sizes: tuple[tuple[int, ...], ...]  # [time][group]
    potential: Fraction
    hypotheses_met: bool
    paper_bounds_met: bool
    max_label_count: int
    max_group_size: int


def build_balanced_schedules(
    num_variables: int,
    factor_scopes: Sequence[Iterable[int]],
    r: int,
    q: int,
    max_work: int | None = _MAX_SCHEDULE_WORK,
) -> ScheduleResult:
    """Choose variable/factor group schedules by exact conditional expectation.

    Each variable gets a schedule in ``[r]^q``. Each nonempty factor gets an
    independent schedule; empty-scope factors are assigned to group zero at
    every point. The minimized potential is the manuscript's normalized sum
    of squared incidence-label and variable-group deviations.

    The construction is deterministic. When the manuscript's two balance
    hypotheses hold, its analysis certifies both factor-occurrence and group
    size bounds. For smaller toy inputs the function still returns the
    deterministic minimum-potential schedules, with the certificate status
    reported explicitly.
    """
    if num_variables < 0:
        raise ValueError("num_variables must be nonnegative")
    if r < 2 or q < 1:
        raise ValueError("r must be at least 2 and q must be positive")
    if max_work is not None and max_work < 1:
        raise ValueError("max_work must be positive or None")
    scopes = tuple(
        tuple(sorted(set(scope))) for scope in factor_scopes
    )
    for factor_index, scope in enumerate(scopes):
        if any(variable < 0 or variable >= num_variables for variable in scope):
            raise ValueError(f"factor {factor_index} contains an invalid variable index")

    incidences: tuple[Incidence, ...] = tuple(
        (factor_index, variable)
        for factor_index, scope in enumerate(scopes)
        for variable in scope
    )
    m = len(incidences)
    w = max((len(scope) for scope in scopes), default=1)
    variable_frequency = Counter(variable for _, variable in incidences)
    b = max(variable_frequency.values(), default=1)
    if not m:
        output_size = (num_variables + len(scopes) + r) * q
        if max_work is not None and output_size > max_work:
            raise ValueError(
                f"empty-scope schedule output size {output_size} exceeds "
                f"the limit {max_work}"
            )
        dimension = 1
        variable_schedules = tuple(
            tuple((variable + point) % r for point in range(q))
            for variable in range(num_variables)
        )
        factor_schedules = tuple(tuple(0 for _ in range(q)) for _ in scopes)
        group_sizes = _group_sizes(variable_schedules, r, q)
        return _result(
            variable_schedules,
            factor_schedules,
            incidences,
            group_sizes,
            Fraction(0),
            False,
            num_variables,
            m,
            dimension,
            r,
        )

    candidate_count = 1
    for _ in range(q):
        candidate_count *= r
        if max_work is not None and candidate_count > max_work:
            raise ValueError(
                "schedule candidate domain exceeds the exact conditional-"
                "expectation work limit"
            )
    random_key_count = num_variables + sum(bool(scope) for scope in scopes)
    estimated_work = (
        random_key_count
        * candidate_count
        * q
        * (m * m + num_variables * num_variables)
    )
    if max_work is not None and estimated_work > max_work:
        raise ValueError(
            f"schedule construction work estimate {estimated_work} exceeds "
            f"the limit {max_work}"
        )
    dimension = r ** (2 * q)
    domain: tuple[Schedule, ...] = tuple(product(range(r), repeat=q))

    random_keys: tuple[ScheduleKey, ...] = tuple(
        [("a", variable) for variable in range(num_variables)]
        + [
            ("d", factor_index)
            for factor_index, scope in enumerate(scopes)
            if scope
        ]
    )
    assigned: dict[ScheduleKey, Schedule] = {}

    def equality_probability(
        kind: str, left: int, right: int, point: int
    ) -> Fraction:
        left_key = (kind, left)
        right_key = (kind, right)
        if left_key == right_key:
            return Fraction(1)
        left_schedule = assigned.get(left_key)
        right_schedule = assigned.get(right_key)
        if left_schedule is not None and right_schedule is not None:
            return Fraction(left_schedule[point] == right_schedule[point])
        return Fraction(1, r)

    def expected_potential() -> Fraction:
        equal_incidence_pairs = Fraction(0)
        for left_factor, left_variable in incidences:
            for right_factor, right_variable in incidences:
                probability = Fraction(1)
                for point in range(q):
                    probability *= equality_probability(
                        "a", left_variable, right_variable, point
                    )
                    probability *= equality_probability(
                        "d", left_factor, right_factor, point
                    )
                    if not probability:
                        break
                equal_incidence_pairs += probability
        phi = equal_incidence_pairs - Fraction(m * m, dimension)

        equal_variable_pairs = Fraction(0)
        for point in range(q):
            for left_variable in range(num_variables):
                for right_variable in range(num_variables):
                    equal_variable_pairs += equality_probability(
                        "a", left_variable, right_variable, point
                    )
        xi = equal_variable_pairs - Fraction(q * num_variables * num_variables, r)
        return phi / (m * (b + w)) + xi / (q * num_variables)

    for key in random_keys:
        best_schedule: Schedule | None = None
        best_potential: Fraction | None = None
        for candidate in domain:
            assigned[key] = candidate
            value = expected_potential()
            if best_potential is None or value < best_potential:
                best_schedule = candidate
                best_potential = value
        if best_schedule is None:
            raise ArithmeticError("schedule domain unexpectedly had no candidates")
        assigned[key] = best_schedule

    variable_schedules = tuple(assigned[("a", variable)] for variable in range(num_variables))
    factor_schedules = tuple(
        assigned[("d", factor_index)] if scope else tuple(0 for _ in range(q))
        for factor_index, scope in enumerate(scopes)
    )
    group_sizes = _group_sizes(variable_schedules, r, q)
    final_potential = expected_potential()
    hypotheses_met = (
        2 * (b + w) * dimension * dimension <= m
        and 2 * q * r * r <= num_variables
    )
    return _result(
        variable_schedules,
        factor_schedules,
        incidences,
        group_sizes,
        final_potential,
        hypotheses_met,
        num_variables,
        m,
        dimension,
        r,
    )


def _group_sizes(
    variable_schedules: Sequence[Schedule], r: int, q: int
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(sum(schedule[point] == group for schedule in variable_schedules) for group in range(r))
        for point in range(q)
    )


def _result(
    variable_schedules: tuple[Schedule, ...],
    factor_schedules: tuple[Schedule, ...],
    incidences: Sequence[Incidence],
    group_sizes: tuple[tuple[int, ...], ...],
    potential: Fraction,
    hypotheses_met: bool,
    num_variables: int,
    incidence_count: int,
    dimension: int,
    r: int,
) -> ScheduleResult:
    counts: Counter[Label] = Counter()
    for factor, variable in incidences:
        label = tuple(
            (variable_schedules[variable][point], factor_schedules[factor][point])
            for point in range(len(factor_schedules[factor]))
        )
        counts[label] += 1
    max_label_count = max(counts.values(), default=0)
    max_group_size = max((max(row, default=0) for row in group_sizes), default=0)
    label_bound = all(count * dimension <= 2 * incidence_count for count in counts.values())
    group_bound = all(
        size * r <= 2 * num_variables
        for row in group_sizes
        for size in row
    )
    return ScheduleResult(
        variable_schedules,
        factor_schedules,
        tuple(sorted(counts.items())),
        group_sizes,
        potential,
        hypotheses_met,
        label_bound and group_bound,
        max_label_count,
        max_group_size,
    )
