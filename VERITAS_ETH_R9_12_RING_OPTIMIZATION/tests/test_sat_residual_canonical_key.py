"""Canonical residual keys: in-scope unit propagation buckets consistently."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any

from veritas.core.cnf import CNF
from veritas.research.sat_micro_generators import micro_generator_suite
from veritas.research.sat_residual_equivalence import (
    count_by_residual_equivalence,
    residual_state_key,
    residual_state_key_without_unit_propagation,
    restrict_partial,
)
from veritas.solvers.count_dag import _root_state
from veritas.solvers.reference import exhaustive_count


def _distinct_classes(
    cnf: CNF,
    *,
    key_fn,
) -> int:
    root = _root_state(cnf)
    order = tuple(range(1, cnf.n + 1))
    classes: dict[tuple[Any, ...], int] = defaultdict(int)

    def recurse(state, depth: int, mult: int) -> None:
        if depth >= len(order):
            classes[key_fn(state)] += mult
            return
        var = order[depth]
        if var not in state[0]:
            recurse(state, depth + 1, mult)
            return
        for value in (False, True):
            recurse(restrict_partial(state, var, value), depth + 1, mult)

    recurse(root, 0, 1)
    return len(classes)


def test_up_normalization_agreement_on_micro_generators():
    for _name, cnf, _family in micro_generator_suite():
        rep = count_by_residual_equivalence(cnf)
        assert rep["agreement"] is True
        assert rep["status"] == "EXACT_COUNT"
        assert rep["residual_key_normalization"] == "unit_propagation_fixpoint_v1"


def test_canonical_key_never_increases_bucket_count():
    for _name, cnf, _family in micro_generator_suite():
        legacy = _distinct_classes(cnf, key_fn=residual_state_key_without_unit_propagation)
        canon = _distinct_classes(cnf, key_fn=residual_state_key)
        assert canon <= legacy


def test_residual_fuzz_small_random_3cnf_agreement():
    rng = random.Random(823)
    for _ in range(40):
        n = rng.randint(2, 4)
        m = rng.randint(1, 6)
        clauses: list[list[int]] = []
        for _ in range(m):
            vs = rng.sample(range(1, n + 1), min(3, n))
            while len(vs) < 3:
                vs.append(rng.randint(1, n))
            clauses.append([v if rng.random() < 0.5 else -v for v in vs[:3]])
        cnf = CNF.from_lists(n, clauses)
        if exhaustive_count(cnf, max_vars=n) > 10_000:
            continue
        rep = count_by_residual_equivalence(cnf)
        assert rep["agreement"] is True
        legacy = _distinct_classes(cnf, key_fn=residual_state_key_without_unit_propagation)
        canon = _distinct_classes(cnf, key_fn=residual_state_key)
        assert canon <= legacy


def test_crafted_unit_propagation_merges_residual_buckets():
    # After x1=1: unit (-2) propagates; legacy key may differ before UP fixpoint.
    cnf = CNF.from_lists(3, [[1, 2], [1, -2], [-1, 2]])
    legacy = _distinct_classes(cnf, key_fn=residual_state_key_without_unit_propagation)
    canon = _distinct_classes(cnf, key_fn=residual_state_key)
    assert canon <= legacy
    rep = count_by_residual_equivalence(cnf)
    assert rep["agreement"] is True
    assert rep["count"] == exhaustive_count(cnf, max_vars=3)