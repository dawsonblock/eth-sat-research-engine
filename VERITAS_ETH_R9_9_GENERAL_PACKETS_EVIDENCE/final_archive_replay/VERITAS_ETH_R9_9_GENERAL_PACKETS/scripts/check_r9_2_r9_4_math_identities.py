#!/usr/bin/env python3
"""Small exact-arithmetic checks for identities used by the R9.2-R9.4 audit.

This is a finite sanity checker, not a proof of the universal packet,
contraction, interpolation, or complexity lemmas in the manuscript.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import product
from math import factorial


def cauchy_polynomial(L: int) -> list[int]:
    """Return C(T)=prod_{q=-L}^{L-1}(T-q), coefficients in ascending order."""
    coefficients = [1]
    for q in range(-L, L):
        updated = [0] * (len(coefficients) + 1)
        for i, coefficient in enumerate(coefficients):
            updated[i] -= q * coefficient
            updated[i + 1] += coefficient
        coefficients = updated
    return coefficients


def divide_by_root(coefficients: list[int], root: int) -> list[int]:
    """Exact synthetic division by T-root for an ascending coefficient list."""
    degree = len(coefficients) - 1
    quotient = [0] * degree
    quotient[-1] = coefficients[-1]
    for i in range(degree - 2, -1, -1):
        quotient[i] = coefficients[i + 1] + root * quotient[i + 1]
    remainder = coefficients[0] + root * quotient[0]
    if remainder != 0:
        raise ArithmeticError(f"T-{root} does not divide C(T); remainder={remainder}")
    return quotient


def check_pattern_multiplicity() -> int:
    cases = 0
    for r in range(2, 6):
        pairs = tuple((x, y) for x in range(r) for y in range(x, r))
        for a in range(1, 5):
            weighted_patterns = 0
            for pattern in product(pairs, repeat=a):
                unequal_coordinates = sum(x != y for x, y in pattern)
                weighted_patterns += 1 << unequal_coordinates
            assert weighted_patterns == r ** (2 * a), (r, a, weighted_patterns)

            # Also check the dense packet-number count for H=3L (which is a
            # multiple of every packet copy count 2^(a-a')).
            L = 1 << a
            H_pad = 3 * L
            packet_count = 0
            for pattern in product(pairs, repeat=a):
                unequal_coordinates = sum(x != y for x, y in pattern)
                copies_per_class_per_packet = 1 << (a - unequal_coordinates)
                assert H_pad % copies_per_class_per_packet == 0
                packet_count += H_pad // copies_per_class_per_packet
            assert packet_count == H_pad * r ** (2 * a) // L
            cases += 1
    return cases


def check_cauchy_origin() -> tuple[int, int]:
    checked_sizes = 0
    checked_entries = 0
    for a in range(0, 7):
        L = 1 << a
        coefficients = cauchy_polynomial(L)
        derivative_at_zero = coefficients[1]
        expected_derivative = (-1) ** (L - 1) * factorial(L) * factorial(L - 1)
        assert derivative_at_zero == expected_derivative, (L, derivative_at_zero)

        for difference in range(-(L - 1), L):
            quotient = divide_by_root(coefficients, difference)
            value_at_zero = Fraction(quotient[0], derivative_at_zero)
            assert value_at_zero == (1 if difference == 0 else 0)
            checked_entries += 1
        checked_sizes += 1
    return checked_sizes, checked_entries


def main() -> None:
    pattern_cases = check_pattern_multiplicity()
    cauchy_sizes, cauchy_entries = check_cauchy_origin()
    print(f"PASS: {pattern_cases} pattern and packet-count cases")
    print(f"PASS: C'(0) and W(0)=I for {cauchy_sizes} packet sizes")
    print(f"PASS: {cauchy_entries} distinct Cauchy differences checked by exact division")
    print("SCOPE: finite identity sanity checks only; no universal theorem qualification")


if __name__ == "__main__":
    main()
