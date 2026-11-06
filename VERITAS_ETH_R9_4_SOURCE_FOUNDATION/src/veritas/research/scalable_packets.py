"""Scalable, bounded packet-incidence search with a *provable* finite lower bound.

This does NOT implement manuscript D.3 packing. The packet collision surrogate
is the one defined in packet_schedule.py. The minimum per-factor number of
colliding pairs over p packets is obtained by distributing d incidences as
uniformly as possible. Summing these independent minima is a valid GLOBAL
lower bound, not necessarily attainable simultaneously by all factors.

When the computed score matches BOTH components of that bound, we have a
mathematical optimality certificate for the surrogate without exhaustive search.
Otherwise the output is only a fully checked feasible schedule, and the bound
quantifies an honest optimality gap. Work/time limits return a valid incumbent.
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from time import monotonic

from veritas.research.packet_schedule import PacketSchedule, collision_score
from veritas.research.tensor import TensorNetwork


@dataclass(frozen=True)
class PacketSearchEvidence:
    optimizer: str
    wires: int
    packet_size: int
    packets: int
    pair_lower_bound: int
    peak_lower_bound: int
    achieved_pairs: int
    achieved_peak: int
    pair_gap: int
    full_lower_bound_matched: bool
    exact_optimum_certified: bool
    candidate_swaps: int
    complete_passes: int
    restarts_attempted: int
    termination: str
    objective_replayed: bool


def collision_lower_bound(net: TensorNetwork, packet_size: int) -> tuple[int, int]:
    """Valid global lower bound of lexicographic (pairs, peak-incidence).

    Each factor has d distinct wires. Among p packets, the convex sum
    sum_j binom(c_j,2) is minimized by c_j differing by at most 1. Capacity
    packet_size is not violated because d<=n and p=ceil(n/packet_size).
    Peak >= ceil(d/p). This holds regardless of inter-factor constraints.
    """
    if type(packet_size) is not int or packet_size not in (1, 2, 4, 8):
        raise ValueError('packet_size must be 1, 2, 4 or 8')
    p = (net.edges + packet_size - 1) // packet_size
    if p == 0:
        return 0, 0
    lb_pairs = lb_peak = 0
    for factor in net.factors:
        d = len(factor.ports)
        q, rem = divmod(d, p)
        lb_pairs += (p-rem)*q*(q-1)//2 + rem*(q+1)*q//2
        lb_peak = max(lb_peak, (d+p-1)//p)
    return lb_pairs, lb_peak


def _factor_pair_weights(net: TensorNetwork) -> tuple[list[list[int]], list[list[int]]]:
    n = net.edges
    weights = [[0]*n for _ in range(n)]
    incident = [[] for _ in range(n)]
    for factor_id, factor in enumerate(net.factors):
        for i, a in enumerate(factor.ports):
            incident[a].append(factor_id)
            for b in factor.ports[i+1:]:
                weights[a][b] += 1
                weights[b][a] += 1
    return weights, incident


def _block_score(packet: tuple[int, ...], weights: list[list[int]],
                 incident: list[list[int]]) -> tuple[int, int]:
    pairs = 0
    occurrences: dict[int, int] = {}
    for i, a in enumerate(packet):
        for b in packet[i+1:]:
            pairs += weights[a][b]
        for f in incident[a]:
            occurrences[f] = occurrences.get(f, 0) + 1
    return pairs, max(occurrences.values(), default=0)


def _greedy_order(n: int, packet_size: int, weights: list[list[int]]) -> tuple[int, ...]:
    remaining = set(range(n))
    deg = [sum(row) for row in weights]
    order: list[int] = []
    while remaining:
        # Start with the wire appearing in the most collision opportunities.
        pivot = min(remaining, key=lambda v: (-deg[v], v))
        remaining.remove(pivot)
        packet = [pivot]
        for _ in range(min(packet_size-1, len(remaining))):
            chosen = min(remaining, key=lambda v: (sum(weights[v][u] for u in packet), -deg[v], v))
            packet.append(chosen)
            remaining.remove(chosen)
        order.extend(packet)
    return tuple(order)


def optimize_packets_scalable(net: TensorNetwork, *, packet_size: int = 2,
                              timeout_s: float = 5.0, max_wires: int = 256,
                              max_evaluations: int = 25_000,
                              restarts: int = 5, seed: int = 190026) -> tuple[PacketSchedule, PacketSearchEvidence]:
    """Bounded multi-start local swaps, with exact objective replay and bounds.

    Returns a valid schedule even when a search budget is exhausted. It only
    asserts global optimality if its achieved objective equals a rigorous
    lower bound, which is normally impossible on dense, conflicting instances.
    """
    if type(packet_size) is not int or packet_size not in (1, 2, 4, 8):
        raise ValueError('packet_size must be 1, 2, 4 or 8')
    if type(max_wires) is not int or not 0 <= max_wires <= 2048:
        raise ValueError('max_wires must be in 0..2048')
    if net.edges > max_wires:
        raise ValueError(f'packet search supports at most {max_wires} wires')
    if type(timeout_s) not in (float, int) or not 0 < timeout_s <= 30:
        raise ValueError('timeout_s must be in (0,30]')
    if type(max_evaluations) is not int or not 1 <= max_evaluations <= 1_000_000:
        raise ValueError('max_evaluations must be in 1..1000000')
    if type(restarts) is not int or not 0 <= restarts <= 64:
        raise ValueError('restarts must be in 0..64')
    if type(seed) is not int or not 0 <= seed <= (1 << 32)-1:
        raise ValueError('seed must be a uint32')
    n = net.edges
    deadline = monotonic() + timeout_s
    weights, incident = _factor_pair_weights(net)
    lb_pairs, lb_peak = collision_lower_bound(net, packet_size)
    original = tuple(range(n))
    original_score = collision_score(net, original, packet_size)
    incumbent = original
    incumbent_score = original_score
    total_evals = 0
    complete_passes = 0
    attempted = 0
    termination = 'all_restarts_completed'
    rng = Random(seed)

    candidate_orders = [original, _greedy_order(n, packet_size, weights)]
    for _ in range(restarts):
        order = list(range(n))
        rng.shuffle(order)
        candidate_orders.append(tuple(order))

    for start in candidate_orders:
        if monotonic() >= deadline or total_evals >= max_evaluations:
            termination = 'time_budget' if monotonic() >= deadline else 'evaluation_budget'
            break
        attempted += 1
        current = list(start)
        packet_count = (n + packet_size - 1) // packet_size
        packet_scores = [_block_score(tuple(current[i:i+packet_size]), weights, incident)
                         for i in range(0, n, packet_size)]
        total_pairs = sum(score[0] for score in packet_scores)
        total_peak = max((score[1] for score in packet_scores), default=0)
        if (total_pairs, total_peak) < incumbent_score:
            incumbent_score, incumbent = (total_pairs, total_peak), tuple(current)
        if incumbent_score == (lb_pairs, lb_peak):
            termination = 'global_lower_bound_attained'
            break
        # First-improvement coordinate descent. Only swap BETWEEN packets;
        # within-packet order has no effect on the mathematical objective.
        while True:
            improved = False
            for i in range(n):
                a = i // packet_size
                for j in range(i+1, n):
                    b = j // packet_size
                    if a == b:
                        continue
                    if total_evals >= max_evaluations or monotonic() >= deadline:
                        termination = 'evaluation_budget' if total_evals >= max_evaluations else 'time_budget'
                        break
                    total_evals += 1
                    current[i], current[j] = current[j], current[i]
                    score_a = _block_score(tuple(current[a*packet_size:(a+1)*packet_size]), weights, incident)
                    score_b = _block_score(tuple(current[b*packet_size:(b+1)*packet_size]), weights, incident)
                    new_pairs = total_pairs - packet_scores[a][0] - packet_scores[b][0] + score_a[0] + score_b[0]
                    if new_pairs <= total_pairs:
                        new_peak = max(score_a[1], score_b[1],
                                       *(packet_scores[p][1] for p in range(packet_count) if p not in (a,b))) if packet_count else 0
                    else:
                        new_peak = total_peak
                    if (new_pairs, new_peak) < (total_pairs, total_peak):
                        packet_scores[a], packet_scores[b] = score_a, score_b
                        total_pairs, total_peak = new_pairs, new_peak
                        improved = True
                        if (total_pairs, total_peak) < incumbent_score:
                            incumbent_score, incumbent = (total_pairs, total_peak), tuple(current)
                        break
                    current[i], current[j] = current[j], current[i]
                if improved or termination in ('time_budget','evaluation_budget'):
                    break
            if termination in ('time_budget','evaluation_budget'):
                break
            if not improved:
                complete_passes += 1
                break
            if incumbent_score == (lb_pairs, lb_peak):
                termination = 'global_lower_bound_attained'
                break
        if termination in ('global_lower_bound_attained','time_budget','evaluation_budget'):
            break

    # Recompute objective from the original factor incidence arrays (not the
    # cached pair-weight search structure).
    replayed = collision_score(net, incumbent, packet_size)
    if replayed != incumbent_score:
        raise AssertionError('incremental score differs from original factor score')
    globally_certified = incumbent_score == (lb_pairs, lb_peak)
    plan = PacketSchedule(incumbent, packet_size, original_score[0], incumbent_score[0],
                          original_score[1], incumbent_score[1], total_evals,
                          globally_certified, 'lower-bound-certified-search' if globally_certified
                          else 'bounded-multistart-local-search')
    evidence = PacketSearchEvidence('GLOBAL_LOWER_BOUND_WITH_BOUNDED_SEARCH',n, packet_size,
                    (n+packet_size-1)//packet_size, lb_pairs, lb_peak,
                    incumbent_score[0], incumbent_score[1],incumbent_score[0]-lb_pairs,
                    globally_certified,globally_certified,total_evals,complete_passes,
                    attempted,termination,True)
    return plan,evidence
