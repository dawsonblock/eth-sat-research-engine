"""Reproducible comparison of finite packet scores, with planning time separated."""
from random import Random
from time import perf_counter
import json
from veritas.research.tensor import TensorNetwork, Factor
from veritas.research.matching_packets import optimize_packets_matching
from veritas.research.scalable_packets import optimize_packets_scalable


def randomized_cycle(n:int,seed:int):
    rng=Random(seed)
    positions=list(range(n));rng.shuffle(positions)
    # A cycle has every wire in exactly two 2-ary factors.
    factors=tuple(Factor((positions[i],positions[(i+1)%n]),(1,1,1,1),f'f{i}') for i in range(n))
    return TensorNetwork(n,factors)

rows=[]
for wires in (32,64,96,128):
    net=randomized_cycle(wires,20261030+wires)
    a=perf_counter(); matching,proof=optimize_packets_matching(net,independent_check=False)
    match_ms=round((perf_counter()-a)*1000,3)
    b=perf_counter(); heuristic,heur_proof=optimize_packets_scalable(net,packet_size=2,
                   timeout_s=5,max_evaluations=3000,restarts=2,seed=20261030)
    heur_ms=round((perf_counter()-b)*1000,3)
    assert matching.optimized_collisions<=heuristic.optimized_collisions
    rows.append({'wires':wires,'matching_pairs':matching.optimized_collisions,
                 'heuristic_pairs':heuristic.optimized_collisions,
                 'matching_plan_ms':match_ms,'heuristic_plan_ms':heur_ms,
                 'note':'surrogate plan only; not SAT counting throughput'})
print(json.dumps({'seed':20261030,'rows':rows},indent=2))
