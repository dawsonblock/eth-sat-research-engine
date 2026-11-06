"""Finite, exact-checkable packet assignment optimizer.

Minimizes same-factor pairs of wires placed within each packet. This is a
bounded engineering heuristic/finite combinatorial optimum, NOT the
manuscript's collision-packing lemma, probabilistic construction, or its
asymptotic guarantees. Reordering changes the deformed F(T), but preserves
F(0), the original tensor contraction, exactly.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import permutations
from time import monotonic

from veritas.research.tensor import Factor, TensorNetwork


@dataclass(frozen=True)
class PacketSchedule:
    # new wire position -> old wire index
    wire_order: tuple[int, ...]
    packet_size: int
    original_collisions: int
    optimized_collisions: int
    original_max_incidence: int
    optimized_max_incidence: int
    examined: int
    exact_optimum: bool
    algorithm: str


def _validate_order(order: tuple[int, ...], edges: int) -> None:
    if len(order) != edges or set(order) != set(range(edges)):
        raise ValueError('wire_order must be an exact permutation')


def collision_score(net: TensorNetwork, order: tuple[int, ...], packet_size: int) -> tuple[int, int]:
    if type(packet_size) is not int or packet_size not in (1, 2, 4, 8):
        raise ValueError('packet_size must be 1, 2, 4 or 8')
    _validate_order(order, net.edges)
    positions = {old: new for new, old in enumerate(order)}
    pairs = 0
    maximum = 0
    for factor in net.factors:
        bins: dict[int, int] = {}
        for old in factor.ports:
            key = positions[old] // packet_size
            bins[key] = bins.get(key, 0) + 1
        pairs += sum(n*(n-1)//2 for n in bins.values())
        maximum = max(maximum, *bins.values(), 0)
    return pairs, maximum


def relabel_network(net: TensorNetwork, wire_order: tuple[int, ...]) -> TensorNetwork:
    """Reindex edge labels, without rearranging the corresponding local table bits."""
    _validate_order(wire_order, net.edges)
    new_index = {old: pos for pos, old in enumerate(wire_order)}
    return TensorNetwork(net.edges, tuple(
        Factor(tuple(new_index[e] for e in factor.ports), factor.table, factor.label)
        for factor in net.factors
    ))


def plan_packets(net: TensorNetwork, *, packet_size: int = 2,
                 max_permutations: int = 40320, timeout_s: float = 5.0) -> PacketSchedule:
    if net.edges > 16:
        raise ValueError('bounded packet planner supports at most 16 wires')
    if type(max_permutations) is not int or not 1 <= max_permutations <= 40320:
        raise ValueError('max_permutations must be 1..40320')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
        raise ValueError('timeout_s must be in (0,30]')
    identity = tuple(range(net.edges))
    baseline = collision_score(net, identity, packet_size)
    best_order, best_score = identity, baseline
    deadline = monotonic() + timeout_s
    examined = 0
    exact = net.edges <= 8
    if exact:
        for order in permutations(identity):
            if examined >= max_permutations or monotonic() > deadline:
                exact = False
                break
            score = collision_score(net, order, packet_size)
            examined += 1
            if (score, order) < (best_score, best_order):
                best_score, best_order = score, order
    else:
        # Deterministic coordinate descent with strict decreases and a finite
        # budget. This is NOT proof of global optimality.
        examined = 1
        improved = True
        while improved and examined < max_permutations and monotonic() <= deadline:
            improved = False
            for i in range(net.edges):
                for j in range(i + 1, net.edges):
                    if examined >= max_permutations or monotonic() > deadline:
                        break
                    candidate = list(best_order)
                    candidate[i], candidate[j] = candidate[j], candidate[i]
                    candidate = tuple(candidate)
                    score = collision_score(net, candidate, packet_size)
                    examined += 1
                    if (score, candidate) < (best_score, best_order):
                        best_score, best_order = score, candidate
                        improved = True
                if examined >= max_permutations or monotonic() > deadline:
                    break
    return PacketSchedule(best_order, packet_size, baseline[0], best_score[0], baseline[1],
                          best_score[1], examined, exact,
                          'exhaustive-small' if net.edges <= 8 else 'deterministic-local-swap')
