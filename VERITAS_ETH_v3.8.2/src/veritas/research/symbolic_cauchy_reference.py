"""Independent exact rational-polynomial checks for small Cauchy packets.

This module deliberately does not use the packet, extension-ring or mode
generator implementations. Its exhaustive finite checks are not a proof for
arbitrary packet sizes or a verification of the recursive complexity bound.
"""
from __future__ import annotations

from fractions import Fraction
from math import comb


def _mul(left, right, order):
    out = [Fraction(0) for _ in range(order)]
    for i, a in enumerate(left[:order]):
        for j, b in enumerate(right[:order - i]):
            out[i + j] += a * b
    return out


def _v2(value):
    value = Fraction(value)
    if not value:
        return None
    n, d = abs(value.numerator), value.denominator
    return ((n & -n).bit_length() - 1) - ((d & -d).bit_length() - 1)


def _has_weight(value, weight):
    valuation = _v2(value)
    return valuation is None or valuation >= weight


def _wire_polynomial(packet_size, x, y):
    roots = tuple(range(-packet_size, packet_size))
    derivative = 1
    for root in roots:
        if root:
            derivative *= -root
    coefficients = [Fraction(1)]
    for root in roots:
        if root != y - x:
            coefficients = _mul(coefficients, [Fraction(-root), Fraction(1)],
                                len(coefficients) + 1)
    return tuple(value / derivative for value in coefficients)


def _shift(coefficients, t, alpha, order):
    return [sum((coefficients[j] * comb(j, k) * t ** (j - k) * alpha ** k
                 for j in range(k, len(coefficients))), Fraction(0))
            for k in range(order)]


def audit_small_cauchy_symbolically(packet_size, *, precision=5, order=5):
    """Check W(0), local geometric modes, and their valuations exactly."""
    if type(packet_size) is not int or packet_size not in (2, 4):
        raise ValueError('symbolic reference supports packet sizes 2 or 4')
    if (type(precision) is not int or not 2 <= precision <= 8 or
            type(order) is not int or not 1 <= order <= 8):
        raise ValueError('symbolic precision and jet order must be in 2..8 and 1..8')
    L = packet_size
    alpha = 2 * L
    a = L.bit_length() - 1
    entries = {(x, y): _wire_polynomial(L, x, y) for x in range(L) for y in range(L)}
    for (x, y), polynomial in entries.items():
        if polynomial[0] != int(x == y):
            raise ArithmeticError('Cauchy polynomial does not reduce to equality at zero')
    crossings = 0
    checked_modes = 0
    checked_coefficients = 0
    for t in range(-L, L):
        if t == 0:
            continue
        i = (abs(t) & -abs(t)).bit_length() - 1
        if i >= a:
            continue
        block = 1 << (i + 1)
        for x in range(L):
            for y in range(L):
                if (x >> i) & 1 != (y >> i) & 1:
                    continue
                y0, j = y % block, y // block
                denominator = t - y0 + x
                if not denominator:
                    raise ArithmeticError('crossing denominator unexpectedly vanishes')
                base = _shift(entries[x, y0], t, alpha, order)
                expected = _shift(entries[x, y], t, alpha, order)
                ratio = [Fraction(block, denominator)]
                for _ in range(1, order):
                    ratio.append(-ratio[-1] * Fraction(alpha, denominator))
                power = [Fraction(1)] + [Fraction(0)] * (order - 1)
                actual = [Fraction(0)] * order
                for b in range(precision - 1):
                    mode = _mul(base, power, order)
                    if not all(_has_weight(value, b + 1) for value in mode):
                        raise ArithmeticError('symbolic mode violates its divisibility bound')
                    actual = [left + right * j ** b for left, right in zip(actual, mode)]
                    power = _mul(power, ratio, order)
                    checked_modes += 1
                    checked_coefficients += order
                if not all(_has_weight(left - right, precision)
                           for left, right in zip(expected, actual)):
                    raise ArithmeticError('symbolic truncated geometric expansion differs')
                crossings += 1
    return {'status': 'FINITE_SYMBOLIC_CAUCHY_IDENTITIES_CHECKED',
            'packet_size': L, 'precision': precision, 'jet_order': order,
            'equality_entries_checked': len(entries), 'crossings_checked': crossings,
            'modes_checked': checked_modes, 'mode_coefficients_checked': checked_coefficients,
            'full_recursive_theorem_proven': False}
