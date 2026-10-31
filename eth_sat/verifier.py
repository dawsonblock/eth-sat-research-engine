"""Exact rational matrix checks for shared-measurement designs."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence


def _fraction(value: int | str | Fraction) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(value)


def matrix_rank(matrix: Sequence[Sequence[int | str | Fraction]], width: int | None = None) -> int:
    """Compute matrix rank over Q using exact Gaussian elimination."""
    rows = [[_fraction(value) for value in row] for row in matrix]
    if rows:
        inferred = len(rows[0])
        if any(len(row) != inferred for row in rows):
            raise ValueError("matrix rows must have equal width")
        if width is not None and width != inferred:
            raise ValueError("specified width does not match matrix rows")
    else:
        inferred = 0 if width is None else width
    rank = 0
    for column in range(inferred):
        pivot = next((row for row in range(rank, len(rows)) if rows[row][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        divisor = rows[rank][column]
        rows[rank] = [value / divisor for value in rows[rank]]
        for row in range(len(rows)):
            if row == rank:
                continue
            factor = rows[row][column]
            if factor:
                rows[row] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(rows[row], rows[rank])
                ]
        rank += 1
        if rank == len(rows):
            break
    return rank


def row_space_contains(
    matrix: Sequence[Sequence[int | str | Fraction]],
    vector: Sequence[int | str | Fraction],
) -> bool:
    """Return whether ``vector`` belongs to the rational row space of matrix."""
    if any(len(row) != len(vector) for row in matrix):
        raise ValueError("row-space vector and matrix dimensions differ")
    return matrix_rank(matrix, width=len(vector)) == matrix_rank(
        [*matrix, list(vector)], width=len(vector)
    )


def row_space_coordinates(
    matrix: Sequence[Sequence[int | str | Fraction]],
    vector: Sequence[int | str | Fraction],
) -> tuple[Fraction, ...] | None:
    """Find exact coefficients lambda with lambda * matrix == vector.

    Returns one rational solution with free coefficients set to zero, or None
    when the vector is outside the row space. The output length equals the
    number of rows in ``matrix``.
    """
    rows = len(matrix)
    width = len(vector)
    if any(len(row) != width for row in matrix):
        raise ValueError("row-space vector and matrix dimensions differ")
    # Solve matrix.T * lambda.T = vector.T by rational row reduction.
    augmented = [
        [_fraction(matrix[row][column]) for row in range(rows)]
        + [_fraction(vector[column])]
        for column in range(width)
    ]
    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(rows):
        pivot = next(
            (index for index in range(pivot_row, width) if augmented[index][column]),
            None,
        )
        if pivot is None:
            continue
        augmented[pivot_row], augmented[pivot] = augmented[pivot], augmented[pivot_row]
        divisor = augmented[pivot_row][column]
        augmented[pivot_row] = [value / divisor for value in augmented[pivot_row]]
        for index in range(width):
            if index == pivot_row:
                continue
            factor = augmented[index][column]
            if factor:
                augmented[index] = [
                    value - factor * pivot_value
                    for value, pivot_value in zip(augmented[index], augmented[pivot_row])
                ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == width:
            break
    if any(
        all(value == 0 for value in row[:rows]) and row[rows] != 0
        for row in augmented
    ):
        return None
    solution = [Fraction(0)] * rows
    for index, column in enumerate(pivot_columns):
        solution[column] = augmented[index][rows]
    return tuple(solution)


@dataclass(frozen=True, slots=True)
class VerificationIssue:
    factor: int
    replacement_row: int
    group: int
    message: str


def verify_replacement_rowspaces(
    groups: Sequence[Sequence[int]],
    measurement_matrices: Sequence[Sequence[Sequence[int | str | Fraction]]],
    factor_owners: Sequence[int],
    replacement_rows: Sequence[Sequence[Sequence[int | str | Fraction]]],
) -> tuple[VerificationIssue, ...]:
    """Check every nonowner restriction lies in that group's measurement span.

    For a row P assigned to group g, the kernel invariance condition on another
    group h is equivalent to P restricted to h belonging to rowspace(C_h).
    """
    if len(groups) != len(measurement_matrices):
        raise ValueError("supply one measurement matrix per group")
    if len(factor_owners) != len(replacement_rows):
        raise ValueError("supply one owner per factor's replacement rows")
    all_variables = [variable for group in groups for variable in group]
    if sorted(all_variables) != list(range(len(all_variables))):
        raise ValueError("groups must partition consecutive global variable indices")
    n = len(all_variables)
    for group, matrix in zip(groups, measurement_matrices):
        if any(len(row) != len(group) for row in matrix):
            raise ValueError("measurement matrix width does not match its group")
    issues: list[VerificationIssue] = []
    for factor, (owner, rows) in enumerate(zip(factor_owners, replacement_rows)):
        if owner < 0 or owner >= len(groups):
            raise ValueError(f"factor {factor} owner is outside group range")
        for row_index, row in enumerate(rows):
            if len(row) != n:
                raise ValueError(f"factor {factor} replacement row has wrong width")
            for group_index, group in enumerate(groups):
                if group_index == owner:
                    continue
                restriction = [_fraction(row[variable]) for variable in group]
                if not row_space_contains(measurement_matrices[group_index], restriction):
                    issues.append(
                        VerificationIssue(
                            factor,
                            row_index,
                            group_index,
                            "restriction is not in the group's rational measurement row space",
                        )
                    )
    return tuple(issues)


def verify_measurement_bounds(
    measurement_matrices: Iterable[Sequence[Sequence[int]]],
    max_row_l1: int,
    max_total_rows: int,
) -> tuple[str, ...]:
    """Check integer row L1 bounds and the aggregate measurement budget."""
    if max_row_l1 < 0 or max_total_rows < 0:
        raise ValueError("measurement bounds must be nonnegative")
    errors: list[str] = []
    total_rows = 0
    for group_index, matrix in enumerate(measurement_matrices):
        for row_index, row in enumerate(matrix):
            total_rows += 1
            if any(not isinstance(value, int) for value in row):
                errors.append(f"group {group_index} row {row_index} is not integer-valued")
            if sum(abs(int(value)) for value in row) > max_row_l1:
                errors.append(f"group {group_index} row {row_index} exceeds L1 bound")
    if total_rows > max_total_rows:
        errors.append(f"total row count {total_rows} exceeds budget {max_total_rows}")
    return tuple(errors)
