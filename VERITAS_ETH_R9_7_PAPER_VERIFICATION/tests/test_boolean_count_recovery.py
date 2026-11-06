import pytest

from veritas.research.eth_arithmetic.boolean_count import recover_boolean_count


@pytest.mark.parametrize('n', range(9))
def test_full_boolean_count_range_is_unique_at_n_plus_one_bits(n):
    for count in range((1 << n) + 1):
        assert recover_boolean_count(count, precision=n + 1, num_variables=n) == count
    # At only n bits, an all-satisfying formula and an unsatisfiable formula
    # have the same zero residue, so even an observed zero is inconclusive.
    if n:
        with pytest.raises(ValueError, match='precision'):
            recover_boolean_count(0, precision=n, num_variables=n)


@pytest.mark.parametrize('residue,precision,n', [
    (-1, 3, 2), (True, 3, 2), (0, True, 0), (0, 1, False),
    (0, 0, 0), (0, 3, -1), (8, 3, 2), (5, 4, 2),
])
def test_boolean_count_recovery_rejects_invalid_or_impossible_inputs(residue, precision, n):
    with pytest.raises(ValueError):
        recover_boolean_count(residue, precision=precision, num_variables=n)


def test_large_declared_precision_does_not_require_constructing_the_modulus():
    assert recover_boolean_count(5, precision=10**9, num_variables=10**8) == 5
