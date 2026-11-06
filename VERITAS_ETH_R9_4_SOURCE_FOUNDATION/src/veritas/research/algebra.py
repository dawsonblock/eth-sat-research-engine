"""Exact toy-sized identities used in ETH research; NOT the ETH algorithm."""
from __future__ import annotations
from fractions import Fraction
from itertools import combinations
from math import comb


def clause_indicator(clause: tuple[int, ...], assignment: dict[int, bool]) -> int:
    """1 - product of falsifying literal indicators."""
    product = 1
    for literal in clause:
        val = assignment[abs(literal)]
        product *= 1 - int(val) if literal > 0 else int(val)
    return 1 - product


def parity_indicator(level: int, integer: int) -> int:
    """p_level(Y) mod 2**level. Well-defined for negative Y too."""
    if not 1 <= level <= 32:
        raise ValueError("level must be 1..32")
    total = sum(comb(level+j-1, j) * integer**j for j in range(level))
    return ((1-integer)**level * total) % (1 << level)


def two_adic_valuation(value: int) -> int | None:
    """Return v_2(value); v_2(0)=infinity represented as None."""
    if value == 0: return None
    return (abs(value) & -abs(value)).bit_length() - 1


def omit_if_zero_mod(value: int, precision_bits: int) -> int:
    if not 1 <= precision_bits <= 4096:
        raise ValueError("precision_bits must be 1..4096")
    return 0 if value % (1 << precision_bits) == 0 else value % (1 << precision_bits)


def mobius_coefficients(values: list[int]) -> list[int]:
    """Return multilinear coefficients from evaluations f(1_S).
    Uses fixed bit ordering; len(values) must be a power of two.
    """
    length = len(values)
    if length == 0 or length & (length-1):
        raise ValueError("table size must be a positive power of two")
    if length > 1 << 18:
        raise ValueError("Boolean table too large")
    result = list(values)
    n = length.bit_length()-1
    for bit in range(n):
        for mask in range(length):
            if mask & (1 << bit):
                result[mask] -= result[mask ^ (1 << bit)]
    return result


def eval_multilinear(coeffs: list[int], bits: tuple[bool, ...]) -> int:
    assert len(coeffs) == 1 << len(bits)
    mask = sum((1 << i) for i, bit in enumerate(bits) if bit)
    return sum(value for submask, value in enumerate(coeffs) if submask & ~mask == 0)


def hermite_coefficients(samples: list[tuple[int, list[int]]]) -> list[Fraction]:
    """Solve exact confluent interpolation with ordinary derivatives.

    Samples: [(x, [f(x),f'(x),...,f^(k)(x)]), ...].
    Returns monomial coefficients for degree < total supplied derivative count.
    Uses Fraction Gaussian elimination. Intended for small reproducible cases.
    """
    if not samples or any(not derivs for _, derivs in samples):
        raise ValueError("nonempty derivative samples required")
    if len({x for x, _ in samples}) != len(samples):
        raise ValueError("interpolation nodes must be distinct")
    n = sum(len(d) for _, d in samples)
    if n > 28:
        raise ValueError("toy Hermite solver limited to degree 27")
    matrix: list[list[Fraction]] = []
    for x, derivatives in samples:
        for order, y in enumerate(derivatives):
            row = [Fraction(comb(degree, order)*x**(degree-order)) if degree >= order else Fraction(0) for degree in range(n)]
            row.append(Fraction(y))
            matrix.append(row)
    for col in range(n):
        pivot = next((r for r in range(col, n) if matrix[r][col] != 0), None)
        if pivot is None: raise ValueError("interpolation system is singular")
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = matrix[col][col]
        matrix[col] = [x / scale for x in matrix[col]]
        for r in range(n):
            if r != col and matrix[r][col]:
                factor = matrix[r][col]
                matrix[r] = [a - factor*b for a, b in zip(matrix[r], matrix[col])]
    return [matrix[i][-1] for i in range(n)]


def polynomial_derivative_eval(coefficients: list[Fraction], x: int, order: int = 0) -> Fraction:
    return sum(Fraction(coefficients[d]) * comb(d, order) * x**(d-order)
               for d in range(order, len(coefficients))) * _factorial(order)


def _factorial(n: int) -> int:
    result = 1
    for x in range(2, n+1): result *= x
    return result
