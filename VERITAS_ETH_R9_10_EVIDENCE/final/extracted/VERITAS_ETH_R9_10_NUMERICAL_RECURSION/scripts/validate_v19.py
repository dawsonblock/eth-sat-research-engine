"""Deterministic independent global bound oracle and scalable stress validation."""
from __future__ import annotations
from itertools import permutations
from random import Random
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, eliminate
from veritas.research.packet_schedule import collision_score, relabel_network
from veritas.research.scalable_packets import optimize_packets_scalable, collision_lower_bound
from veritas.research.packet_bound_checker import check_packet_search_evidence

rng = Random(191919)
tested_oracles = 0
certified = 0
uncertified = 0
relabel_count_checks = 0
for case in range(130):
    n = rng.randint(0,4)
    clauses=[]
    for _ in range(rng.randint(0,5)):
        w=rng.randint(0,min(n,3))
        clauses.append([v*(1 if rng.getrandbits(1) else -1)
                        for v in rng.sample(range(1,n+1),w)])
    cnf=CNF.from_lists(n,clauses)
    net=from_cnf(cnf)
    if net.edges>7: continue
    for k in (1,2,4,8):
        lower=collision_lower_bound(net,k)
        oracle=min(collision_score(net,order,k) for order in permutations(range(net.edges)))
        assert lower<=oracle
        result,proof=optimize_packets_scalable(net,packet_size=k,max_evaluations=1600,restarts=3,seed=case)
        ok,reason=check_packet_search_evidence(net,result,proof)
        assert ok,reason
        assert oracle <= (result.optimized_collisions,result.optimized_max_incidence)
        if proof.exact_optimum_certified:
            assert oracle == (result.optimized_collisions,result.optimized_max_incidence)
            certified += 1
        else:uncertified+=1
        tested_oracles+=1
        if net.edges<=7 and k==2:
            assert eliminate(net)==eliminate(relabel_network(net,result.wire_order))
            relabel_count_checks+=1

large=[]
for case in range(8):
    n=40+case*5
    clauses=[[((j*7)%n)+1,((j*7+13)%n)+1] for j in range(32+case*4)]
    net=from_cnf(CNF.from_lists(n,clauses),max_degree=12)
    result,proof=optimize_packets_scalable(net,packet_size=4,max_evaluations=2000,restarts=2,seed=case)
    assert check_packet_search_evidence(net,result,proof)[0]
    assert result.optimized_collisions <= result.original_collisions
    large.append({'wires':net.edges,'before':result.original_collisions,
                  'after':result.optimized_collisions,'lower_bound':proof.pair_lower_bound,
                  'certified_optimal':proof.exact_optimum_certified,'search_swaps':proof.candidate_swaps})

output={'status':'PASS','oracle_score_cases':tested_oracles,'finite_lower_bound_optima_certified':certified,
        'finite_bound_not_attained':uncertified,'small_relabel_count_checks':relabel_count_checks,
        'large_networks':large,
        'disclaimer':'Finite surrogate packet objective; no manuscript D.3 packing theorem or subexponential algorithm.'}
p=Path(__file__).resolve().parents[1]/'validation'/'validation_v19.json'
p.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
