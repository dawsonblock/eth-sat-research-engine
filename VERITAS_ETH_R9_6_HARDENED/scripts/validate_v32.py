"""Fast independent demo and tamper validation for v3.2."""
from copy import deepcopy
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes,contract_mode_children
from veritas.research.eth_mode_bonds_v32 import construct_bond_certificate,check_bond_certificate
rng=Random(3200);ok=0
for k in range(40):
 n=rng.randint(1,3)
 clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))]
          for j in range(rng.randint(1,2))]
 net=from_cnf(CNF.from_lists(n,clauses))
 if net.edges>5:continue
 d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
 modes=make_jet_tile_modes(d3,precision=rng.choice((3,4,5)),jet_length=rng.choice((1,2,3)))
 cert=construct_bond_certificate(net,modes)
 assert cert['result']==contract_mode_children(net,modes)['result']
 assert check_bond_certificate(cert)['valid']
 bad=deepcopy(cert);bad['stats']['joined_entries']+=1
 assert not check_bond_certificate(bad)['valid']
 ok+=1
assert ok>=30
print(f'PASS: {ok} independent v3.2 finite bond networks; tampering rejected; ETH theorem unproved')
