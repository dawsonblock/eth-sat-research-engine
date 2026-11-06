"""Independent finite tests for manuscript-shaped group-local child tensors."""
from copy import deepcopy
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_d44_child_reference import (construct_child_reference,verify_child_reference)

def test_exact_child_network_reference():
    net=from_cnf(CNF.from_lists(2,[[1,2]]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
    modes=make_jet_tile_modes(d3,precision=5,jet_length=2)
    proof=construct_child_reference(net,modes)
    assert verify_child_reference(proof)['valid']
    assert proof['exact_direct_reference_matches']
    assert all(g['extra_mode_bond_wires']==0 for g in proof['children'])
    assert proof['manuscript_M_over_8_theorem_proven'] is False

def test_tamper_rejected():
    net=from_cnf(CNF.from_lists(2,[[1,2]]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
    modes=make_jet_tile_modes(d3,precision=5,jet_length=2)
    proof=construct_child_reference(net,modes)
    for kind in ('result','wire_count','theorem','beta_count'):
        copy=deepcopy(proof)
        if kind=='result':copy['result'][0][0]+=1
        elif kind=='wire_count':copy['children'][0]['child_wires']+=1
        elif kind=='theorem':copy['subexponential_runtime_proven']=True
        else:copy['mode_tuple_count']+=1
        assert verify_child_reference(copy)['valid'] is False

def test_seeded_random_cnfs():
    rng=Random(3700)
    for _ in range(9):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))]]
        net=from_cnf(CNF.from_lists(n,clauses))
        d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
        modes=make_jet_tile_modes(d3,node=rng.choice([-1,1]),precision=4,jet_length=2)
        proof=construct_child_reference(net,modes)
        assert proof['exact_direct_reference_matches']
