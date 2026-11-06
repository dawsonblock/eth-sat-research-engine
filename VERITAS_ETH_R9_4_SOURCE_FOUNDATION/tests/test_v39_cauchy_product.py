import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value
from veritas.research.eth_interpolation.extension_lagrange import evaluate_polynomial
from veritas.research.eth_interpolation.shifted_cauchy import (
    fraction_to_ring, shifted_fraction_coefficients,
)
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials


@pytest.mark.parametrize('L,node,x,y,precision', [
    (2, -1, 0, 1, 5), (4, 2, 3, 0, 7), (8, -3, 0, 7, 69),
    (16, 3, 15, 0, 197), (16, -16, 4, 4, 197),
])
def test_product_cancellation_matches_independent_rational_polynomial(L, node, x, y, precision):
    ring = ExtensionRing(precision, first_irreducible(3))
    raw = cauchy_matrix_polynomials(L)[x][y]
    shifted = shifted_fraction_coefficients(raw, node, 2 * L)
    reference = tuple(fraction_to_ring(ring, coefficient) for coefficient in shifted)
    for zeta in (ring.zero, ring.one, ring.elem([0, 1]), ring.elem([1, 1, 1])):
        assert cauchy_point_value(L, node, ring, x, y, zeta) == evaluate_polynomial(ring, reference, zeta)


def test_product_cancellation_rejects_noncanonical_points():
    ring = ExtensionRing(5, first_irreducible(3))
    with pytest.raises(ValueError, match='canonical'):
        cauchy_point_value(4, 1, ring, 0, 0, (32, 0, 0))
