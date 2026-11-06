"""Independent checks for packet/group capacity-aware tuple streaming."""
from itertools import product
from random import Random

import pytest

from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples


def _mode(packet, group, weight, rows):
    return {'packet': packet, 'target_group': group, 'weight': weight,
            'rows': [[row, []] for row in rows]}


def test_iterative_stream_matches_independent_cartesian_filter():
    rng = Random(20261102)
    for _ in range(120):
        count = rng.randrange(6)
        precision = rng.randrange(1, 6)
        modes = [_mode(rng.randrange(2), rng.randrange(2), rng.randrange(1, 5),
                       [row for row in range(4) if rng.randrange(2)])
                 for _ in range(count)]
        groups = {(m['packet'], m['target_group']) for m in modes}
        capacity = {g: len({row[0] for m in modes
                            if (m['packet'], m['target_group']) == g
                            for row in m['rows']}) for g in groups}
        expected = []
        for beta in product(range(precision), repeat=count):
            if sum(b * m['weight'] for b, m in zip(beta, modes)) >= precision:
                continue
            if any(b > len(m['rows']) for b, m in zip(beta, modes)):
                continue
            if any(sum(b for b, m in zip(beta, modes)
                       if (m['packet'], m['target_group']) == g) > capacity[g]
                   for g in groups):
                continue
            expected.append(beta)
        assert list(structural_tuples(modes, precision, max_tuples=100_000)) == expected


def test_large_mode_count_does_not_depend_on_python_recursion_limit():
    modes = [_mode(0, 0, 3, (0,)) for _ in range(1500)]
    assert list(structural_tuples(modes, 3, max_tuples=1)) == [(0,) * 1500]


def test_tuple_limit_fails_without_silently_truncating_stream():
    stream = structural_tuples([_mode(0, 0, 1, (0, 1))], 3, max_tuples=1)
    assert next(stream) == (0,)
    with pytest.raises(ModeBudgetExceeded):
        next(stream)
