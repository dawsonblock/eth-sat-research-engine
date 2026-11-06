"""Seeded v3.4 construction/checks and independent source coverage checks."""
from __future__ import annotations
from random import Random
from copy import deepcopy
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_child_topology_v34 import (
    construct_topology_certificate,check_topology_certificate,
    construct_integrated_certificate,check_integrated_certificate)


def main():
    rng=Random(340034);n_cases=45;n_integrated=0
    for i in range(n_cases):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n)
            for _ in range(rng.randint(1,2))] for _ in range(rng.randint(1,2))]
        net=from_cnf(CNF.from_lists(n,clauses))
        d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
        t=construct_topology_certificate(d3)
        assert check_topology_certificate(t)['valid']
        assert sum(g['real_half_ports'] for g in t['groups'])==2*net.edges
        if net.edges<=5 and n_integrated<12:
            m=make_jet_tile_modes(d3,node=1,precision=4,extension_degree=2,jet_length=2)
            z=construct_integrated_certificate(net,m)
            assert check_integrated_certificate(z)['valid']
            tampered=deepcopy(z)
            tampered['structural_link']['mode_bond_bridge']=False
            assert not check_integrated_certificate(tampered)['valid']
            n_integrated+=1
    assert n_integrated>=10
    print(f'PASS: {n_cases} D.3 port-ledger checks; {n_integrated} composed exact contractions and tamper rejections')

if __name__=='__main__':main()
