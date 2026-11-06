from random import Random

import pytest

from veritas.research.hermite_ring import hermite_plan
from veritas.research.eth_interpolation.hermite_crt import hermite_crt_plan


def test_crt_reference_matches_independent_dense_confluent_solve():
    rng = Random(20261102)
    for _ in range(30):
        positions = rng.sample(range(-6, 7), rng.randrange(1, 5))
        specs = tuple((t, rng.randrange(1, 5)) for t in positions)
        degree = rng.randrange(min(sum(m for _, m in specs), 12))
        alpha = 1 << rng.randrange(0, 4)
        assert hermite_crt_plan(specs, alpha=alpha, degree_bound=degree) == hermite_plan(
            specs, alpha=alpha, degree_bound=degree)


def test_crt_reference_rejects_ambiguous_or_insufficient_inputs():
    for nodes, alpha, degree in [(((1,1),(1,1)), 1, 1), (((1,1),), 1, 1),
                                 (((1,1),), 0, 0), (((True,1),), 1, 0)]:
        with pytest.raises(ValueError):
            hermite_crt_plan(nodes, alpha=alpha, degree_bound=degree)
