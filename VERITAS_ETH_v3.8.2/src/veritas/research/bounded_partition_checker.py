"""Independent finite packet-collision replay and bound verification.

No claim is made to independently certify completion of large branch-and-
bound searches: only small independent subset-DP instances can support that.
"""
from __future__ import annotations
from veritas.research.tensor import TensorNetwork
from veritas.research.packet_schedule import PacketSchedule
from veritas.research.bounded_partition import BoundedPartitionEvidence


def verify_bounded_partition(net: TensorNetwork, plan:PacketSchedule,
                             evidence:BoundedPartitionEvidence)->tuple[bool,str]:
    n=net.edges; k=plan.packet_size
    if k not in (1,2,4,8) or evidence.packet_size!=k or evidence.wires!=n:
        return False,'invalid packet size or count'
    if len(plan.wire_order)!=n or set(plan.wire_order)!=set(range(n)):
        return False,'invalid wire order'
    if plan.algorithm!='finite-packet-branch-and-bound' or evidence.algorithm!='FINITE_PACKET_BRANCH_AND_BOUND':
        return False,'unexpected method'
    # Replay the score directly from incidence tables, not optimizer pair weights.
    def score(order):
        groups={wire:pos//k for pos,wire in enumerate(order)}
        total=0; peak=0
        for factor in net.factors:
            counts={}
            for v in factor.ports:
                slot=groups[v]
                counts[slot]=counts.get(slot,0)+1
            for x in counts.values():
                total+=x*(x-1)//2
                peak=max(peak,x)
        return total,peak
    best=score(plan.wire_order); initial=score(tuple(range(n)))
    if best!=(plan.optimized_collisions,plan.optimized_max_incidence) or initial!=(plan.original_collisions,plan.original_max_incidence):
        return False,'replayed objective does not match plan'
    if (evidence.objective,evidence.max_incidence)!=best or best>initial:
        return False,'evidence claims incorrect score'
    if not(0<=evidence.lower_bound_pairs<=best[0]) or evidence.absolute_gap_pairs!=best[0]-evidence.lower_bound_pairs:
        return False,'invalid lower bound or gap'
    if evidence.finished_search!=plan.exact_optimum:
        return False,'contradictory optimality flags'
    if evidence.finished_search:
        if evidence.lower_bound_pairs!=best[0] or evidence.optimum_status not in ('INDEPENDENT_SUBSET_DP','EXHAUSTIVE_SEARCH_COMPLETED_INTERNAL'):
            return False,'unsupported completed-search claim'
    else:
        if evidence.optimum_status!='FEASIBLE_SCHEDULE_WITH_ADMISSIBLE_BOUND':
            return False,'unsupported incomplete-search claim'
        # An independently derived root bound is available when all packets
        # have equal size. With a partial packet, zero remains admissible.
        if n%k:
            if evidence.lower_bound_pairs!=0:
                return False,'nonzero partial-packet lower bound not justified'
        else:
            remaining=tuple(range(n))
            def weights_for(v,u):
                return sum(v in factor.ports and u in factor.ports for factor in net.factors)
            root=0
            for v in remaining:
                root+=sum(sorted(weights_for(v,u) for u in remaining if u!=v)[:k-1])
            root=(root+1)//2
            if evidence.lower_bound_pairs!=root:
                return False,'root lower bound mismatch'
    if evidence.independent_oracle_checked:
        if not evidence.finished_search or n>12 or evidence.optimum_status!='INDEPENDENT_SUBSET_DP':
            return False,'unsupported independent optimum assertion'
        from veritas.research.optimal_packets import optimize_packets_exact,PacketPlanningLimit
        try:
            oracle,_=optimize_packets_exact(net,packet_size=k,timeout_s=5,max_states=500000,max_transitions=10000000)
        except PacketPlanningLimit:
            return False,'independent oracle unavailable'
        if (oracle.optimized_collisions,oracle.optimized_max_incidence)!=best or evidence.oracle_pairs!=best[0]:
            return False,'independent optimality mismatch'
        return True,'SCORE_BOUND_AND_INDEPENDENT_DP_OPTIMUM_REPLAYED'
    if evidence.oracle_pairs is not None or evidence.optimum_status=='INDEPENDENT_SUBSET_DP':
        return False,'forged independent oracle evidence'
    return True,'FEASIBLE_SCORE_AND_ADMISSIBLE_BOUND_REPLAYED; LARGE_OPTIMALITY_NOT_INDEPENDENTLY_CERTIFIED'
