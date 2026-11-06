"""Bounded exact checks of the clause-mask compatibility rank lemma.

The general lemma follows from a tensor-product inverse. This finite audit
does not establish a lower bound for arbitrary SAT algorithms.
"""
from __future__ import annotations

from fractions import Fraction


def _rational_rank(matrix):
    rows = [[Fraction(value) for value in row] for row in matrix]
    height, width = len(rows), len(rows[0]) if rows else 0
    rank = 0
    for column in range(width):
        pivot = next((i for i in range(rank, height) if rows[i][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        pivot_value = rows[rank][column]
        for i in range(rank + 1, height):
            if rows[i][column]:
                factor = rows[i][column] / pivot_value
                for j in range(column, width):
                    rows[i][j] -= factor * rows[rank][j]
        rank += 1
        if rank == height:
            break
    return rank


def _binary_rank(matrix):
    rows = [sum((value & 1) << column for column, value in enumerate(row)) for row in matrix]
    rank = 0
    for column in range(len(rows)):
        pivot = next((i for i in range(rank, len(rows)) if rows[i] >> column & 1), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(rank + 1, len(rows)):
            if rows[i] >> column & 1:
                rows[i] ^= rows[rank]
        rank += 1
    return rank


def audit_clause_interface_rank(crossing_clauses, *, max_entries=4096):
    """Compute exact rational and F_2 ranks for a resource-bounded matrix."""
    if type(crossing_clauses) is not int or not 0 <= crossing_clauses <= 6:
        raise ValueError('finite rank audit supports 0..6 crossing clauses')
    if type(max_entries) is not int or max_entries < 1:
        raise ValueError('positive matrix-entry cap required')
    dimension = 1 << crossing_clauses
    if dimension * dimension > max_entries:
        raise ValueError('matrix-entry budget exceeded')
    all_ones = dimension - 1
    matrix = [[int((s | t) == all_ones) for t in range(dimension)]
              for s in range(dimension)]
    return {'crossing_clauses': crossing_clauses, 'dimension': dimension,
            'rational_rank': _rational_rank(matrix), 'binary_rank': _binary_rank(matrix),
            'universal_sat_lower_bound_proven': False}
