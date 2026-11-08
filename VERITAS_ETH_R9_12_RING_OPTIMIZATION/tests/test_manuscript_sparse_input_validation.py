"""Reject malformed indices before Python equality can erase their types."""
from decimal import Decimal
from fractions import Fraction
import pytest
from veritas.research.manuscript.sparse import normalize_system
from veritas.research.manuscript.sparse_query import common_zeros
from veritas.research.manuscript.optimizations import common_zeros_factored

@pytest.mark.parametrize('invalid', [True, False, 1.0, 0.0, Decimal(1), Fraction(1)])
@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('api', [normalize_system, common_zeros, common_zeros_factored])
def test_equal_valued_noninteger_indices_always_rejected(invalid, reverse, api):
    monomial = [int(invalid), invalid]
    if reverse:
        monomial.reverse()
    with pytest.raises(ValueError, match='monomial variable'):
        api(2, [[monomial]])

def test_duplicate_integer_powers_and_equations_preserve_boolean_semantics():
    assert normalize_system(2, [[[1, 1, 0, 0], [0, 1]], [[1, 1]]]) == ((), (frozenset({1}),))
    for api in (common_zeros, common_zeros_factored):
        receipt = api(2, [[[1, 1, 0, 0], [0, 1]], [[1, 1]]])
        assert receipt['status'] == 'PASS_EXACT_COUNT'
        assert receipt['count'] == 2

def test_one_shot_monomial_iterators_validate_before_deduplication():
    assert normalize_system(2, [[iter([1, 1, 0])]]) == ((frozenset({0, 1}),),)
    with pytest.raises(ValueError, match='monomial variable'):
        normalize_system(2, [[iter([1, True])]])
