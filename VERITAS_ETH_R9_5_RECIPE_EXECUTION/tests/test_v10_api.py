import os
from fastapi.testclient import TestClient
from veritas.api.main import app


def test_v10_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv('VERITAS_AUDIT_DB',str(tmp_path/'audit.sqlite'))
    from veritas.audit.store import AuditStore
    app.state.audit=AuditStore(tmp_path/'audit.sqlite')
    client=TestClient(app)
    body={'n':3,'clauses':[[1,2],[-2,3]],'timeout_s':5.0}
    answer=client.post('/v1/research/separator-contract',json=body)
    assert answer.status_code==200,answer.text
    got=answer.json()
    assert got['status']=='EXACT_COUNT' and got['count']=='4'
    assert got['evidence_level']=='RESEARCH_CROSS_CHECKED'
    response=client.post('/v1/research/grouped-cauchy',json={**body,'node':1,'packet_size':2,
                    'precision_bits':8,'jet_order':5})
    assert response.status_code==200,response.text
    data=response.json()
    assert data['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert data['jet_coefficients_mod_2_power']==data['independent_jet']
    assert client.get('/health').json()['version']=='2.4.0'


def test_v10_reject_uncertified_big_or_bad_inputs(tmp_path):
    from veritas.audit.store import AuditStore
    app.state.audit=AuditStore(tmp_path/'audit2.sqlite')
    client=TestClient(app)
    assert client.post('/v1/research/separator-contract',json={
      'n':10,'clauses':[[1,2,3,4,5],[6,7,8,9,10]],'max_cut_edges':1,
      'cross_check':True}).status_code==200  # cross-check limited by occurrences not width
    fail=client.post('/v1/research/grouped-cauchy',json={'n':2,'clauses':[[1,2]],
              'node':2,'packet_size':2})
    assert fail.status_code==422
