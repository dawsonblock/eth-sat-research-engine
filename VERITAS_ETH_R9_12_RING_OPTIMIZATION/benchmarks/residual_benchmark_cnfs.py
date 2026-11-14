"""Structured and adversarial CNF families for residual-state growth benchmarks."""
from __future__ import annotations

import random

from veritas.core.cnf import CNF


def cnf_block_xy_z() -> CNF:
    return CNF.from_lists(3, [[1, 3], [2, 3]])


def cnf_chain(n: int) -> CNF:
    if n < 2:
        return CNF.from_lists(max(n, 0), [])
    return CNF.from_lists(n, [[i, i + 1] for i in range(1, n)])


def cnf_independent_pairs(pair_count: int) -> CNF:
    clauses = [[2 * i - 1, 2 * i] for i in range(1, pair_count + 1)]
    return CNF.from_lists(2 * pair_count, clauses)


def cnf_star_coupled(spokes: int) -> CNF:
    """Hub variable 1 coupled to every peripheral OR."""
    n = 1 + spokes
    return CNF.from_lists(n, [[1, i] for i in range(2, n + 1)])


def cnf_layered_bridge(width: int, layers: int) -> CNF:
    """Independent chains within layers, linked by matching OR across layers."""
    if layers < 1 or width < 2:
        raise ValueError('width>=2 and layers>=1 required')
    n = width * layers
    clauses: list[list[int]] = []
    for layer in range(layers):
        base = layer * width + 1
        for i in range(width - 1):
            clauses.append([base + i, base + i + 1])
        if layer + 1 < layers:
            next_base = (layer + 1) * width + 1
            for i in range(width):
                clauses.append([base + i, next_base + i])
    return CNF.from_lists(n, clauses)


def cnf_pigeon_one_hot(n: int) -> CNF:
    """At-most-one style pairwise bans; intentionally brittle for unit merging."""
    if n < 2:
        return CNF.from_lists(n, [])
    clauses: list[list[int]] = []
    for i in range(1, n):
        for j in range(i + 1, n + 1):
            clauses.append([-i, -j])
    clauses.append(list(range(1, n + 1)))
    return CNF.from_lists(n, clauses)


def cnf_random_3sat(*, n: int, m: int, seed: int) -> CNF:
    rng = random.Random(seed)
    clauses: list[list[int]] = []
    for _ in range(m):
        vars_ = rng.sample(range(1, n + 1), 3)
        row: list[int] = []
        for v in vars_:
            row.append(v if rng.random() < 0.5 else -v)
        clauses.append(row)
    return CNF.from_lists(n, clauses)


def cnf_tight_primed_pairs(pair_count: int) -> CNF:
    """Each pair (a,b) with unit-like imbalance: defeats naive prefix symmetry."""
    clauses: list[list[int]] = []
    for i in range(1, pair_count + 1):
        a, b = 2 * i - 1, 2 * i
        clauses.append([a, b])
        clauses.append([a, -b])
    return CNF.from_lists(2 * pair_count, clauses)


FAMILY_BUILDERS = {
    'block_xy_z': lambda: cnf_block_xy_z(),
    'chain_8': lambda: cnf_chain(8),
    'independent_pairs_6': lambda: cnf_independent_pairs(6),
    'star_coupled_8': lambda: cnf_star_coupled(8),
    'layered_bridge_4x3': lambda: cnf_layered_bridge(4, 3),
    'pigeon_one_hot_5': lambda: cnf_pigeon_one_hot(5),
    'random_3sat_n10_m35_s42': lambda: cnf_random_3sat(n=10, m=35, seed=42),
    'tight_primed_pairs_5': lambda: cnf_tight_primed_pairs(5),
}
