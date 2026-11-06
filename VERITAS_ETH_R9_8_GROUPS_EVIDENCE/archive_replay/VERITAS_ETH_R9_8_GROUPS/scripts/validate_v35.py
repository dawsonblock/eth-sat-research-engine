"""Seeded v3.5 child scope + exact numerical validation and tamper cases."""
from random import Random
from copy import deepcopy
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_child_network_v35 import construct_child_network_certificate,check_child_network_certificate

rng=Random(350035)
for i in range(35):
    n=rng.randint(1,3)
    clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))] for _ in range(rng.randint(1,2))]
    net=from_cnf(CNF.from_lists(n,clauses))
    if net.edges>6:continue
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    mode=make_jet_tile_modes(d3,node=1,precision=4,extension_degree=2,jet_length=2)
    cert=construct_child_network_certificate(net,mode)
    assert check_child_network_certificate(cert)['valid']
    assert cert['model']['summary']['original_halfbit_count']==2*net.edges
    forged=deepcopy(cert)
    forged['model']['summary']['max_finite_child_scope_size']=0
    assert not check_child_network_certificate(forged)['valid']
print('PASS: 35 seeded child-network source replays, arithmetic oracle comparisons and forged scope rejection')
