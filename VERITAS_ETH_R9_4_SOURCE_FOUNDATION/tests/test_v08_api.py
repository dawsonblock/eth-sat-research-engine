from fastapi.testclient import TestClient
from veritas.api.main import app

client=TestClient(app)


def test_cauchy_api_full_rational_and_jet():
    req={'n':3,'clauses':[[1,2],[-1,3]],'packet_size':2,'node':-1,'precision_bits':9,'jet_order':5}
    r=client.post('/v1/research/cauchy-deformation',json=req)
    assert r.status_code==200,r.text
    data=r.json()
    assert data['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert data['original_satisfying_assignments']=='4'
    assert len(data['rational_coefficients'])==data['degree_bound']+1
    assert data['shifted_jet']['node']==-1
    assert len(data['shifted_jet']['coefficients_mod_2_power'])==5
    assert data['grid_invariants']['grid_shift_sparsity_checked']
    assert len(data['audit_sha256'])==64
    assert 'NO subexponential' not in data['method']


def test_cauchy_api_rejections():
    for payload in [
        {'n':1,'clauses':[[1]],'packet_size':3},
        {'n':1,'clauses':[[1]],'packet_size':2,'node':2},
        {'n':4,'clauses':[[1,2,3,4],[1,2,3,4]]},
        {'n':4,'clauses':[[1,2,3,4]],'packet_size':8},
        {'n':1,'clauses':[[1]],'jet_order':0},
    ]:
        r=client.post('/v1/research/cauchy-deformation',json=payload)
        assert r.status_code==422, r.text


def test_empty_formula_and_contradiction():
    a=client.post('/v1/research/cauchy-deformation',json={'n':4,'clauses':[]})
    assert a.status_code==200 and a.json()['original_satisfying_assignments']=='16'
    b=client.post('/v1/research/cauchy-deformation',json={'n':1,'clauses':[[1],[-1]]})
    assert b.status_code==200 and b.json()['original_satisfying_assignments']=='0'
    c=client.get('/v1/paper/audit').json()
    assert any(x['implementation']=='EXACT_TINY_EXHAUSTIVE_REFERENCE_NO_SPEEDUP' for x in c['claims'])
    assert c['status']=='INCOMPLETE_PAPER_REPRODUCTION'
    assert client.get('/health').json()['version']=='2.4.0'
