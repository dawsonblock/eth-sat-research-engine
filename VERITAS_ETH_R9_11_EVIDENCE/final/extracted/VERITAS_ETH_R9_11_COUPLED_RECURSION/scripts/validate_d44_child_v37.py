"""Independent seeded finite reference validation for v3.7."""
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_d44_child_reference import construct_child_reference

if __name__=='__main__':
    rng=Random(37001);passed=0
    for idx in range(40):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))] for c in range(rng.randint(1,2))]
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>5:continue
        d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
        mc=make_jet_tile_modes(d3,node=rng.choice((-1,1)),precision=rng.choice((3,4,5)),extension_degree=rng.choice((1,2,3)),jet_length=rng.choice((1,2,3)))
        cert=construct_child_reference(net,mc,max_work=1_000_000)
        assert cert['exact_direct_reference_matches']
        passed+=1
    print('PASS',passed,'independent finite D.4.4 group-local comparisons')
