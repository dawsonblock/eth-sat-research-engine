from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.audit.store import AuditStore


def test_v12_api_crosscheck_and_limits(tmp_path):
    app.state.audit=AuditStore(tmp_path/'v12.sqlite3')
    client=TestClient(app)
    body={'n':3,'clauses':[[1,2],[-2,3]],'packet_size':2,'node':1,
          'precision_bits':12,'jet_order':5,'timeout_s':7}
    r=client.post('/v1/research/weighted-children',json=body)
    assert r.status_code==200,r.text
    obj=r.json()
    assert obj['status']=='JET_RESIDUES'
    assert obj['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert obj['jet_coefficients_mod_2_power']==obj['independent_jet']
    assert obj['stats']['recursion_calls']>0
    assert obj['stats']['internal_tensors']>0
    assert client.get('/health').json()['version']=='2.4.0'
    assert any('v1.2' in x['claim'] for x in client.get('/v1/paper/audit').json()['claims'])
    r=client.post('/v1/research/weighted-children',json={**body,'max_work_assignments':1})
    assert r.status_code==200 and r.json()['status']=='UNKNOWN'
    assert r.json()['evidence_level']=='NONE'
    assert client.post('/v1/research/weighted-children',json={**body,'group_span':3}).status_code==422
    assert client.post('/v1/research/weighted-children',json={**body,'node':3}).status_code==422
    assert client.post('/v1/research/weighted-children',json={**body,'precision_bits':0}).status_code==422
