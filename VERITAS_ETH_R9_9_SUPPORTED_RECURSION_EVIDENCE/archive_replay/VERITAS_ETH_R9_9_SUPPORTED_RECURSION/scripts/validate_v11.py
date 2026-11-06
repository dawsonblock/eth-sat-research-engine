"""Repeatable independent small-instance Cauchy and packet validations."""
from __future__ import annotations

from random import Random
from pathlib import Path
from time import monotonic
import json

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract, eliminate
from veritas.research.packet_schedule import plan_packets, relabel_network, collision_score
from veritas.research.cauchy_elimination import eliminate_cauchy_jet
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod


def main():
    rng=Random(2026103011)
    t0=monotonic()
    count_checks = 0
    jet_checks = 0
    nonoptimized_jets = 0
    optimized_jets = 0
    for trial in range(500):
        n=rng.randrange(0,6)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            if not n:break
            idx=rng.sample(range(1,n+1),rng.randrange(0,min(n,3)+1))
            clauses.append([v if rng.randrange(2) else -v for v in idx])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>5:continue
        L=rng.choice((1,2,4))
        t=rng.randrange(-L,L)
        bits=rng.randrange(1,17)
        order=rng.randrange(1,8)
        optimized=(trial%2)==0
        result,stats=eliminate_cauchy_jet(net,packet_size=L,node=t,jet_order=order,
              precision_bits=bits,optimize_packets=optimized,timeout_s=6,
              elimination_order='natural' if trial%3==0 else 'min_fill')
        cnf_network=relabel_network(net,stats.packet_schedule.wire_order) if stats.packet_schedule else net
        expected,_=shifted_cauchy_jet_mod(cnf_network,packet_size=L,node=t,
             jet_order=order,precision_bits=bits,max_edges=6,timeout_s=6)
        assert result==expected,(n,clauses,L,t,bits,order,optimized)
        jet_checks+=1
        if optimized:optimized_jets+=1
        else:nonoptimized_jets+=1
        if optimized:
            schedule=stats.packet_schedule
            assert schedule.optimized_collisions<=schedule.original_collisions
            assert collision_score(net,schedule.wire_order,L)[0]==schedule.optimized_collisions
            assert brute_contract(net,max_edges=6)==eliminate(cnf_network)
            count_checks+=1
    assert jet_checks>=200 and count_checks>=90,(jet_checks,count_checks)
    data={
      'version':'1.1.0','status':'PASS','seed':2026103011,
      'independent_cauchy_jet_comparisons':jet_checks,
      'optimized_packet_jet_comparisons':optimized_jets,
      'unoptimized_jet_comparisons':nonoptimized_jets,
      'relabel_count_preservation_checks':count_checks,
      'upstream_D3_collision_packing_theorem':'NOT_IMPLEMENTED',
      'upstream_D4_weighted_mode_recursion':'NOT_IMPLEMENTED',
      'subexponential_runtime_claim':'NONE',
      'elapsed_seconds':round(monotonic()-t0,3)
    }
    dest=Path(__file__).resolve().parents[1]/'validation/validation_v11.json'
    dest.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    print(json.dumps(data,indent=2))

if __name__=='__main__':main()
