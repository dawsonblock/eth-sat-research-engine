from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.audit.store import AuditStore


def test_v11_endpoints_and_cross_checked_jets(tmp_path):
    app.state.audit=AuditStore(tmp_path/'audit.sqlite')
    client=TestClient(app)
    body={'n':3,'clauses':[[1,2],[-2,3]],'timeout_s':5}
    r=client.post('/v1/research/packet-schedule',json=body)
    assert r.status_code==200,r.text
    assert r.json()['status']=='SCHEDULE'
    assert r.json()['evidence_level']=='RESEARCH_CROSS_CHECKED'
    r=client.post('/v1/research/cauchy-eliminate',json={**body,'packet_size':2,'node':1,
             'precision_bits':12,'jet_order':5,'optimize_packets':True})
    assert r.status_code==200,r.text
    x=r.json()
    assert x['status']=='JET_RESIDUES'
    assert x['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert x['jet_coefficients_mod_2_power']==x['independent_jet']
    assert x['stats']['packet_schedule'] is not None
    assert client.get('/health').json()['version']=='2.4.0'
    assert any('v1.1' in c['claim'] for c in client.get('/v1/paper/audit').json()['claims'])


def test_v11_unknown_and_reject(tmp_path):
    app.state.audit=AuditStore(tmp_path/'audit2.sqlite')
    client=TestClient(app)
    body={'n':3,'clauses':[[1,2],[-2,3]]}
    r=client.post('/v1/research/cauchy-eliminate',json={**body,'max_table_entries':2,'max_total_entries':256})
    assert r.status_code==200 and r.json()['status']=='UNKNOWN'
    assert r.json()['evidence_level']=='NONE'
    assert client.post('/v1/research/cauchy-eliminate',json={**body,'node':4,'packet_size':2}).status_code==422
    assert client.post('/v1/research/packet-schedule',json={**body,'packet_size':3}).status_code==422
    assert client.post('/v1/research/cauchy-eliminate',json={**body,'max_table_entries':1024,'max_total_entries':512}).status_code==422
    assert client.post('/v1/research/cauchy-eliminate',json={'n':7,'clauses':[[1,2,3,4,5,6,7]],'cross_check':True}).status_code==422
