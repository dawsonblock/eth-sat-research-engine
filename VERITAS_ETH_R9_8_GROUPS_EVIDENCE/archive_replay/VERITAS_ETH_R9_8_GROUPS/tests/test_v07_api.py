"""End-to-end API gates for exact research results and fail-closed limits."""
from fastapi.testclient import TestClient
from veritas.api.main import app

client = TestClient(app)


def test_wire_api_exact_and_modular():
    source = {'n':3,'clauses':[[1,2],[-1,3]],'timeout_s':5.0}
    exact = client.post('/v1/research/wire-deformation',json=source)
    assert exact.status_code==200,exact.text
    data=exact.json()
    assert data['status']=='POLYNOMIAL'
    assert data['method']=='TOY_SPLIT_WIRE_DEFORMATION_GENERIC_ELIMINATION'
    assert data['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert data['original_satisfying_assignments']=='4'
    assert data['degree_bound']==4
    assert data['independent_rank_one_checks']['rank_one_nodes_checked']
    assert data['coefficients'][0]=='4'
    assert data['interpolated_constant_term']=='4'
    mod=client.post('/v1/research/wire-deformation',json={**source,'precision_bits':2})
    assert mod.status_code==200,mod.text
    dmod=mod.json()
    assert dmod['original_satisfying_assignments'] is None
    assert dmod['original_count_residue']=='0'
    assert [int(x) for x in dmod['coefficients']] == [int(x)%4 for x in data['coefficients']]
    mod2=client.post('/v1/research/wire-deformation',json={**source,'precision_bits':4})
    assert mod2.status_code==200
    assert mod2.json()['original_satisfying_assignments']=='4'


def test_wire_api_rejects_unsupported_input():
    payload={'n':4,'clauses':[[1,2],[-2,3]],'max_edges':3}
    res=client.post('/v1/research/wire-deformation',json=payload)
    assert res.status_code==422
    res=client.post('/v1/research/wire-deformation',json={'n':1,'clauses':[[1]],'precision_bits':0})
    assert res.status_code==422
    res=client.post('/v1/research/wire-deformation',json={'n':41,'clauses':[]})
    assert res.status_code==422


def test_zero_edges_v07_status_and_audit_page():
    res=client.post('/v1/research/wire-deformation',json={'n':2,'clauses':[]})
    assert res.status_code==200
    data=res.json()
    assert data['coefficients']==['4']
    assert data['degree_bound']==0
    assert data['original_satisfying_assignments']=='4'
    status=client.get('/v1/paper/audit')
    assert status.status_code==200
    assert any(item['implementation']=='EXACT_GENERIC_ELIMINATION_NO_SPEEDUP' for item in status.json()['claims'])
    assert status.json()['status']=='INCOMPLETE_PAPER_REPRODUCTION'


def test_wire_api_empty_clause_and_inconsistent():
    res=client.post('/v1/research/wire-deformation',json={'n':1,'clauses':[[1],[-1]]})
    assert res.status_code==200
    assert res.json()['coefficients'][0]=='0'
    res=client.post('/v1/research/wire-deformation',json={'n':2,'clauses':[[]]})
    assert res.status_code==200
    assert res.json()['coefficients']==['0']
