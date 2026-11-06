"""Globally optimal finite packet partitioning for the v1.1 incidence score.

Given a tensor network and packet size 1/2/4/8, return an order that
minimizes (total within-packet same-factor collision pairs, maximum factor
incidence in a packet) lexicographically. This code is an exact subset-DP
for <=16 *wires*, NOT the manuscript's D.3 collision-packing construction.

Within-packet permutations are irrelevant to this objective. Restrict
full packets to contain the least remaining wire, and enumerate the
possible final partial packet separately. This searches all partitions,
without factorial enumeration of wire permutations.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from time import monotonic

from veritas.research.tensor import TensorNetwork
from veritas.research.packet_schedule import PacketSchedule, collision_score


class PacketPlanningLimit(RuntimeError):
    """No finite optimum returned because an explicit bound was exceeded."""


@dataclass(frozen=True)
class PacketOptimalityEvidence:
    optimizer: str
    certificate_type: str
    size: int
    wires: int
    subset_states: int
    evaluated_blocks: int
    candidate_tail_packets: int
    collision_pairs: int
    maximum_incidence: int
    independent_score_replayed: bool


def optimize_packets_exact(net: TensorNetwork, *, packet_size: int = 2,
                           timeout_s: float = 5.0, max_wires: int = 16,
                           max_states: int = 250_000,
                           max_transitions: int = 2_000_000,
                           ) -> tuple[PacketSchedule, PacketOptimalityEvidence]:
    """Return a certifiable finite optimum, or raise PacketPlanningLimit.

    Search all packet *partitions*, not permutations. Identical packet sizes
    are treated as interchangeable. For n % packet_size != 0, the one partial
    packet must be last, and all possible partial groups are considered.

    Complexity remains exponential in the number of wires. Exactness of the
    combinatorial proxy does not imply good Cauchy runtime or any ETH theorem.
    """
    if type(packet_size) is not int or packet_size not in (1, 2, 4, 8):
        raise ValueError('packet_size must be 1, 2, 4 or 8')
    if type(max_wires) is not int or not 0 <= max_wires <= 16:
        raise ValueError('max_wires must be 0..16')
    if type(max_states) is not int or not 1 <= max_states <= 500_000:
        raise ValueError('max_states must be 1..500000')
    if type(max_transitions) is not int or not 1 <= max_transitions <= 10_000_000:
        raise ValueError('max_transitions must be 1..10000000')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
        raise ValueError('timeout_s must be in (0,30]')
    n = net.edges
    if n > max_wires:
        raise PacketPlanningLimit(f'exact packet subset DP supports <= {max_wires} wires, got {n}')

    deadline = monotonic() + timeout_s
    full = (1 << n) - 1
    factor_masks = tuple(sum(1 << v for v in f.ports) for f in net.factors)
    states = 0
    transitions = 0
    tails = 0

    def check_budget() -> None:
        if states > max_states or transitions > max_transitions:
            raise PacketPlanningLimit('exact packet DP state/transition budget exceeded')
        if monotonic() > deadline:
            raise PacketPlanningLimit('exact packet DP timeout')

    @lru_cache(maxsize=None)
    def block_score(mask: int) -> tuple[int, int]:
        pairs = 0
        peak = 0
        for factor in factor_masks:
            incidence = (factor & mask).bit_count()
            pairs += incidence * (incidence - 1) // 2
            peak = max(peak, incidence)
        return pairs, peak

    @lru_cache(maxsize=None)
    def best_full(mask: int) -> tuple[int, int, tuple[int, ...]]:
        nonlocal states, transitions
        states += 1
        check_budget()
        if not mask:
            return 0, 0, ()
        if mask.bit_count() % packet_size:
            raise AssertionError('non-full packet passed to full-packet DP')
        low = mask & -mask
        pivot = low.bit_length() - 1
        rest = [v for v in range(n) if (mask & (1 << v)) and v != pivot]
        best = None
        for selected in combinations(rest, packet_size - 1):
            transitions += 1
            if (transitions & 511) == 0:
                check_budget()
            packet = (pivot, *selected)
            packet_mask = low | sum(1 << v for v in selected)
            local_pairs, local_max = block_score(packet_mask)
            downstream_pairs, downstream_max, downstream_order = best_full(mask ^ packet_mask)
            candidate = (local_pairs + downstream_pairs,
                         max(local_max, downstream_max),
                         packet + downstream_order)
            if best is None or candidate < best:
                best = candidate
        if best is None:
            raise AssertionError('nonempty packet partition has no candidate')
        return best

    tail_size = n % packet_size
    best = None
    if tail_size:
        for tail in combinations(range(n), tail_size):
            tails += 1
            check_budget()
            tail_mask = sum(1 << v for v in tail)
            local_pairs, local_max = block_score(tail_mask)
            full_pairs, full_max, order = best_full(full ^ tail_mask)
            candidate = (local_pairs + full_pairs,
                         max(local_max, full_max), order + tail)
            if best is None or candidate < best:
                best = candidate
    else:
        best = best_full(full)
        tails = 1
    assert best is not None
    identity = tuple(range(n))
    baseline = collision_score(net, identity, packet_size)
    check = collision_score(net, best[2], packet_size)
    if check != best[:2]:
        raise AssertionError('packet subset DP disagrees with independent factor-incidence replay')
    if check > baseline:
        raise AssertionError('exact optimum worse than identity order')

    plan = PacketSchedule(
        wire_order=best[2], packet_size=packet_size,
        original_collisions=baseline[0], optimized_collisions=check[0],
        original_max_incidence=baseline[1], optimized_max_incidence=check[1],
        examined=transitions, exact_optimum=True,
        algorithm='exact-packet-subset-dp',
    )
    evidence = PacketOptimalityEvidence(
        optimizer='FINITE_PACKET_PARTITION_DP',
        certificate_type='RECOMPUTABLE_EXHAUSTIVE_SUBSET_RECURRENCE',
        size=packet_size, wires=n, subset_states=states,
        evaluated_blocks=transitions, candidate_tail_packets=tails,
        collision_pairs=check[0], maximum_incidence=check[1],
        independent_score_replayed=True,
    )
    return plan, evidence
