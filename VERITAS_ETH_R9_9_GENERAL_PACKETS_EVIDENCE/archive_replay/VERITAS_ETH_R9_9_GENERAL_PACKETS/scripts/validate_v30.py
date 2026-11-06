"""Seeded independent finite child-tensor checks; exit nonzero on mismatch."""
from __future__ import annotations
import random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30 import make_bipartite_edges,make_child_certificate,check_child_certificate

def main():
    rng=random.Random(300031)
    good=0
    for i in range(70):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))] for _ in range(rng.randint(1,2))]
        net=from_cnf(CNF.from_lists(n,clauses))
        d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_work=150000,max_packets=256)
        cert=make_child_certificate(net,d3,node=rng.choice((-1,1)),precision=8,
                                      extension_degree=4,jet_length=3)
        result=check_child_certificate(cert)
        assert result['valid'],(i,result)
        good+=1
    print(f'PASS: {good} seeded finite child + half-edge oracle + origin-count certificates')

if __name__=='__main__':main()
