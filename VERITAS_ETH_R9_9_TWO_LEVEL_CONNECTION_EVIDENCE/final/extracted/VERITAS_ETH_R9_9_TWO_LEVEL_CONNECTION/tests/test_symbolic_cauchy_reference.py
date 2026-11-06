from fractions import Fraction

import pytest

from veritas.research.symbolic_cauchy_reference import (
    _has_weight, _shift, _wire_polynomial, audit_small_cauchy_symbolically,
)
from veritas.research.eth_interpolation.shifted_cauchy import shifted_fraction_coefficients
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials


@pytest.mark.parametrize('size', [2, 4])
@pytest.mark.parametrize('precision,order', [(2, 1), (5, 5), (7, 4)])
def test_independent_symbolic_geometric_modes(size, precision, order):
    result = audit_small_cauchy_symbolically(size, precision=precision, order=order)
    assert result['status'] == 'FINITE_SYMBOLIC_CAUCHY_IDENTITIES_CHECKED'
    assert result['crossings_checked'] > 0
    assert result['modes_checked'] == result['crossings_checked'] * (precision - 1)
    assert not result['full_recursive_theorem_proven']


def test_independent_polynomials_match_existing_exact_cauchy_coefficients():
    for size in (2, 4):
        existing = cauchy_matrix_polynomials(size)
        for x in range(size):
            for y in range(size):
                independent = _wire_polynomial(size, x, y)
                assert tuple(existing[x][y]) == independent
                for t in (-1, 1):
                    shifted = shifted_fraction_coefficients(existing[x][y], t, 2 * size)
                    assert _shift(independent, t, 2 * size, len(shifted)) == list(shifted)


def test_symbolic_valuation_rejects_a_corrupted_mode_coefficient():
    assert _has_weight(Fraction(16, 3), 4)
    assert not _has_weight(Fraction(16, 3) + 1, 4)
    assert not _has_weight(Fraction(1, 2), 1)
