"""Deterministic independent v1.0 research differential validation."""
from __future__ import annotations

import json
from pathlib import Path
from random import Random
from time import monotonic

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract, eliminate
from veritas.research.recursive_separator import recursive_contract, separator_plan
from veritas.research.grouped_cauchy import grouped_cauchy_jet_mod, group_cauchy_modes
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod


def main() -> None:
    rng=Random(100020261029)
    start=monotonic()
    exact=modular=jets=rank_cases=0
    for trial in range(550):
        n=rng.randrange(0,6)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            width=rng.randrange(0,min(n,3)+1)
            vars=rng.sample(list(range(1,n+1)),width)
            clauses.append([x if rng.randrange(2) else -x for x in vars])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>10:continue
        oracle=brute_contract(net,max_edges=10)
        actual,stats=recursive_contract(net,leaf_factors=2,max_cut_edges=12)
        assert actual==oracle,(n,clauses,actual,oracle)
        exact+=1
        bits=rng.randrange(1,17)
        residue,_=recursive_contract(net,modulus=1<<bits,max_cut_edges=12)
        assert residue==oracle%(1<<bits)
        modular+=1
        if net.edges<=5:
            L=rng.choice((1,2,4))
            node=rng.randrange(-L,L)
            span=rng.randrange(1,L+1)
            order=rng.randrange(1,8)
            jet,modes,info=grouped_cauchy_jet_mod(net,packet_size=L,node=node,
                    group_span=span,precision_bits=bits,jet_order=order)
            independent,_=shifted_cauchy_jet_mod(net,packet_size=L,node=node,
                    precision_bits=bits,jet_order=order,max_edges=6)
            assert jet==independent,(n,clauses,L,node,span,order)
            jets+=1
            assert info.rank_one_modes==len(modes)
            rank_cases+=1
    assert exact>=300 and modular==exact and jets>=200,(exact,modular,jets)
    result={'version':'1.0.0','status':'PASS','seed':100020261029,
            'recursive_vs_independent_edge_enumeration':exact,
            'recursive_modular_vs_independent_edge_enumeration':modular,
            'grouped_cauchy_vs_independent_shifted_jets':jets,
            'exact_rational_rank_decomposition_cases':rank_cases,
            'paper_specific_recursive_mode_bound':'NOT_IMPLEMENTED',
            'runtime_improvement_claim':'NONE',
            'elapsed_seconds':round(monotonic()-start,3)}
    from _evidence import evidence_path, write_evidence
    write_evidence(evidence_path('validation/validation_v10.json',
                                 root=Path(__file__).resolve().parents[1]),
                   json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
