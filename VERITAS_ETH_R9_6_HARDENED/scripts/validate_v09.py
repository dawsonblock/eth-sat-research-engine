"""Independent seeded audit for new v0.9 modular Hermite and cross-mode methods."""
import json
from pathlib import Path
from random import Random
from time import monotonic
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
from veritas.research.cauchy_modes import cauchy_modes_at_node
from veritas.research.hermite_ring import hermite_plan, reconstruct_mod


def main():
    rng=Random(20091029)
    start=monotonic()
    checks=0
    prune_val=0
    prune_z=0
    hermites=0
    for trial in range(220):
        n=rng.randrange(0,6)
        m=rng.randrange(0,5)
        clauses=[]
        for _ in range(m):
            k=rng.randrange(0,3) if n else 0
            clauses.append([rng.choice((-1,1))*rng.randrange(1,n+1) for _ in range(k)])
        M=sum(map(len,clauses))
        if M>5: continue
        net=from_cnf(CNF.from_lists(n,clauses))
        L=rng.choice((1,2,4))
        t=rng.randrange(-L,L)
        p=rng.randrange(1,17)
        order=rng.randrange(1,10)
        modes,_,stats=cauchy_modes_at_node(net,packet_size=L,node=t,
             precision_bits=p,jet_order=order,max_edges=5)
        full,_=shifted_cauchy_jet_mod(net,packet_size=L,node=t,
             precision_bits=p,jet_order=order,max_edges=5)
        assert modes==full, (clauses,L,t,p,order)
        checks+=1
        prune_val+=stats.dropped_by_valuation
        prune_z+=stats.dropped_by_z_degree
        if M<=4 and L in (1,2) and hermites<95:
            degree=M*(2*L-1)
            nodes=[u for u in range(-L,L) if u!=0]
            mult=(degree+len(nodes))//len(nodes)
            plan=hermite_plan([(u,mult) for u in nodes],alpha=2*L,degree_bound=degree)
            bits=12+plan.guard_bits
            jets=[shifted_cauchy_jet_mod(net,packet_size=L,node=u,
                  precision_bits=bits,jet_order=mult,max_edges=5)[0] for u in nodes]
            count=reconstruct_mod(plan,jets,precision_bits=12,data_precision_bits=bits)
            assert count==brute_contract(net,max_edges=5)%(1<<12), (clauses,L,degree)
            hermites+=1
    assert checks>=100 and hermites>=40, (checks,hermites)
    assert prune_val+prune_z>0
    summary={'version':'0.9.0','status':'PASS','seed':20091029,
        'cross_group_modes_vs_independent_local_jet':checks,
        'hermite_vs_independent_original_tensor_count':hermites,
        'certified_mode_branches_dropped_valuation':prune_val,
        'certified_mode_branches_dropped_z_degree':prune_z,
        'max_wires':5,'asymptotic_theorem':'NOT_IMPLEMENTED',
        'elapsed_seconds':round(monotonic()-start,3)}
    from _evidence import evidence_path, write_evidence
    write_evidence(evidence_path('validation/validation_v09.json',
                                 root=Path(__file__).resolve().parents[1]),
                   json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
