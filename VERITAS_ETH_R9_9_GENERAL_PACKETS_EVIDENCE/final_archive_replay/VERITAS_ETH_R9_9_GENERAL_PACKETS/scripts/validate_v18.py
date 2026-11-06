"""Reproducible independent tests for v1.8 finite packet partition DP."""
from __future__ import annotations
from itertools import permutations
from random import Random
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract, eliminate
from veritas.research.packet_schedule import collision_score, relabel_network, plan_packets
from veritas.research.optimal_packets import optimize_packets_exact

rng=Random(18002026)
independent=0
relabel=0
compared=0
improved=0
for _ in range(160):
    n=rng.randrange(0,5)
    clauses=[]
    if n:
        for _ in range(rng.randrange(0,5)):
            k=rng.randrange(0,min(3,n)+1)
            clauses.append([v if rng.randrange(2) else -v for v in rng.sample(range(1,n+1),k)])
    net=from_cnf(CNF.from_lists(n,clauses))
    if net.edges>7: continue
    for packet_size in (1,2,4,8):
        plan,proof=optimize_packets_exact(net,packet_size=packet_size,timeout_s=10)
        expected=min((collision_score(net,order,packet_size),order)
                     for order in permutations(range(net.edges)))
        assert (plan.optimized_collisions,plan.optimized_max_incidence,plan.wire_order)==(*expected[0],expected[1])
        assert proof.independent_score_replayed
        independent+=1
        if net.edges<=6:
            assert brute_contract(net,max_edges=6)==eliminate(relabel_network(net,plan.wire_order))
            relabel+=1
# Check exact search extends well beyond the legacy exhaustive 8-wire limit.
fixed=from_cnf(CNF.from_lists(8,[[1,2,3],[-1,4],[2,-3,5],[-2,6],[3,7],[-4,8,1]]))
assert fixed.edges==15
for k in (2,4,8):
    optimized,proof=optimize_packets_exact(fixed,packet_size=k,timeout_s=10)
    legacy=plan_packets(fixed,packet_size=k,timeout_s=3)
    assert (optimized.optimized_collisions,optimized.optimized_max_incidence) <= (legacy.optimized_collisions,legacy.optimized_max_incidence)
    if optimized.optimized_collisions<legacy.optimized_collisions: improved+=1
    assert proof.certificate_type=='RECOMPUTABLE_EXHAUSTIVE_SUBSET_RECURRENCE'
    compared+=1
print(json.dumps({'status':'PASS','independent_exhaustive_optima':independent,
                  'count_preserving_relabel_checks':relabel,'fifteen_wire_comparisons':compared,
                  'strict_collision_improvements':improved,
                  'scope':'finite optimizer for a surrogate incidence score; NOT paper D.3'},indent=2))
