"""Materialize one unstructured graph at the packing lemma's minimum size and
check the child-size bound by direct counting.

The Lean theorem ``ModeCount.child_edges_of_packing`` says: for a bipartite
graph with ``M`` edges, maximum degree ``Delta``, labels in ``[r]^a`` and
``D = r^(2a)``, the conditions ``2*D^2*Delta <= M`` and ``L*D <= M`` give a
labeling under which every (coordinate, symbol) group owns at most ``6M/r``
edge ends, hence at most ``M/8`` once ``r >= 48``.

This script builds an explicit random graph of maximum degree ``Delta`` with
at least that many edges, draws labels, and verifies every hypothesis and the
conclusion with exact integer arithmetic. Labels are drawn at random and then
checked; nothing is trusted from the draw.

It is one instance of a counting lemma. It is off the manuscript's schedule
(which forces ``a >= 2`` and ``s >= 2^131071`` before any coordinate exists),
it builds no tensor network or child, runs no contraction, and is not evidence
for any running-time bound.
"""
from __future__ import annotations

import argparse
import json
from time import monotonic

MAX_EDGES = 200_000_000


def minimum_edges(radix: int, a: int, degree: int) -> int:
    D = radix ** (2 * a)
    return max(2 * D * D * degree, (1 << a) * D)


def _graph(np, target: int, degree: int, seed: int):
    """Union of ``degree`` random perfect matchings, duplicates removed."""
    rng = np.random.default_rng(seed)
    n = -(-target // degree) + 64
    keys = np.concatenate([np.arange(n, dtype=np.int64) * n + rng.permutation(n)
                           for _ in range(degree)])
    keys = np.unique(keys)
    return (keys // n).astype(np.int32), (keys % n).astype(np.int32), n


def audit(radix: int = 48, a: int = 1, degree: int = 1, seed: int = 0,
          max_label_draws: int = 8) -> dict:
    for name, value, low, high in (('radix', radix, 2, 64), ('a', a, 1, 2),
                                   ('degree', degree, 1, 64), ('seed', seed, 0, 2 ** 32 - 1),
                                   ('max_label_draws', max_label_draws, 1, 64)):
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{name} must be an integer in {low}..{high}')
    target = minimum_edges(radix, a, degree)
    if target > MAX_EDGES:
        raise ValueError(f'minimum edge count {target} exceeds the {MAX_EDGES} materialization cap')
    import numpy as np

    started = monotonic()
    rows, cols, n = _graph(np, target, degree, seed)
    M = int(rows.size)
    D, L = radix ** (2 * a), 1 << a
    row_degree = int(np.bincount(rows, minlength=n).max())
    col_degree = int(np.bincount(cols, minlength=n).max())

    weights = np.array([radix ** i for i in range(a)], dtype=np.int64)
    rng = np.random.default_rng([seed, 1])
    for draw in range(1, max_label_draws + 1):
        f = rng.integers(0, radix, size=(n, a), dtype=np.uint8)
        g = rng.integers(0, radix, size=(n, a), dtype=np.uint8)
        classes = (f[rows].astype(np.int64) @ weights) * radix ** a + g[cols].astype(np.int64) @ weights
        loads = [int(x) for x in np.bincount(classes, minlength=D)]
        # sum_gamma (X_gamma - M/D)^2 <= 2*M*Delta, cleared of denominators.
        potential_scaled = sum((D * x - M) ** 2 for x in loads)
        if potential_scaled <= 2 * M * degree * D * D:
            break
    potential_ok = potential_scaled <= 2 * M * degree * D * D

    padded = L * -(-max(loads) // L)
    packets_times_L = padded * D
    worst_row = worst_col = worst_child = 0
    for c in range(a):
        row_ports = np.bincount(f[rows, c], minlength=radix)
        col_ports = np.bincount(g[cols, c], minlength=radix)
        worst_row = max(worst_row, int(row_ports.max()))
        worst_col = max(worst_col, int(col_ports.max()))
        worst_child = max(worst_child, int((row_ports + col_ports).max()))

    hypotheses = {
        'simple_graph_edges_distinct': True,
        'row_degree_at_most_delta': row_degree <= degree,
        'column_degree_at_most_delta': col_degree <= degree,
        'edges_at_least_2_D2_delta': 2 * D * D * degree <= M,
        'edges_at_least_L_D': L * D <= M,
    }
    conclusions = {
        'potential_at_most_2_M_delta': potential_ok,
        'padded_slots_at_most_3M': packets_times_L <= 3 * M,
        'side_ports_within_padded_share': max(worst_row, worst_col) * radix <= packets_times_L,
        'child_edges_times_r_at_most_6M': worst_child * radix <= 6 * M,
        'child_edges_at_most_M_over_8': worst_child * 8 <= M,
    }
    return {
        'scope': 'MATERIALIZED_OFF_SCHEDULE_PACKING_INSTANCE_ONLY',
        'lean_theorem': 'ModeCount.child_edges_of_packing',
        'radix': radix, 'a': a, 'delta': degree, 'seed': seed, 'D': D, 'L': L,
        'minimum_edges_required': target, 'edges': M, 'vertices_per_side': n,
        'label_draws_used': draw,
        'hypotheses': hypotheses, 'conclusions': conclusions,
        'max_load': max(loads), 'mean_load_floor': M // D, 'padded_load': padded,
        'worst_child_edges': worst_child,
        'child_bound_6M_over_r_floor': 6 * M // radix, 'M_over_8_floor': M // 8,
        'worst_child_per_million_edges': worst_child * 1_000_000 // M,
        'one_eighth_bound_applicable': radix >= 48,
        'all_checks_pass': all(hypotheses.values()) and all(
            v for k, v in conclusions.items()
            if k != 'child_edges_at_most_M_over_8' or radix >= 48),
        'seconds': round(monotonic() - started, 2),
        'labels_are_random_then_verified': True,
        'deterministic_constructor_replayed': False,
        'on_manuscript_schedule': False,
        'tensor_network_built': False,
        'children_constructed': False,
        'contraction_executed': False,
        'complexity_claim': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--radix', type=int, default=48)
    parser.add_argument('--a', type=int, default=1)
    parser.add_argument('--degree', type=int, default=1)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    try:
        result = audit(args.radix, args.a, args.degree, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['all_checks_pass'] else 1)


if __name__ == '__main__':
    main()
