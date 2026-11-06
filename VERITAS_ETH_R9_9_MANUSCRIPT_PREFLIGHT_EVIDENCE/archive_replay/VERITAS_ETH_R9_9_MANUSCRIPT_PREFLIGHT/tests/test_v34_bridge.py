from copy import deepcopy
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_child_topology_v34 import construct_integrated_certificate,check_integrated_certificate

def test_bridge_and_tamper_checks():
    net=from_cnf(CNF.from_lists(2,[[1,2]]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_jet_tile_modes(d3,node=1,precision=5,extension_degree=3,jet_length=2)
    cert=construct_integrated_certificate(net,modes)
    assert check_integrated_certificate(cert)['valid']
    assert cert['structural_link']['mode_bond_bridge']
    assert cert['scope']['m_over_8_child_wire_bound_proven'] is False
    bad=deepcopy(cert)
    bad['recursive_certificate']['child_descriptions'][0]['owned_halfbits']+=[999]
    assert not check_integrated_certificate(bad)['valid']
    bad=deepcopy(cert)
    bad['topology_certificate']['mode_ledger'][0]['weight']+=1
    assert not check_integrated_certificate(bad)['valid']
    bad=deepcopy(cert)
    bad['structural_link']['actual_recursive_child_wires_verified']=True
    assert not check_integrated_certificate(bad)['valid']

def test_composite_api():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    c=TestClient(app)
    res=c.post('/v1/research/eth/checked-structure-and-contraction',json={'n':2,'clauses':[[1,2]]})
    assert res.status_code==200,res.text
    result=c.post('/v1/research/eth/checked-structure-and-contraction/check',json={'certificate':res.json()['certificate']})
    assert result.status_code==200 and result.json()['valid']
