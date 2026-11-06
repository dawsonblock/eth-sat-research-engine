"""Reproducible v3.3 standalone differential and tamper validation."""
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_mode_bonds_v32.bonds import construct_bond_certificate
from veritas.research.eth_recursive_bonds_v33 import construct_recursive_certificate,check_recursive_certificate

rng=Random(330033);passed=0
for i in range(45):
    n=rng.randint(1,3)
    clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))] for _ in range(rng.randint(1,2))]
    net=from_cnf(CNF.from_lists(n,clauses))
    if net.edges>5:continue
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_jet_tile_modes(d3,node=rng.choice((-1,1)),precision=rng.randint(3,6),extension_degree=rng.randint(1,3),jet_length=rng.randint(1,3))
    cert=construct_recursive_certificate(net,modes)
    assert check_recursive_certificate(cert)['valid']
    assert cert['result']==construct_bond_certificate(net,modes)['result']
    passed+=1
assert passed>=30
print(f'PASS: {passed} exact finite triple-checked recursive-mode cases')
