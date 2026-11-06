"""Independent, pure verifier of scalable packet-search lower-bound claims."""
from __future__ import annotations

from veritas.research.tensor import TensorNetwork
from veritas.research.packet_schedule import PacketSchedule
from veritas.research.scalable_packets import PacketSearchEvidence


def check_packet_search_evidence(net: TensorNetwork, plan: PacketSchedule,
                                 proof: PacketSearchEvidence) -> tuple[bool, str]:
    """Check permutation, attained score, and convex per-factor lower bound.

    This checker intentionally does NOT call the optimizer or collision_score.
    It constructs factor incidences directly and computes the independent
    lower bound by greedy assignment of d indistinguishable balls to p bins.
    It certifies *global* optimality only when score == lower bound exactly.
    """
    n = net.edges
    k = plan.packet_size
    if type(k) is not int or k not in (1, 2, 4, 8):
        return False, 'invalid packet size'
    if len(plan.wire_order) != n or set(plan.wire_order) != set(range(n)):
        return False, 'invalid permutation'
    p = (n+k-1)//k
    if (proof.wires, proof.packet_size, proof.packets) != (n,k,p):
        return False, 'mismatched network metadata'
    where = {wire: pos//k for pos,wire in enumerate(plan.wire_order)}
    actual_pairs = 0
    actual_peak = 0
    lower_pairs = 0
    lower_peak = 0
    for factor in net.factors:
        freq = [0]*p
        for v in factor.ports:
            freq[where[v]] += 1
        actual_pairs += sum(t*(t-1)//2 for t in freq)
        actual_peak = max(actual_peak,*freq,0)
        # Independent balanced-allocation proof: each ball is placed into a
        # bin with the least occupancy, which minimizes total pair increments.
        occupancy = [0]*p
        for _ in factor.ports:
            if not occupancy:
                return False, 'nonempty factor with zero packets'
            b = min(range(p), key=lambda idx: occupancy[idx])
            lower_pairs += occupancy[b]
            occupancy[b] += 1
        lower_peak = max(lower_peak,*occupancy,0)
    reached = actual_pairs == lower_pairs and actual_peak == lower_peak
    if (proof.pair_lower_bound, proof.peak_lower_bound,proof.achieved_pairs,proof.achieved_peak,
        proof.pair_gap,proof.full_lower_bound_matched,proof.exact_optimum_certified) != (
        lower_pairs,lower_peak,actual_pairs,actual_peak,actual_pairs-lower_pairs,reached,reached):
        return False, 'reported bounds/optimality contradict independent replay'
    if (plan.optimized_collisions,plan.optimized_max_incidence,plan.exact_optimum) != (
        actual_pairs,actual_peak,reached):
        return False, 'plan score or exactness is incorrect'
    if proof.objective_replayed is not True:
        return False, 'reported replay flag is false'
    return True, 'LOWER_BOUND_ATTAINED' if reached else 'FEASIBLE_ONLY_GLOBAL_GAP_UNRESOLVED'
