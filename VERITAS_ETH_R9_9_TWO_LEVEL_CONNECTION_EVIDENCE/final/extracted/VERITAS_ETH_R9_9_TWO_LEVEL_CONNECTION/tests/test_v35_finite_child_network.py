"""Correctness and fail-closed verification of finite child network accounting."""
import copy
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_child_network_v35 import (
    construct_child_network_certificate,check_child_network_certificate,
    ChildScopeBudgetExceeded)


def sample(n=2,clauses=((1,2),)):
    net=from_cnf(CNF.from_lists(n,[list(c) for c in clauses]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_jet_tile_modes(d3,node=1,precision=5,extension_degree=3,jet_length=2)
    return net,modes


def test_checked_child_scope_and_exact_oracle():
    net,modes=sample()
    cert=construct_child_network_certificate(net,modes)
    assert check_child_network_certificate(cert)['valid']
    model=cert['model']
    assert model['summary']['original_halfbit_count']==2*net.edges
    assert model['summary']['total_finite_mode_bond_incidences']==2*len(modes['modes'])
    assert model['summary']['manuscript_D44_child_wire_bound_verified'] is False
    assert model['summary']['subexponential_runtime_proven'] is False
    for c in model['children']:
        assert c['finite_child_scope_size']==c['owned_original_halfbit_count']+c['incident_mode_bond_count']


@pytest.mark.parametrize('mutate',[
    lambda c: c['model']['children'][0].update(finite_child_scope_size=0),
    lambda c: c['model']['summary'].update(manuscript_D44_child_wire_bound_verified=True),
    lambda c: c['model']['children'][0]['finite_scope_indices'].append(['mode',999]),
    lambda c: c['model']['mode_bonds'][0].update(source=99),
    lambda c: c['scope'].update(subexponential_time_proven=True),
    lambda c: c['result'][0].__setitem__(0,-22),
])
def test_rejects_forged_claims_and_scopes(mutate):
    net,modes=sample()
    cert=construct_child_network_certificate(net,modes)
    tamper=copy.deepcopy(cert)
    mutate(tamper)
    assert check_child_network_certificate(tamper)['valid'] is False


def test_rejects_oversized_finite_child_scope():
    net,modes=sample()
    with pytest.raises(ChildScopeBudgetExceeded):
        construct_child_network_certificate(net,modes,max_child_scope=1)


def test_invalid_limit_fails_closed():
    net,modes=sample()
    for cap in (0,-1,257,True,1.5):
        with pytest.raises(ValueError):
            construct_child_network_certificate(net,modes,max_child_scope=cap)


def test_multiple_formula_shapes():
    for n,clauses in [(1,((1,),)),(2,((1,-2),)),(3,((1,2),(-2,3)))]:
        net,modes=sample(n,clauses)
        cert=construct_child_network_certificate(net,modes)
        assert check_child_network_certificate(cert)['valid']


def test_isolated_declared_variable_uses_default_symbol():
    # A declared but unused variable still has a zero-port factor, which has
    # no D.3 edge-label entry and must still be assigned to a child group.
    net,modes=sample(3,((1,2),))
    cert=construct_child_network_certificate(net,modes)
    assert check_child_network_certificate(cert)['valid']
    assert any(f['label']=='variable:3' and f['owned_halfbits']==[] for f in cert['model']['original_vertex_factors'])


def test_v35_api_construct_and_check():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    client=TestClient(app)
    response=client.post('/v1/research/eth/finite-child-network',json={
        'n':2,'clauses':[[1,2]],'radix':2,'a':1,'node':1,
        'precision':5,'extension_degree':3,'jet_length':2})
    assert response.status_code==200,response.text
    cert=response.json()['certificate']
    check=client.post('/v1/research/eth/finite-child-network/check',json={'certificate':cert})
    assert check.status_code==200,check.text
    assert check.json()['valid'] is True
    assert client.get('/v1/research/eth/v35/status').json()['version']=='3.5.0'
