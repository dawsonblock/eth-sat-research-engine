"""Reproducible randomized independent Cauchy-jet differential validations."""
import json
from pathlib import Path
from random import Random
from time import perf_counter
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
from veritas.research.weighted_children import recursive_weighted_jet


def main():
    start=perf_counter()
    rng=Random(20261030)
    checked=0
    tested_drops=0
    max_join=0
    for case in range(260):
        n=rng.randrange(0,5)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            if not n:break
            width=rng.randrange(0,min(n,3)+1)
            vs=rng.sample(range(1,n+1),width)
            clauses.append([v if rng.randrange(2) else -v for v in vs])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>6:continue
        packet=rng.choice((1,2,4))
        node=rng.randrange(-packet,packet)
        order=rng.randrange(1,7)
        precision=rng.choice((1,2,3,8,12,24))
        span=rng.randrange(1,packet+1)
        result,modes,stats=recursive_weighted_jet(net,packet_size=packet,node=node,
                        group_span=span,jet_order=order,precision_bits=precision,timeout_s=8)
        oracle,_=shifted_cauchy_jet_mod(net,packet_size=packet,node=node,
                          precision_bits=precision,jet_order=order,max_edges=6,timeout_s=8)
        assert result==oracle,(case,n,clauses,packet,node,order,precision)
        checked+=1
        tested_drops+=stats.dropped_rank_one_modes
        max_join=max(max_join,stats.max_join_variables)
    assert checked>=170, checked
    report={'version':'v1.2.0','seed':20261030,'cross_checked_cases':checked,
            'certified_mode_drops':tested_drops,'max_join_variables':max_join,
            'elapsed_seconds':round(perf_counter()-start,3),
            'status':'PASS','scope':'bounded finite-instance differential tests; not a proof of ETH runtime'}
    from _evidence import evidence_path, write_evidence
    write_evidence(evidence_path('validation/validation_v12.json',
                                 root=Path(__file__).resolve().parents[1]),
                   json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
