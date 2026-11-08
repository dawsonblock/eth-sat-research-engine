"""Independent replay and small-instance optimum cross-check for pair matching.

For >16 wires, we verify feasibility, the factor incidence score, and the
reported metadata, NOT the internals of the external blossom algorithm.
The finite global optimum for large inputs is a theorem-backed algorithmic
claim, not a self-contained independently checkable proof certificate.
"""
from __future__ import annotations
from veritas.research.tensor import TensorNetwork
from veritas.research.packet_schedule import PacketSchedule
from veritas.research.matching_packets import MatchingEvidence


def verify_matching_evidence(net: TensorNetwork, plan: PacketSchedule,
                             evidence: MatchingEvidence) -> tuple[bool,str]:
    n=net.edges
    order=plan.wire_order
    if plan.packet_size!=2 or len(order)!=n or set(order)!=set(range(n)):
        return False,'invalid matching schedule'
    if not plan.exact_optimum or plan.algorithm!='minimum-weight-perfect-matching':
        return False,'invalid claimed algorithm'
    if evidence.algorithm!='NETWORKX_BLOSSOM_MIN_WEIGHT_PERFECT_MATCHING':
        return False,'unexpected algorithm identifier'
    if evidence.wires!=n or evidence.pairs!=n//2 or evidence.dummy_used!=(n%2==1):
        return False,'mismatched metadata'
    # Deliberately use per-factor frequencies, not the optimizer's weights.
    def score(candidate):
        location={v:j//2 for j,v in enumerate(candidate)}
        pairs=0
        peak=0
        for f in net.factors:
            frequencies={}
            for v in f.ports:
                j=location[v]
                frequencies[j]=frequencies.get(j,0)+1
            for count in frequencies.values():
                pairs+=count*(count-1)//2
                peak=max(peak,count)
        return pairs,peak
    actual=score(order)
    baseline=score(tuple(range(n)))
    if actual!=(plan.optimized_collisions,plan.optimized_max_incidence):
        return False,'replayed score differs from plan'
    if baseline!=(plan.original_collisions,plan.original_max_incidence):
        return False,'baseline score differs'
    if (evidence.pair_objective,evidence.maximum_incidence)!=actual or not evidence.replay_matches:
        return False,'reported objective differs'
    if actual[1]!=(2 if actual[0] else (1 if n else 0)):
        return False,'invalid pairing peak identity'
    from veritas.research.scalable_packets import collision_lower_bound
    lower,_=collision_lower_bound(net,2)
    if evidence.lower_bound_pairs!=lower or actual[0]<lower:
        return False,'invalid lower bound'
    if actual>baseline:return False,'schedule worse than identity'
    if n<=16 and evidence.oracle_checked:
        from veritas.research.optimal_packets import optimize_packets_exact, PacketPlanningLimit
        try:
            oracle,_=optimize_packets_exact(net,packet_size=2,timeout_s=5,
                         max_states=500000,max_transitions=10000000)
        except PacketPlanningLimit:
            return False,'reported DP cross-check not reproducible'
        if (oracle.optimized_collisions,oracle.optimized_max_incidence)!=actual:
            return False,'independent optimum disagreement'
        if evidence.oracle_objective!=actual[0] or evidence.optimality_claim!='INDEPENDENT_SUBSET_DP_CROSSCHECK':
            return False,'independent optimum metadata mismatch'
        return True,'MATCHING_FEASIBLE_AND_INDEPENDENT_DP_OPTIMUM'
    if evidence.oracle_checked or evidence.oracle_objective is not None or evidence.optimality_claim!='ALGORITHM_OPTIMUM_UNCERTIFIED_EXTERNAL_SOLVER':
        return False,'unsupported oracle assertion'
    return True,'FEASIBLE_SCORE_CHECKED_EXTERNAL_OPTIMALITY_ALGORITHM'
