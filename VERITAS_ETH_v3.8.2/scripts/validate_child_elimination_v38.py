"""Seeded end-to-end finite reference checks; not a complexity theorem validation."""
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_child_elimination_v38 import (
    construct_elimination_reference,verify_elimination_reference)

rng=Random(3802026)
passed=0
for _ in range(40):
    n=rng.randint(1,3)
    clauses=[[rng.choice((-1,1))*rng.randint(1,n) for j in range(rng.randint(1,2))]
             for k in range(rng.randint(1,2))]
    net=from_cnf(CNF.from_lists(n,clauses))
    if net.edges>5: continue
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
    modes=make_jet_tile_modes(d3,node=rng.choice((-1,1)),precision=rng.choice((3,4,5)),
                 extension_degree=rng.choice((1,2,3)),jet_length=rng.choice((1,2)))
    c=construct_elimination_reference(net,modes,max_work=1000000)
    assert verify_elimination_reference(c,max_work=1000000)['valid']
    passed+=1
print('PASS',passed,'exact finite child-elimination oracle/certificate comparisons')
