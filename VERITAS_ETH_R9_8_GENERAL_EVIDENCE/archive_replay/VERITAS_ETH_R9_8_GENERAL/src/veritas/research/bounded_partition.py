"""Certified-bound finite packet optimization for packet sizes 2, 4 and 8.

Finite proxy ONLY: partitions tensor wires into full packets plus an optional
final partial packet, minimizing (same-factor incidence pairs, worst incidence).
For a full block the collision objective is a sum of nonnegative pair weights.
An admissible per-vertex bound and canonical (least-wire) partition enumeration
permit exact branch-and-bound for small instances and a VALID feasible best
schedule plus a globally valid lower bound if interrupted.

Neither this combinatorial surrogate nor its runtime is the manuscript's
D.3 packing construction or the paper's subexponential recursion.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from time import monotonic

from veritas.research.tensor import TensorNetwork
from veritas.research.packet_schedule import PacketSchedule, collision_score


@dataclass(frozen=True)
class BoundedPartitionEvidence:
    algorithm: str
    wires: int
    packet_size: int
    objective: int
    max_incidence: int
    lower_bound_pairs: int
    absolute_gap_pairs: int
    finished_search: bool
    optimum_status: str
    visited_states: int
    tested_blocks: int
    pruned_states: int
    candidate_tail_packets: int
    independent_oracle_checked: bool
    oracle_pairs: int | None
    elapsed_ms: float


def pair_weights(net: TensorNetwork) -> tuple[tuple[int,...], ...]:
    """w[a,b] counts factors incident to both wires; purely combinatorial."""
    n=net.edges
    weights=[[0]*n for _ in range(n)]
    for factor in net.factors:
        for i,a in enumerate(factor.ports):
            for b in factor.ports[i+1:]:
                weights[a][b]+=1
                weights[b][a]+=1
    return tuple(tuple(row) for row in weights)


def partition_lower_bound(weights: tuple[tuple[int,...], ...], packet_size:int,
                          remaining:tuple[int,...]) -> int:
    """Admissible lower bound for partitions into full packet_size blocks.

    Every remaining vertex has exactly k-1 companions. The sum of the (k-1)
    cheapest available incident pair weights for each vertex, divided by two,
    is <= the total sum of within-packet pair weights. Use ceiling division.
    The empty case returns zero. The caller must supply a multiple of k.
    """
    if len(remaining)%packet_size:
        raise ValueError('full-packet lower bound requires a multiple of packet size')
    if not remaining:return 0
    if packet_size==1:return 0
    total=0
    for v in remaining:
        vals=sorted(weights[v][u] for u in remaining if u!=v)
        total+=sum(vals[:packet_size-1])
    return (total+1)//2


def block_score(net:TensorNetwork, members:tuple[int,...])->tuple[int,int]:
    members=set(members)
    pairs=0;peak=0
    for f in net.factors:
        k=sum(p in members for p in f.ports)
        pairs+=k*(k-1)//2
        peak=max(peak,k)
    return pairs,peak


def _initial_best(net:TensorNetwork,k:int,weights)->tuple[tuple[int,int],tuple[int,...]]:
    n=net.edges
    identity=tuple(range(n))
    best=(collision_score(net,identity,k),identity)
    # Greedy full-packet construction, with the last remainder kept separate.
    # This is only an upper bound, never treated as an optimality proof.
    remaining=list(range(n));order=[]
    while len(remaining)>=k:
        pivot=remaining[0]
        companions=tuple(sorted(remaining[1:],key=lambda u:(weights[pivot][u],u))[:k-1])
        chosen=(pivot,)+companions
        order.extend(chosen)
        chosen_set=set(chosen)
        remaining=[x for x in remaining if x not in chosen_set]
    order.extend(remaining)
    greedy=tuple(order)
    score=collision_score(net,greedy,k)
    if score<best[0]:best=(score,greedy)
    return best


def optimize_packets_bounded(net:TensorNetwork, *, packet_size:int=4,
                             max_wires:int=24, max_states:int=150_000,
                             max_blocks:int=1_000_000, timeout_s:float=5.0,
                             independent_check:bool=True)->tuple[PacketSchedule,BoundedPartitionEvidence]:
    if type(packet_size) is not int or packet_size not in (1,2,4,8):
        raise ValueError('packet_size must be 1, 2, 4 or 8')
    if type(max_wires) is not int or not 0<=max_wires<=24:
        raise ValueError('max_wires must be 0..24')
    if type(max_states) is not int or not 1<=max_states<=1_000_000:
        raise ValueError('max_states must be in 1..1000000')
    if type(max_blocks) is not int or not 1<=max_blocks<=5_000_000:
        raise ValueError('max_blocks must be in 1..5000000')
    if type(timeout_s) not in (float,int) or not 0<timeout_s<=30:
        raise ValueError('timeout_s must be in (0,30]')
    n=net.edges
    if n>max_wires:raise ValueError(f'bounded optimizer supports at most {max_wires} wires')
    start=monotonic();deadline=start+timeout_s
    baseline=collision_score(net,tuple(range(n)),packet_size)
    weights=pair_weights(net)
    (best_score,best_order)=_initial_best(net,packet_size,weights)
    visited=0;blocks=0;pruned=0;tails=0;aborted=False
    # The global root bound accounts for the possible final partial packet.
    # Enumerating every tail yields an admissible global lower bound.
    r=n%packet_size
    all_wires=tuple(range(n))
    if r:
        # Avoid exponential up-front tail enumeration when n is large.
        # Zero is globally admissible, though usually weaker.
        global_bound=0
    else:
        global_bound=partition_lower_bound(weights,packet_size,all_wires)

    def within_budget():
        return visited<max_states and blocks<max_blocks and monotonic()<=deadline

    current_tail:tuple[int,...]=()

    def search(remaining:tuple[int,...],chosen:tuple[int,...],
               running_pairs:int,running_peak:int):
        nonlocal visited,blocks,pruned,aborted,best_score,best_order
        if not within_budget():
            aborted=True
            return
        visited+=1
        # All remaining blocks are full; bound is valid by construction.
        lb=partition_lower_bound(weights,packet_size,remaining)
        if running_pairs+lb>best_score[0] or (
            running_pairs+lb==best_score[0] and running_peak>=best_score[1]
        ):
            pruned+=1
            return
        if not remaining:
            candidate=(running_pairs,running_peak)
            if candidate<best_score:
                best_score=candidate
                best_order=chosen+current_tail
            return
        pivot=remaining[0]
        options=[]
        for comp in combinations(remaining[1:],packet_size-1):
            # Limit candidate materialization as well as recursive exploration.
            # A timed-out search returns a feasible incumbent, never a false
            # mathematical optimality claim.
            if len(options)+blocks>=max_blocks or len(options)>=200_000 or monotonic()>deadline:
                aborted=True
                return
            block=(pivot,)+comp
            local=block_score(net,block)
            options.append((local,block))
        options.sort(key=lambda entry:(entry[0],entry[1]))
        for local,block in options:
            if not within_budget():
                aborted=True
                return
            blocks+=1
            selected=set(block)
            rest=tuple(v for v in remaining if v not in selected)
            search(rest,chosen+block,running_pairs+local[0],max(running_peak,local[1]))
            if aborted:return

    # Iterate every possible trailing partial block. Canonical least-wire
    # anchored enumeration avoids packet-permutation duplication.
    if not r:
        search(all_wires,(),0,0)
    else:
        for tail in combinations(all_wires,r):
            if not within_budget():
                aborted=True
                break
            tails+=1
            current_tail=tail
            tail_set=set(tail)
            remaining=tuple(v for v in all_wires if v not in tail_set)
            local=block_score(net,tail)
            # Lower bound can be tightened incrementally without compromising
            # global validity: we never use incomplete tail enumeration as a
            # proof of a global bound.
            search(remaining,(),local[0],local[1])
            if not aborted and (score:=collision_score(net,best_order,packet_size))!=best_score:
                raise AssertionError('intermediate score mismatch')
            if aborted:break
            # Store tail to be added after all full packets; only update on a
            # full solution. The recursion uses chosen+tail via closure below.

    optimum=not aborted
    if collision_score(net,best_order,packet_size)!=best_score:
        raise AssertionError('optimized schedule failed independent score replay')
    oracle_ok=False; oracle_pairs=None
    if independent_check and n<=12 and optimum:
        from veritas.research.optimal_packets import optimize_packets_exact,PacketPlanningLimit
        try:
            oracle,_=optimize_packets_exact(net,packet_size=packet_size,max_wires=16,
                        timeout_s=5,max_states=500000,max_transitions=10000000)
            oracle_pairs=oracle.optimized_collisions
            if (oracle.optimized_collisions,oracle.optimized_max_incidence)!=best_score:
                raise AssertionError('independent subset DP disagreed with bounded optimizer')
            oracle_ok=True
        except PacketPlanningLimit:
            pass
    if optimum:
        lower=best_score[0]
    else:
        lower=global_bound
    if lower>best_score[0]:raise AssertionError('invalid global collision lower bound')
    evidence=BoundedPartitionEvidence(
       'FINITE_PACKET_BRANCH_AND_BOUND',n,packet_size,best_score[0],best_score[1],
       lower,best_score[0]-lower,optimum,
       'INDEPENDENT_SUBSET_DP' if oracle_ok else (
          'EXHAUSTIVE_SEARCH_COMPLETED_INTERNAL' if optimum else 'FEASIBLE_SCHEDULE_WITH_ADMISSIBLE_BOUND'),
       visited,blocks,pruned,tails,oracle_ok,oracle_pairs,
       round((monotonic()-start)*1000,3))
    plan=PacketSchedule(best_order,packet_size,baseline[0],best_score[0],
       baseline[1],best_score[1],blocks,optimum,
       'finite-packet-branch-and-bound')
    return plan,evidence
