"""Transfer the auxiliary spectral reference to a small CNF incidence layout."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from .model import CNF, Literal
from .polynomial import Poly, add, constant, evaluate
from .measurements import LinearMeasurements
from .schedules import ScheduleResult, build_balanced_schedules
from .spectral import SpectralReference, build_spectral_reference
from .verifier import row_space_coordinates


@dataclass(frozen=True, slots=True)
class SpectralCNFLayout:
    num_variables: int
    spectral: SpectralReference
    schedules: ScheduleResult
    scopes: tuple[tuple[int, ...], ...]
    groups_by_point: tuple[tuple[tuple[int, ...], ...], ...]
    owners_by_point: tuple[tuple[int, ...], ...]
    measurements_by_point: tuple[tuple[LinearMeasurements, ...], ...]
    replacements: tuple[tuple[tuple[int, PolyRow], ...], ...]
    copy_count: int
    placements: tuple[tuple[int | None, ...], ...]
    formula: CNF | None = None
    factor_literals: tuple[tuple[Literal, ...] | None, ...] | None = None


PolyRow = tuple[Poly, ...]


def build_spectral_cnf_layout(
    formula: CNF,
    *,
    r: int,
    q: int,
    degree_window: int,
    max_auxiliary_dimension: int | None = 64,
    max_schedule_work: int | None = 5_000_000,
) -> SpectralCNFLayout:
    """Build schedules, occurrence rows, and per-point group measurements.

    The function works on toy instances even when the manuscript's asymptotic
    balance hypotheses fail. In that case the identities remain exact, while
    ``schedules.paper_bounds_met`` reports that the advertised cost bounds were
    not certified.
    """
    factor_literals = tuple(_normalize_clause(clause) for clause in formula.clauses)
    scopes = tuple(
        tuple(sorted({literal.variable - 1 for literal in clause}))
        if clause is not None
        else tuple()
        for clause in factor_literals
    )
    layout = build_spectral_factor_layout(
        formula.num_variables,
        scopes,
        r=r,
        q=q,
        degree_window=degree_window,
        max_auxiliary_dimension=max_auxiliary_dimension,
        max_schedule_work=max_schedule_work,
    )
    return SpectralCNFLayout(
        num_variables=layout.num_variables,
        spectral=layout.spectral,
        schedules=layout.schedules,
        scopes=layout.scopes,
        groups_by_point=layout.groups_by_point,
        owners_by_point=layout.owners_by_point,
        measurements_by_point=layout.measurements_by_point,
        replacements=layout.replacements,
        copy_count=layout.copy_count,
        placements=layout.placements,
        formula=formula,
        factor_literals=factor_literals,
    )


def build_spectral_factor_layout(
    num_variables: int,
    factor_scopes: tuple[tuple[int, ...], ...],
    *,
    r: int,
    q: int,
    degree_window: int,
    max_auxiliary_dimension: int | None = 64,
    max_schedule_work: int | None = 5_000_000,
) -> SpectralCNFLayout:
    """Build a spectral layout for arbitrary factor scopes.

    Scope entries are zero-based variable indices. Factor functions are
    supplied separately to the generic Taylor evaluator.
    """
    scopes = tuple(tuple(sorted(set(scope))) for scope in factor_scopes)
    spectral = build_spectral_reference(
        r, q, degree_window, max_dimension=max_auxiliary_dimension
    )
    schedules = build_balanced_schedules(
        num_variables, scopes, r, q, max_work=max_schedule_work
    )

    copy_by_label: Counter[tuple[tuple[int, int], ...]] = Counter()
    occurrence_labels: dict[tuple[int, int], tuple[int, int]] = {}
    for factor_index, scope in enumerate(scopes):
        for variable in scope:
            label = tuple(
                (
                    schedules.variable_schedules[variable][point],
                    schedules.factor_schedules[factor_index][point],
                )
                for point in range(q)
            )
            coordinate = spectral.coordinate_index[label]
            copy_index = copy_by_label[label]
            copy_by_label[label] += 1
            occurrence_labels[(factor_index, variable)] = (copy_index, coordinate)

    copy_count = max(copy_by_label.values(), default=0)
    placements: list[list[int | None]] = [
        [None] * spectral.dimension for _ in range(copy_count)
    ]
    for (factor_index, variable), (copy_index, coordinate) in occurrence_labels.items():
        if placements[copy_index][coordinate] is not None:
            raise AssertionError("occurrence copies must occupy distinct auxiliary cells")
        placements[copy_index][coordinate] = variable

    replacements: list[list[tuple[int, PolyRow]]] = [
        [] for _ in scopes
    ]
    auxiliary_rows: dict[int, PolyRow] = {}
    for (factor_index, variable), (copy_index, coordinate) in occurrence_labels.items():
        auxiliary_row = auxiliary_rows.get(coordinate)
        if auxiliary_row is None:
            auxiliary_row = spectral.replacement_row(coordinate)
            auxiliary_rows[coordinate] = auxiliary_row
        actual_row = [constant(0) for _ in range(num_variables)]
        for auxiliary_coordinate, actual_variable in enumerate(placements[copy_index]):
            if actual_variable is not None:
                actual_row[actual_variable] = add(
                    actual_row[actual_variable], auxiliary_row[auxiliary_coordinate]
                )
        replacements[factor_index].append((variable, tuple(actual_row)))

    global_measurements: list[tuple[int, ...]] = []
    for placement in placements:
        for measurement_row in spectral.measurements:
            actual_row = [0] * num_variables
            for coordinate, actual_variable in enumerate(placement):
                if actual_variable is not None:
                    actual_row[actual_variable] += measurement_row[coordinate]
            global_measurements.append(tuple(actual_row))

    groups_by_point = tuple(
        tuple(
            tuple(
                variable
                for variable, schedule in enumerate(schedules.variable_schedules)
                if schedule[point] == group
            )
            for group in range(r)
        )
        for point in range(q)
    )
    owners_by_point = tuple(
        tuple(schedule[point] for schedule in schedules.factor_schedules)
        for point in range(q)
    )
    measurements_by_point = tuple(
        tuple(
            LinearMeasurements(
                tuple(
                    tuple(row[variable] for variable in group_variables)
                    for row in global_measurements
                ),
                len(group_variables),
            )
            for group_variables in groups
        )
        for groups in groups_by_point
    )

    return SpectralCNFLayout(
        num_variables=num_variables,
        spectral=spectral,
        schedules=schedules,
        scopes=scopes,
        groups_by_point=groups_by_point,
        owners_by_point=owners_by_point,
        measurements_by_point=measurements_by_point,
        replacements=tuple(tuple(rows) for rows in replacements),
        copy_count=copy_count,
        placements=tuple(tuple(copy) for copy in placements),
    )


def _normalize_clause(clause: tuple[Literal, ...]) -> tuple[Literal, ...] | None:
    """Remove duplicate literals and mark clauses containing x and not-x."""
    signs: dict[int, bool] = {}
    unique: list[Literal] = []
    seen: set[tuple[int, bool]] = set()
    for literal in clause:
        previous = signs.get(literal.variable)
        if previous is not None and previous != literal.negated:
            return None
        signs[literal.variable] = literal.negated
        key = (literal.variable, literal.negated)
        if key not in seen:
            seen.add(key)
            unique.append(literal)
    return tuple(unique)


def verify_spectral_cnf_layout(layout: SpectralCNFLayout) -> tuple[str, ...]:
    """Check restoration at zero and all per-point row-space conditions."""
    errors: list[str] = []
    n = layout.num_variables
    q = layout.spectral.parameters.q
    for factor_index, factor_rows in enumerate(layout.replacements):
        row_map = dict(factor_rows)
        for variable in layout.scopes[factor_index]:
            row = row_map[variable]
            restored = tuple(evaluate(coefficient, 0) for coefficient in row)
            expected = tuple(Fraction(int(index == variable)) for index in range(n))
            if restored != expected:
                errors.append(f"factor {factor_index}, variable {variable}: P(0) is not e_v")

    for point in range(q):
        groups = layout.groups_by_point[point]
        owners = layout.owners_by_point[point]
        matrices = layout.measurements_by_point[point]
        for factor_index, factor_rows in enumerate(layout.replacements):
            owner = owners[factor_index]
            for variable, polynomial_row in factor_rows:
                row_at_point = tuple(evaluate(coefficient, point + 1) for coefficient in polynomial_row)
                for group_index, group_variables in enumerate(groups):
                    if group_index == owner:
                        continue
                    restricted = tuple(row_at_point[variable] for variable in group_variables)
                    if row_space_coordinates(matrices[group_index].rows, restricted) is None:
                        errors.append(
                            f"factor {factor_index}, variable {variable}, point {point + 1}: "
                            f"group {group_index} restriction is outside measurement row space"
                        )
    return tuple(errors)
