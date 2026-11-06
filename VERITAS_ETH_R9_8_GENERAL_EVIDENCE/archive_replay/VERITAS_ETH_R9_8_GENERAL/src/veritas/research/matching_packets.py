"""Exact finite packet-pair minimization via minimum weight perfect matching.

For packet_size=2, the incidence-collision objective equals sum of pairwise
weights w(i,j), where w(i,j) is the number of factors containing both wires.
The optimum partition is a minimum-weight perfect matching of the complete
weighted wire graph. If the number of wires is odd, a zero-weight dummy is
introduced and removed after solving, leaving one singleton packet.

The second lexicographic objective (peak factor incidence per packet) is
fixed by the first: it is 2 iff any positive-weight pair is present, else 1
for a nonempty wire network. Thus minimum weight matching is sufficient.

This solves ONLY the v1.1 finite incidence-collision surrogate. The manuscript
D.3 theorem does NOT reduce to this statement, and no ETH runtime guarantee
follows. networkx's blossom algorithm is a trusted implementation, not an
independently checked optimality certificate for large networks.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from veritas.research.packet_schedule import PacketSchedule, collision_score
from veritas.research.tensor import TensorNetwork
from veritas.research.scalable_packets import collision_lower_bound


class MatchingDependencyMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class MatchingEvidence:
    algorithm: str
    wires: int
    pairs: int
    dummy_used: bool
    pair_objective: int
    maximum_incidence: int
    lower_bound_pairs: int
    optimality_claim: str
    replay_matches: bool
    oracle_checked: bool
    oracle_objective: int | None
    elapsed_ms: float
    # The optional exhaustive DP cross-check applies only for <=16 wires.


def _pair_weights(net: TensorNetwork) -> list[list[int]]:
    n=net.edges
    weight=[[0]*n for _ in range(n)]
    for factor in net.factors:
        ports=factor.ports
        for i, a in enumerate(ports):
            for b in ports[i+1:]:
                weight[a][b]+=1
                weight[b][a]+=1
    return weight


def optimize_packets_matching(net: TensorNetwork, *, max_wires: int=128,
                              independent_check: bool=True) -> tuple[PacketSchedule, MatchingEvidence]:
    """Compute a global optimum of the finite collision objective for k=2.

    Memory O(n^2) and polynomial-time blossom matching. max_wires protects
    browser-facing callers from unexpectedly large planning jobs. No timeout
    guarantee is offered for the third-party matching call; callers should
    enforce a deadline at the process boundary for untrusted workloads.
    """
    if type(max_wires) is not int or not 0 <= max_wires <= 256:
        raise ValueError('max_wires must be in 0..256')
    n=net.edges
    if n>max_wires:
        raise ValueError(f'matching optimizer supports <= {max_wires} wires, got {n}')
    try:
        import networkx as nx
    except ImportError as exc:
        raise MatchingDependencyMissing('install the optional matching dependency: pip install -e ".[matching]"') from exc
    t0=monotonic()
    weights=_pair_weights(net)
    graph=nx.Graph()
    dummy=n if n%2 else None
    graph.add_nodes_from(range(n+(dummy is not None)))
    for a in range(n):
        for b in range(a+1,n):
            graph.add_edge(a,b,weight=weights[a][b])
    if dummy is not None:
        for a in range(n):
            graph.add_edge(a,dummy,weight=0)
    matching=nx.algorithms.matching.min_weight_matching(graph,weight='weight')
    expected=(n+int(dummy is not None))//2
    if len(matching)!=expected:
        raise AssertionError('non-perfect blossom matching returned')
    seen=set()
    pairs=[]
    singleton=[]
    for a,b in matching:
        if a in seen or b in seen:raise AssertionError('matching repeated vertex')
        seen.update((a,b))
        if a==dummy or b==dummy:
            singleton.append(b if a==dummy else a)
        else:
            pairs.append(tuple(sorted((a,b))))
    if seen!=set(graph.nodes): raise AssertionError('matching did not cover all vertices')
    if len(singleton)!=(n%2):raise AssertionError('incorrect dummy matching')
    pairs.sort()
    order=tuple(v for pair in pairs for v in pair)+tuple(singleton)
    identity=tuple(range(n))
    initial=collision_score(net,identity,2)
    score=collision_score(net,order,2)
    calculated=sum(weights[a][b] for a,b in pairs)
    if calculated!=score[0]:raise AssertionError('matching score disagrees with direct factor replay')
    # In a k=2 partition, a colliding pair has exactly two occurrences of
    # some factor in that packet. Otherwise the peak is 1 if n>0, or 0.
    predicted_peak=2 if calculated else (1 if n else 0)
    if score[1]!=predicted_peak:raise AssertionError('lexicographic peak identity violated')
    if score>initial:raise AssertionError('matching returned score worse than identity')
    independent=False
    oracle=None
    if independent_check and n<=16:
        from veritas.research.optimal_packets import optimize_packets_exact
        from veritas.research.optimal_packets import PacketPlanningLimit
        try:
            check,_=optimize_packets_exact(net,packet_size=2,
                         timeout_s=5,max_states=500000,max_transitions=10000000)
        except PacketPlanningLimit:
            # Missing independent oracle is explicit; matching remains an
            # algorithmic optimum, not an independently checked certificate.
            pass
        else:
            oracle=check.optimized_collisions
            if (check.optimized_collisions,check.optimized_max_incidence)!=score:
                raise AssertionError('matching disagreed with independent exact subset DP')
            independent=True
    lb,_=collision_lower_bound(net,2)
    plan=PacketSchedule(order,2,initial[0],score[0],initial[1],score[1],
                        graph.number_of_edges(),True,'minimum-weight-perfect-matching')
    proof=MatchingEvidence('NETWORKX_BLOSSOM_MIN_WEIGHT_PERFECT_MATCHING',n,len(pairs),dummy is not None,
                          score[0],score[1],lb,
                          'INDEPENDENT_SUBSET_DP_CROSSCHECK' if independent else 'ALGORITHM_OPTIMUM_UNCERTIFIED_EXTERNAL_SOLVER',
                          True,independent,oracle,round((monotonic()-t0)*1000,3))
    return plan,proof
