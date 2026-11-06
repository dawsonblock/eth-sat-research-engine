"""Independent finite D3-grouped implicit Taylor child experiments."""
import copy,random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf,TensorNetwork,Factor
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30 import (
    make_bipartite_edges,make_child_certificate,check_child_certificate,ImplicitBudgetExceeded)
from veritas.research.eth_modes_v29.extension_modes import make_extension_modes


def fixture_net():
    return from_cnf(CNF.from_lists(2,[[1,2]]))


def build(net, **kwargs):
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_work=150000,max_packets=256)
    return make_child_certificate(net,d3,**kwargs)


def test_finite_implicit_replay():
    cert=build(fixture_net())
    status=check_child_certificate(cert)
    assert status['valid'],status
    assert len(cert['result'])==3
    assert cert['scope']=={'manuscript_D44_child_tensors':False,
                            'geometric_tile_modes_used':False,
                            'subexponential_runtime_proven':False}
    assert len(cert['children'])>=1
    assert status['boundary_width']>=0


def test_existing_v29_modes_can_be_checked_but_are_not_used_as_d44_modes():
    net=fixture_net()
    base=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_extension_modes(base,node=1,precision=8,extension_degree=4,jet_length=3)
    cert=make_child_certificate(net,base,mode_certificate=modes)
    assert check_child_certificate(cert)['valid']
    modes['node']=-1
    with pytest.raises(ValueError,match='v2.9 modes'):
        make_child_certificate(net,base,mode_certificate=modes)


def test_reject_tamper_result_graph_scope_and_boundary():
    cert=build(fixture_net())
    for modify in ('result','scope','table','boundary','claims'):
        bad=copy.deepcopy(cert)
        if modify=='result':bad['result'][0][0]+=1
        elif modify=='scope':bad['scope']['subexponential_runtime_proven']=True
        elif modify=='table':bad['network']['factors'][0]['table'][0]+=1
        elif modify=='boundary':bad['boundary'].append(999)
        else:bad['claim']='FULL_SUBEXPONENTIAL_SOLVER'
        assert not check_child_certificate(bad)['valid'],modify


def test_input_must_match_pack_endpoints():
    net=fixture_net()
    base=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    bad=copy.deepcopy(base)
    bad['edges'][0][0]=4
    with pytest.raises(ValueError):make_child_certificate(net,bad)


def test_budget_fails_closed():
    net=fixture_net()
    with pytest.raises(ImplicitBudgetExceeded):build(net,max_assignments=1)


def test_randomized_independent_half_edge_differential():
    rng=random.Random(300027)
    checked=0
    for _ in range(55):
        n=rng.randint(1,3)
        clauses=[]
        for _ in range(rng.randint(1,2)):
            clauses.append([rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))])
        net=from_cnf(CNF.from_lists(n,clauses))
        if not 1<=net.edges<=6:continue
        cert=build(net,node=rng.choice((-1,1)),jet_length=rng.randint(1,3),
                   precision=rng.choice((4,6,8)),extension_degree=rng.choice((1,2,4)))
        verdict=check_child_certificate(cert)
        assert verdict['valid'],(clauses,verdict)
        checked+=1
    assert checked>=45


def test_scalar_and_repeated_variable_factor_supported():
    net=TensorNetwork(2,(Factor((0,1),(0,1,1,1),'row:0'),
                         Factor((0,1),(1,0,0,1),'col:1'),
                         Factor((),(2,),'col:200')))
    cert=build(net)
    assert check_child_certificate(cert)['valid']


def test_checker_rejects_malformed_payload_without_crashing():
    for item in (None,{},[],{'schema':'VERITAS_ETH_IMPLICIT_CHILDREN_V30'}):
        assert not check_child_certificate(item)['valid']


def test_api_v30_status_and_construct():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    c=TestClient(app)
    status=c.get('/v1/research/eth/v30/status')
    assert status.status_code==200
    assert status.json()['claim']=='FINITE_IMPLICIT_SEPARATOR_REFERENCE_ONLY'
    res=c.post('/v1/research/eth/implicit-children',json={'n':2,'clauses':[[1,2]]})
    assert res.status_code==200, res.text
    assert res.json()['checker']['valid']
    assert res.json()['certificate']['origin_count_mod_2p']==3
    bad=c.post('/v1/research/eth/implicit-children',json={'n':2,'clauses':[[1,2]],'node':0})
    assert bad.status_code==422
    check=c.post('/v1/research/eth/implicit-children/check',json={'certificate':res.json()['certificate']})
    assert check.status_code==200 and check.json()['valid']
