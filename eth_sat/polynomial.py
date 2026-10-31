"""Univariate exact polynomial operations and rational Hermite interpolation."""

from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import Iterable, Sequence

Poly = tuple[Fraction, ...]  # coefficients in increasing degree order


def _trim(values: Iterable[int | Fraction]) -> Poly:
    result = [Fraction(value) for value in values]
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result or [Fraction(0)])


def constant(value: int | Fraction) -> Poly:
    return _trim([value])


def add(left: Sequence[Fraction], right: Sequence[Fraction]) -> Poly:
    size = max(len(left), len(right))
    return _trim(
        (left[i] if i < len(left) else 0) + (right[i] if i < len(right) else 0)
        for i in range(size)
    )


def subtract(left: Sequence[Fraction], right: Sequence[Fraction]) -> Poly:
    return add(left, scale(right, -1))


def multiply(left: Sequence[Fraction], right: Sequence[Fraction]) -> Poly:
    if not left or not right:
        return constant(0)
    out = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        if a:
            for j, b in enumerate(right):
                if b:
                    out[i + j] += a * b
    return _trim(out)


def scale(poly: Sequence[Fraction], value: int | Fraction) -> Poly:
    scalar = Fraction(value)
    return _trim(coefficient * scalar for coefficient in poly)


def evaluate(poly: Sequence[Fraction], point: int | Fraction) -> Fraction:
    x = Fraction(point)
    value = Fraction(0)
    for coefficient in reversed(poly):
        value = value * x + coefficient
    return value


def taylor_coefficients(
    poly: Sequence[Fraction], point: int | Fraction, order: int
) -> Poly:
    """Return ``[z**j] poly(point + z)`` for ``0 <= j < order``."""
    if order < 0:
        raise ValueError("order must be nonnegative")
    x = Fraction(point)
    values = []
    for j in range(order):
        coefficient = sum(
            poly[k] * comb(k, j) * x ** (k - j)
            for k in range(j, len(poly))
        )
        values.append(coefficient)
    return _trim(values) if order else tuple()


def _solve_exact(matrix: list[list[Fraction]], rhs: list[Fraction]) -> list[Fraction]:
    size = len(rhs)
    augmented = [
        [Fraction(value) for value in matrix[row]] + [Fraction(rhs[row])]
        for row in range(size)
    ]
    if any(len(row) != size + 1 for row in augmented):
        raise ValueError("Hermite system must be square")
    for column in range(size):
        pivot = next(
            (row for row in range(column, size) if augmented[row][column]), None
        )
        if pivot is None:
            raise ValueError("Hermite data do not determine a unique polynomial")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    a - factor * b
                    for a, b in zip(augmented[row], augmented[column])
                ]
    return [augmented[row][-1] for row in range(size)]


def hermite_interpolate(
    nodes: Sequence[int | Fraction], jets: Sequence[Sequence[int | Fraction]]
) -> Poly:
    """Reconstruct a polynomial from exact Taylor jets at distinct rational nodes.

    Each ``jets[i][j]`` is the coefficient of ``z**j`` in ``p(nodes[i] + z)``;
    it is a Taylor coefficient, not the ``j``th derivative.
    """
    if len(nodes) != len(jets) or not nodes:
        raise ValueError("provide one nonempty Taylor jet per node")
    rational_nodes = [Fraction(node) for node in nodes]
    if len(set(rational_nodes)) != len(rational_nodes):
        raise ValueError("Hermite nodes must be distinct")
    if any(not jet for jet in jets):
        raise ValueError("each Hermite jet must contain at least one coefficient")
    degree_bound = sum(map(len, jets))
    matrix: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    for node, jet in zip(rational_nodes, jets):
        for order, datum in enumerate(jet):
            matrix.append(
                [
                    Fraction(comb(power, order)) * node ** (power - order)
                    if power >= order
                    else Fraction(0)
                    for power in range(degree_bound)
                ]
            )
            rhs.append(Fraction(datum))
    return _trim(_solve_exact(matrix, rhs))


def hermite_value_at_zero(
    nodes: Sequence[int | Fraction], jets: Sequence[Sequence[int | Fraction]]
) -> Fraction:
    return hermite_interpolate(nodes, jets)[0]
