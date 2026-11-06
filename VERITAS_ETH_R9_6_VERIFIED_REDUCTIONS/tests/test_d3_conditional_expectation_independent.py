"""Enumerate complete labelings independently of the D.3 potential routine."""
from fractions import Fraction
from itertools import product

import pytest

from veritas.research.eth_packing_v26.expectation import expected_sq_load_scaled


@pytest.mark.parametrize('edges', [
    ((0, 0), (1, 1)),
    ((0, 0), (0, 1), (1, 0)),
    ((0, 0), (0, 0), (1, 0)),
])
@pytest.mark.parametrize('partial', [
    {}, {('R', 0, 0): 1}, {('R', 0, 0): 1, ('C', 0, 0): 0},
])
def test_conditional_expectation_matches_complete_enumeration(edges, partial):
    r, a = 2, 1
    variables = [('R', v, 0) for v in sorted({u for u, _ in edges})]
    variables += [('C', v, 0) for v in sorted({v for _, v in edges})]
    remaining = [v for v in variables if v not in partial]
    total = 0
    for values in product(range(r), repeat=len(remaining)):
        labels = dict(partial)
        labels.update(zip(remaining, values))
        loads = {}
        for row, col in edges:
            key = (labels['R', row, 0], labels['C', col, 0])
            loads[key] = loads.get(key, 0) + 1
        total += sum(n * n for n in loads.values())
    expected = Fraction(total * r**(2*a), r**len(remaining))
    assert expected_sq_load_scaled(edges, partial, r, a) == expected


def test_unconditional_centered_potential_obeys_degree_bound():
    edges = ((0, 0), (0, 0), (0, 1), (1, 1))
    d, m, delta = 4, len(edges), 3
    scaled = expected_sq_load_scaled(edges, {}, 2, 1)
    assert scaled - m*m <= 2*m*delta*d
