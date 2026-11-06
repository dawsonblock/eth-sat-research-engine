"""Minimal independent v3.1 end-to-end validation."""
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import (make_jet_tile_modes,check_jet_tile_modes,
    contract_mode_children,check_mode_child_certificate)

net=from_cnf(CNF.from_lists(2,[[1,2]]))
base=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
mode=make_jet_tile_modes(base,precision=5,extension_degree=3,jet_length=2)
assert check_jet_tile_modes(mode)['valid']
result=contract_mode_children(net,mode)
assert check_mode_child_certificate(result)['valid']
print('PASS: v3.1 finite geometric extension mode-child identity; NOT full ETH recursion')
