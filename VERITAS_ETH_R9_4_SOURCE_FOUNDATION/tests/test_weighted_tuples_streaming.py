import itertools

import pytest

from veritas.research.eth_modes_v27.enumeration import (
    ModeBudgetExceeded, count_tuples, weighted_tuples,
)


def test_one_shot_weights_are_not_consumed_by_validation():
    assert count_tuples(iter([1, 2]), 4) == 6
    assert list(weighted_tuples(iter([1, 2]), 4)) == [
        (0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (3, 0),
    ]


def test_many_modes_with_one_tuple_does_not_use_python_recursion():
    weights = (3,) * 1500
    assert list(weighted_tuples(weights, 3, max_tuples=1)) == [(0,) * 1500]


def test_streaming_order_and_cutoff_match_independent_enumeration():
    for weights in itertools.product((1, 2, 3), repeat=3):
        for precision in range(1, 7):
            expected = [v for v in itertools.product(range(precision), repeat=3)
                        if sum(w * x for w, x in zip(weights, v)) < precision]
            assert list(weighted_tuples(weights, precision)) == expected
            assert count_tuples(iter(weights), precision) == len(expected)


def test_tuple_cap_fails_before_any_result():
    stream = weighted_tuples((1, 1), 5, max_tuples=2)
    with pytest.raises(ModeBudgetExceeded):
        next(stream)
