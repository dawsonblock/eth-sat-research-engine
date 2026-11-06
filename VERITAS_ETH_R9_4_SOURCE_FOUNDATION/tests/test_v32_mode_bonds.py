"""v3.2: exact finite source/target mode-index tensor bonds."""
from copy import deepcopy
from random import Random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes,contract_mode_children
from veritas.research.eth_mode_bonds_v32 import construct_bond_certificate,check_bond_certificate,BondBudgetExceeded


def make_case(n=2,clauses=((1,2),),p=5,jet=2,node=1):
    net=from_cnf(CNF.from_lists(n,[list(x) for x in clauses]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_jet_tile_modes(d3,node=node,precision=p,extension_degree=3,jet_length=jet)
    return net,modes


def test_finite_mode_bond_network_agrees_with_v31():
    net,modes=make_case()
    cert=construct_bond_certificate(net,modes)
    assert check_bond_certificate(cert)['valid']
    reference=contract_mode_children(net,modes)
    assert cert['result']==reference['result']
    assert cert['scope']['subexponential_runtime_proven'] is False
    assert cert['scope']['manuscript_m_over_8_guarantee'] is False
    assert cert['stats']['child_count']>0
    assert all('entries' in child for child in cert['children'])


def test_tampering_fails_closed():
    net,modes=make_case();cert=construct_bond_certificate(net,modes)
    for kind in ('result','child','claim','scope','mode','network','stats'):
        bad=deepcopy(cert)
        if kind=='result':bad['result'][0][0]+=1
        elif kind=='child':bad['children'][0]['group']+=1
        elif kind=='claim':bad['claim']='PROVEN_ETH'
        elif kind=='scope':bad['scope']['manuscript_m_over_8_guarantee']=True
        elif kind=='mode':bad['mode_certificate']['precision']+=1
        elif kind=='network':bad['network']['factors'][0]['table'][0]+=1
        elif kind=='stats':bad['stats']['work_units']+=1
        assert not check_bond_certificate(bad)['valid'],kind


def test_seeded_random_differential():
    rng=Random(320032)
    successful=0
    for i in range(24):
        n=rng.randint(1,3)
        clauses=[]
        for j in range(rng.randint(1,2)):
            clauses.append([rng.choice((-1,1))*rng.randint(1,n)
                           for _ in range(rng.randint(1,2))])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>5:continue
        d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
        modes=make_jet_tile_modes(d3,node=rng.choice((-1,1)),precision=rng.randint(3,6),
                                  extension_degree=rng.randint(1,3),jet_length=rng.randint(1,3))
        cert=construct_bond_certificate(net,modes)
        assert cert['direct_half_edge_match']
        assert cert['result']==contract_mode_children(net,modes)['result']
        successful+=1
    assert successful>=18


def test_budget_and_api_cli(tmp_path):
    net,modes=make_case()
    with pytest.raises((ValueError,BondBudgetExceeded)):
        construct_bond_certificate(net,modes,max_work=1)
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    client=TestClient(app)
    status=client.get('/v1/research/eth/v32/status')
    assert status.status_code==200
    assert 'not_implemented' in status.json()
    res=client.post('/v1/research/eth/mode-bond-network',json={'n':2,'clauses':[[1,2]]})
    assert res.status_code==200,res.text
    cert=res.json()['certificate']
    valid=client.post('/v1/research/eth/mode-bond-network/check',json={'certificate':cert})
    assert valid.status_code==200 and valid.json()['valid']
