"""Finite Cauchy point evaluation by exact 2-adic factor cancellation."""
from __future__ import annotations

from math import factorial

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing


def _v2_nonzero(value):
    if value == 0:
        raise ValueError('valuation requires a nonzero integer')
    value = abs(value)
    return (value & -value).bit_length() - 1


def cauchy_point_value(L, node, ring, x, y, zeta, *, max_packet_size=16):
    """Evaluate W_xy(node+2L*zeta), in a bounded unramified ring.

    The known 2-powers in numerator factors are cancelled as integers before
    the odd part of C'(0) is inverted. No nonunit is inverted in the ring.
    Packet sizes above 16 require an explicit finite limit, at most 256.
    """
    if not isinstance(ring, ExtensionRing):
        raise TypeError('ExtensionRing required')
    if (type(max_packet_size) is not int or not 1 <= max_packet_size <= 256):
        raise ValueError('finite packet-size limit must be in 1..256')
    if type(L) is not int or not 1 <= L <= max_packet_size or L & (L - 1):
        raise ValueError('finite packet size must be a power of two within the explicit limit')
    if type(node) is not int or node not in range(-L, L):
        raise ValueError('node outside the Cauchy grid')
    if any(type(v) is not int or v not in range(L) for v in (x, y)):
        raise ValueError('invalid Cauchy slot')
    if (not isinstance(zeta, (tuple, list)) or len(zeta) != ring.e or
            any(type(v) is not int or not 0 <= v < ring.modulus for v in zeta)):
        raise ValueError('zeta must be a canonical extension-ring value')
    zeta = tuple(zeta)
    alpha = 2 * L
    q = y - x
    derivative = (-1 if (L - 1) & 1 else 1) * factorial(L) * factorial(L - 1)
    denominator_twos = _v2_nonzero(derivative)
    odd_denominator = derivative // (1 << denominator_twos)
    numerator_twos = 0
    value = ring.one
    for root in range(-L, L):
        if root == q:
            continue
        if root == node:
            numerator_twos += alpha.bit_length() - 1
            factor = zeta
        else:
            difference = node - root
            twos = _v2_nonzero(difference)
            numerator_twos += twos
            factor = ring.add(ring.elem([difference // (1 << twos)]),
                              ring.mul(ring.elem([alpha // (1 << twos)]), zeta))
        value = ring.mul(value, factor)
    remaining_twos = numerator_twos - denominator_twos
    if remaining_twos < 0:
        raise ArithmeticError('uncancelled even denominator in Cauchy evaluation')
    scalar = (pow(odd_denominator, -1, ring.modulus) *
              pow(2, remaining_twos, ring.modulus)) % ring.modulus
    return ring.mul(value, ring.elem([scalar]))
