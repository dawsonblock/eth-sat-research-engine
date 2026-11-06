"""Independent randomized and certificate-adversarial tests for v3.1 finite modes."""
from copy import deepcopy
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import (make_jet_tile_modes,check_jet_tile_modes,
                                         contract_mode_children,check_mode_child_certificate)


def _fixture():
    net=from_cnf(CNF.from_lists(2,[[1,2]]))
    base=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_jet_tile_modes(base,precision=5,jet_length=2)
    return net,modes


def test_small_mode_and_child_replay():
    net,modes=_fixture()
    assert check_jet_tile_modes(modes)['valid']
    cert=contract_mode_children(net,modes)
    assert check_mode_child_certificate(cert)['valid']
    assert cert['mode_tuple_count']>=1
    assert cert['scope']['subexponential_runtime_proven'] is False


def test_tamper_mode_metadata_coefficients_and_scope():
    _,modes=_fixture()
    for corruption in ('scope','node','mode','cross','d3','tuple_count'):
        bad=deepcopy(modes)
        if corruption=='scope':bad['scope']['subexponential_runtime_proven']=True
        elif corruption=='node':bad['node']=-1
        elif corruption=='mode':
            if bad['modes']:bad['modes'][0]['rows'][0][1][0][0]+=1
            else:bad['local'][0][2][0][0]+=1
        elif corruption=='cross':bad['cross_pairs'].clear()
        elif corruption=='d3':bad['d3_certificate']['edges'][0][0]+=20
        else:bad['mode_tuple_count']+=1
        assert not check_jet_tile_modes(bad)['valid'], corruption


def test_tamper_child_result_and_certificate_claim():
    net,modes=_fixture();cert=contract_mode_children(net,modes)
    for change in ('result','claim','network','children'):
        bad=deepcopy(cert)
        if change=='result':bad['result'][0][0]+=1
        elif change=='claim':bad['claim']='PROVEN_SUBEXPONENTIAL'
        elif change=='network':bad['network']['factors'][0]['table'][0]+=1
        else:bad['children'][0]['group']+=1
        assert not check_mode_child_certificate(bad)['valid'],change


def test_seeded_small_cnf_exact_differential():
    rng=Random(310031)
    passed=0
    for k in range(28):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))]
                for j in range(rng.randint(1,2))]
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>5:continue
        d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
        modes=make_jet_tile_modes(d3,node=rng.choice((-1,1)),precision=rng.choice((3,4,5,6)),
                           extension_degree=rng.choice((1,2,3)),jet_length=rng.choice((1,2,3)))
        assert check_jet_tile_modes(modes)['valid']
        result=contract_mode_children(net,modes,max_work=600000)
        assert result['direct_oracle_matches']
        passed+=1
    assert passed>=22


def test_api_and_status():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    c=TestClient(app)
    status=c.get('/v1/research/eth/v31/status')
    assert status.status_code==200
    assert status.json()['not_implemented']
    result=c.post('/v1/research/eth/geometric-mode-children',json={'n':2,'clauses':[[1,2]]})
    assert result.status_code==200,result.text
    data=result.json()
    assert data['mode_checker']['valid'] and data['child_checker']['valid']
    check=c.post('/v1/research/eth/geometric-mode-children/check',json={'certificate':data['certificate']})
    assert check.status_code==200 and check.json()['valid']


def test_resource_fail_closed():
    from pytest import raises
    net,modes=_fixture()
    with raises((ValueError,TimeoutError)):
        contract_mode_children(net,modes,max_work=1)
    with raises(ValueError):
        make_jet_tile_modes(modes['d3_certificate'],precision=20)
