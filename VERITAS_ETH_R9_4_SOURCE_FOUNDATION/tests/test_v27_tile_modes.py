"""D.4.4 finite mode tests against an independent exact coefficient checker."""
import copy
import json
import random
import pytest
from veritas.research.eth_packing_v26 import construct_d3_packing
from veritas.research.eth_modes_v27 import (construct_tile_modes, verify_tile_modes,
                                             weighted_tuples,count_tuples,ModeBudgetExceeded)
from veritas.research.eth_modes_v27.cli import main


def test_weight_enumerator_independent_exhaustive():
    for weights in ([],[1],[1,2],[2,3,1],[3,3,3,2]):
        for p in range(1,10):
            expected=[beta for beta in __import__('itertools').product(range(p),repeat=len(weights))
                      if sum(x*w for x,w in zip(beta,weights))<p]
            got=list(weighted_tuples(weights,p))
            assert set(got)==set(expected)
            assert count_tuples(weights,p)==len(expected)


def test_resource_limit_tuples_fail_closed():
    with pytest.raises(ModeBudgetExceeded):
        count_tuples([1]*20,6,cap=100)
    with pytest.raises(ValueError):
        list(weighted_tuples([0],6))


def test_geometric_modes_small_randomized():
    rng=random.Random(2701)
    comparisons=0
    for a in (1,2):
        for _ in range(28):
            edges=[[rng.randrange(3),rng.randrange(3)] for _ in range(rng.randint(1,6))]
            d3=construct_d3_packing(edges,r=2,a=a)
            nodes=[t for t in range(-(1<<a),(1<<a)) if t and (abs(t)&-abs(t))<(1<<a)]
            node=rng.choice(nodes)
            zeta=rng.choice((0,1,2,3))
            precision=rng.randint(2,8)
            cert=construct_tile_modes(d3,node=node,zeta=zeta,precision=precision)
            result=verify_tile_modes(cert)
            assert result['valid'],result
            assert result['subexponential_claim'] is False
            comparisons+=1
    assert comparisons==56


def test_tampered_modes_fail_closed():
    d3=construct_d3_packing([[0,0],[1,1],[0,1],[1,0]],r=2,a=1)
    cert=construct_tile_modes(d3,node=1,zeta=1,precision=7)
    assert verify_tile_modes(cert)['valid']
    assert cert['modes']
    changes=[lambda c:c['modes'][0].update(weight=99),
             lambda c:c['modes'][0]['column_terms'][0].__setitem__(1,1000),
             lambda c:c['modes'][0]['row_coefficients'][0][1].__setitem__(0,999),
             lambda c:c.__setitem__('mode_tuple_count',-5),
             lambda c:c['d3_certificate']['packets'][0]['slots'].__setitem__(0,999),
             lambda c:c['scope'].__setitem__('subexponential_runtime_proven',True),
             lambda c:c.__setitem__('node',0)]
    for mutate in changes:
        damaged=copy.deepcopy(cert)
        mutate(damaged)
        result=verify_tile_modes(damaged)
        assert not result['valid'],result


def test_certificate_roundtrip(tmp_path,capsys):
    fn=tmp_path/'mode_cert.json'
    assert main(['construct','--edges-json','[[0,0],[1,1],[0,1],[1,0]]',
                 '--radix','2','--a','1','--output',str(fn)])==0
    assert main(['check','--certificate',str(fn)])==0
    data=json.loads(fn.read_text())
    assert verify_tile_modes(data)['valid']
    assert main(['count-tuples','--weights-json','[1,2]','--precision','4'])==0
    assert fn.stat().st_size>100


def test_full_deformed_scalar_identity_randomized():
    from veritas.core.cnf import CNF
    from veritas.research.tensor import from_cnf
    from veritas.research.eth_modes_v27.reference import network_edges,check_full_scalar_identity
    rng=random.Random(2702)
    for _ in range(18):
        clauses=[[rng.choice((-1,1))*rng.randint(1,2)] for __ in range(rng.randint(1,4))]
        net=from_cnf(CNF.from_lists(2,clauses))
        d3=construct_d3_packing(network_edges(net),r=2,a=1)
        cert=construct_tile_modes(d3,node=rng.choice((-1,1)),zeta=rng.randrange(0,3),precision=rng.randrange(2,7))
        assert check_full_scalar_identity(net,cert)['status']=='FINITE_DEFORMED_SCALAR_IDENTITY_VERIFIED'


def test_v27_api():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    client=TestClient(app)
    res=client.post('/v1/research/eth/d44/modes',json={
        'edges':[[0,0],[1,1],[0,1],[1,0]],'radix':2,'a':1,
        'node':1,'zeta':1,'precision':5})
    assert res.status_code==200,res.text
    body=res.json()
    assert body['verification']['valid']
    assert client.post('/v1/research/eth/d44/check',json={'certificate':body['certificate']}).json()['valid']
    status=client.get('/v1/research/eth/d44/status').json()
    assert 'recursive contraction' in ' '.join(status['not_implemented'])
    assert client.post('/v1/research/eth/d44/modes',json={
        'edges':[[0,0]],'node':0}).status_code==422


def test_nontrivial_high_weight_tile_modes():
    # Exercise j>0 columns (not just the b=0 constant mode).
    edges=[[1,3],[2,2],[3,2],[0,3],[3,2],[1,1],
           [3,1],[2,2],[3,2],[0,2],[1,1],[3,3]]
    d3=construct_d3_packing(edges,r=2,a=2)
    cert=construct_tile_modes(d3,node=1,zeta=1,precision=5)
    assert any(mode['weight']>1 for mode in cert['modes'])
    result=verify_tile_modes(cert)
    assert result['valid'], result
    assert result['tuple_count']==len(list(weighted_tuples([m['weight'] for m in cert['modes']],5)))
