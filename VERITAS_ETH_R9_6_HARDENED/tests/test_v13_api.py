import pytest
from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.audit.store import AuditStore


def test_weighted_recovery_api_and_failure_states(tmp_path):
    app.state.audit=AuditStore(tmp_path/'recovery.sqlite3')
    client=TestClient(app)
    body={'n':3,'clauses':[[1,2],[-2,3]],'timeout_s':15}
    response=client.post('/v1/research/weighted-recovery',json=body)
    assert response.status_code==200,response.text
    obj=response.json()
    assert obj['status']=='EXACT_COUNT'
    assert obj['exact_count']=='4'
    assert obj['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert obj['independent_count_checked'] and obj['independent_jet_checked']
    assert obj['transcript_sha256']
    assert obj['data_bits']>=obj['target_bits']
    assert len(obj['node_jets'])==len(obj['nodes'])
    assert client.get('/health').json()['version']=='2.4.0'
    assert any('v1.3' in item['claim'] for item in client.get('/v1/paper/audit').json()['claims'])
    assert client.get('/v1/audits/'+obj['audit_sha256']).status_code==200
    small=client.post('/v1/research/weighted-recovery',json={**body,'precision_bits':2})
    assert small.status_code==200 and small.json()['status']=='COUNT_RESIDUE'
    assert small.json()['exact_count'] is None
    limit=client.post('/v1/research/weighted-recovery',json={**body,'max_work_assignments':1})
    assert limit.status_code==200 and limit.json()['status']=='UNKNOWN'
    assert limit.json()['evidence_level']=='NONE'
    for invalid in ({'packet_size':4},{'max_edges':1},{'group_span':3}):
        r=client.post('/v1/research/weighted-recovery',json={**body,**invalid})
        assert r.status_code==422
