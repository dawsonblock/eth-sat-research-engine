"""D.3-anchored exact finite packet coefficients and independent replay."""
from copy import deepcopy
from random import Random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_packet_tensors_v36 import (
    construct_packet_tensor_certificate,check_packet_tensor_certificate,
    PacketTensorBudgetExceeded)


def sample(n=2,clauses=((1,2),),radix=2,a=1,node=1,p=5,e=3,length=2):
    net=from_cnf(CNF.from_lists(n,[list(c) for c in clauses]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=radix,a=a,max_packets=256)
    mode=make_jet_tile_modes(d3,node=node,precision=p,extension_degree=e,jet_length=length)
    return net,mode


def test_certificate_and_global_exactness():
    net,mode=sample()
    cert=construct_packet_tensor_certificate(net,mode)
    check=check_packet_tensor_certificate(cert)
    assert check['valid'],check
    assert cert['stats']['original_wires']==net.edges
    assert cert['stats']['moebius_assignments_checked']>0
    assert cert['scope']['manuscript_recursive_D44_packet_tensors'] is False
    assert cert['manuscript_M_over_8_child_bound_verified'] is False
    assert sorted(e for packet in cert['packets'] for e in packet['edges'])==list(range(net.edges))


@pytest.mark.parametrize('mutate',[
    lambda c: c['result'][0].__setitem__(0,123),
    lambda c: c['packets'][0].update(edges=[500]),
    lambda c: c['packets'][0]['coefficient_rows'][0]['monomials'][0].__setitem__(0,99),
    lambda c: c['scope'].update(subexponential_runtime_proven=True),
    lambda c: c.update(manuscript_M_over_8_child_bound_verified=True),
    lambda c: c['mode_certificate'].update(node=-1),
])
def test_reject_tampered_certificates(mutate):
    net,mode=sample()
    cert=construct_packet_tensor_certificate(net,mode)
    tampered=deepcopy(cert)
    mutate(tampered)
    assert not check_packet_tensor_certificate(tampered)['valid']


def test_original_factor_shapes_and_empty_packets():
    for n,clauses in [(1,((1,),)),(2,((1,-2),)),(3,((1,2),(-2,3))),
                      (3,((1,2),)),(2,((1,),(-1,2)))]:
        net,mode=sample(n,clauses)
        cert=construct_packet_tensor_certificate(net,mode)
        assert check_packet_tensor_certificate(cert)['valid']
        assert all('row_groups' in packet for packet in cert['packets'])


def test_randomized_nontrivial_integer_jet_cases():
    rng=Random(3600)
    for _ in range(16):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))]
                 for _ in range(rng.randint(1,2))]
        net,mode=sample(n,clauses,p=rng.choice((4,5,6)),e=rng.choice((2,3)),length=rng.choice((1,2,3)))
        cert=construct_packet_tensor_certificate(net,mode)
        assert check_packet_tensor_certificate(cert)['valid']


def test_resource_limits_fail_closed():
    net,mode=sample()
    for cap in (0,True,99,2_000_001,1.5):
        with pytest.raises(ValueError):construct_packet_tensor_certificate(net,mode,max_work=cap)
    larger_net,larger_mode=sample(3,((1,2),(-2,3)))
    with pytest.raises(PacketTensorBudgetExceeded):
        construct_packet_tensor_certificate(larger_net,larger_mode,max_work=100)


def test_api_and_version_status():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    client=TestClient(app)
    resp=client.post('/v1/research/eth/finite-packet-tensors',json={
        'n':2,'clauses':[[1,2]],'radix':2,'a':1,'node':1,
        'precision':5,'extension_degree':3,'jet_length':2})
    assert resp.status_code==200,resp.text
    assert resp.json()['checker']['valid']
    check=client.post('/v1/research/eth/finite-packet-tensors/check',json={
        'certificate':resp.json()['certificate']})
    assert check.status_code==200 and check.json()['valid']
    status=client.get('/v1/research/eth/v36/status')
    assert status.status_code==200 and status.json()['version']=='3.6.0'
