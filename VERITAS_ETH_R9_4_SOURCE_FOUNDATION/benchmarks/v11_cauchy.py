"""Paired direct oracle vs exact polynomial factor elimination (toy benchmark).

Outputs per-instance measured times. Does NOT imply asymptotic acceleration.
"""
from __future__ import annotations
from time import perf_counter
import json
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
from veritas.research.cauchy_elimination import eliminate_cauchy_jet

def main():
    samples=[(3,[[1,2],[-2,3]]),(4,[[1,2],[-2,3],[3,4]]),(4,[[1,2],[2,3]])]
    results=[]
    for n,clauses in samples:
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>6:continue
        a=perf_counter()
        fast,stats=eliminate_cauchy_jet(net,packet_size=2,node=1,precision_bits=10,jet_order=5)
        b=perf_counter()
        oracle,_=shifted_cauchy_jet_mod(net,packet_size=2,node=1,precision_bits=10,jet_order=5,max_edges=6)
        c=perf_counter()
        assert fast==oracle
        results.append({'n':n,'clauses':clauses,'wires':net.edges,'elimination_seconds':round(b-a,6),
            'direct_oracle_seconds':round(c-b,6),'peak_factor_entries':stats.peak_factor_entries})
    print(json.dumps({'status':'PASS','limitations':'Toy inputs; treewidth-exponential algorithm, not ETH runtime proof',
                      'cases':results},indent=2))
if __name__=='__main__':main()
