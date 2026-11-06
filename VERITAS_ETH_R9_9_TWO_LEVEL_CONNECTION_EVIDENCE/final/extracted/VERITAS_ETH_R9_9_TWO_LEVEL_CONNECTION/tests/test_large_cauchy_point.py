from fractions import Fraction
from math import factorial, prod

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value


@pytest.mark.parametrize('size', [32, 64, 128, 256])
@pytest.mark.parametrize('variant', [0, 1, 2])
def test_large_packet_point_matches_independent_rational_product(size, variant):
    # Evaluate the defining rational polynomial at an integer point, then
    # reduce the fraction using only its necessarily odd denominator.
    ring = ExtensionRing(13, 0b11)
    node = (-size, -1, size - 1)[variant]
    x = (0, size - 1, size // 2)[variant]
    y = (size - 1, 0, size // 3)[variant]
    z = (1, 2, 3)[variant]
    t = node + 2 * size * z
    numerator = prod(t - root for root in range(-size, size) if root != y - x)
    derivative = (-1 if (size - 1) & 1 else 1) * factorial(size) * factorial(size - 1)
    exact = Fraction(numerator, derivative)
    assert exact.denominator % 2 == 1
    expected = exact.numerator * pow(exact.denominator, -1, 1 << 13) % (1 << 13)
    assert cauchy_point_value(size, node, ring, x, y, (z,),
                              max_packet_size=size) == ring.elem([expected])


def test_larger_packets_require_an_explicit_bounded_limit():
    ring = ExtensionRing(3, 0b11)
    with pytest.raises(ValueError):
        cauchy_point_value(32, 1, ring, 0, 0, (0,))
    for cap in (True, 0, 257):
        with pytest.raises(ValueError):
            cauchy_point_value(2, 1, ring, 0, 0, (0,), max_packet_size=cap)
    with pytest.raises(ValueError):
        cauchy_point_value(512, 1, ring, 0, 0, (0,), max_packet_size=256)


@pytest.mark.parametrize('size', [32, 64, 128, 256])
def test_large_packet_deformation_is_identity_at_zero(size):
    ring = ExtensionRing(13, 0b11)
    for x, y in ((0, 0), (size - 1, size - 1), (0, size - 1)):
        value = cauchy_point_value(size, 0, ring, x, y, (0,), max_packet_size=size)
        assert value == (ring.one if x == y else ring.zero)
