from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.audit.store import AuditStore


def test_v14_endpoint_and_integrity(tmp_path):
    app.state.audit=AuditStore(tmp_path/'audit14.sqlite3')
    c=TestClient(app)
    req={'n':3,'clauses':[[1,2],[-2,3]],'timeout_s':12}
    r=c.post('/v1/research/bounded-degree-tensor',json=req)
    assert r.status_code==200,r.text
    assert r.json()['stats']['maximum_factor_degree']<=3
    assert r.json()['status']=='STRUCTURALLY_PARISMONIOUS_TENSOR'
    r=c.post('/v1/research/bounded-degree-tensor',json={**req,'contract':True})
    assert r.status_code==200,r.text
    assert r.json()['status']=='EXACT_COUNT'
    assert r.json()['count']=='4'
    assert r.json()['independent_count_checked'] is True
    assert c.get('/v1/audits/'+r.json()['audit_sha256']).status_code==200
    r=c.post('/v1/research/bounded-degree-tensor',json={**req,'contract':True,'modulus_bits':2})
    assert r.status_code==200 and r.json()['count']=='0'
    assert r.json()['status']=='COUNT_RESIDUE'
    assert c.get('/health').json()['version']=='2.4.0'
    assert any('v1.4' in claim['claim'] for claim in c.get('/v1/paper/audit').json()['claims'])


def test_v14_fail_closed(tmp_path):
    app.state.audit=AuditStore(tmp_path/'audit14b.sqlite3')
    c=TestClient(app)
    req={'n':1,'clauses':[[1]]*7,'contract':True}
    r=c.post('/v1/research/bounded-degree-tensor',json={**req,'max_work_assignments':1})
    assert r.status_code==422 and 'budget' in str(r.json()).lower()
    r=c.post('/v1/research/bounded-degree-tensor',json={**req,'max_wires':3})
    assert r.status_code==422
    r=c.post('/v1/research/bounded-degree-tensor',json={**req,'modulus_bits':1})
    assert r.status_code==422
