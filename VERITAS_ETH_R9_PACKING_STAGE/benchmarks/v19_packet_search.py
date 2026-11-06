"""Deterministic packet-search *planner* benchmark; NOT a SAT performance test."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.packet_schedule import plan_packets
from veritas.research.scalable_packets import optimize_packets_scalable
from veritas.research.packet_bound_checker import check_packet_search_evidence

cases=[]
for size in (16,32,64,96,128):
    n=size//2
    clauses=[[((j*7)%n)+1,((j*7+5)%n)+1] for j in range(n)]
    net=from_cnf(CNF.from_lists(n,clauses),max_degree=12)
    p=4
    if net.edges<=16:
        t0=perf_counter()
        legacy=plan_packets(net,packet_size=p,max_permutations=4000,timeout_s=2)
        legacy_s=perf_counter()-t0
        old={'score':legacy.optimized_collisions,'seconds':legacy_s}
    else:old=None
    t0=perf_counter()
    result,proof=optimize_packets_scalable(net,packet_size=p,max_evaluations=10000,
                                           restarts=3,timeout_s=3,seed=222)
    elapsed=perf_counter()-t0
    assert check_packet_search_evidence(net,result,proof)[0]
    cases.append({'wires':net.edges,'packet_size':p,'baseline':result.original_collisions,
                  'scalable':result.optimized_collisions,'lower_bound':proof.pair_lower_bound,
                  'proven_surrogate_optimum':proof.exact_optimum_certified,'evaluations':proof.candidate_swaps,
                  'elapsed_seconds':round(elapsed,6),'legacy':old})
print(json.dumps({'benchmarks':cases,'warning':'Single-run planner-only timing; no proof of faster end-to-end SAT or ETH asymptotics.'},indent=2))
