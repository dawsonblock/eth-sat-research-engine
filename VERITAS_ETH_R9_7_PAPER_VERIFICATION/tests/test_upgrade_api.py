import pytest
from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.audit.store import AuditStore

@pytest.fixture
def client(tmp_path):
    app.state.audit = AuditStore(tmp_path / 'upgrade.sqlite3')
    yield TestClient(app)
    app.state.audit = None


def test_certify_unsat_and_check_endpoint(client):
    payload = {'n':2,'clauses':[[1,2],[1,-2],[-1,2],[-1,-2]]}
    r = client.post('/v1/certify/unsat', json=payload)
    assert r.status_code == 200, r.text
    val = r.json()
    assert val['status'] == 'UNSAT' and val['evidence_level'] == 'PROOF_CHECKED'
    checked = client.post('/v1/certificates/check',json={**payload,'certificate':val['certificate']})
    assert checked.status_code == 200 and checked.json()['status'] == 'VALID'
    wrong = client.post('/v1/certificates/check', json={'n':2,'clauses':[], 'certificate':val['certificate']})
    assert wrong.status_code == 200 and wrong.json()['status'] == 'REJECTED'
    v = client.post('/v1/verify', json={**payload,'request_unsat_certificate':True})
    assert v.status_code == 200 and v.json()['evidence_level'] == 'PROOF_CHECKED'
    assert client.get('/health').json()['audit_chain_valid']


def test_certify_sat_timeout_and_invalid(client):
    sat = client.post('/v1/certify/unsat',json={'n':3,'clauses':[[1,2]]})
    assert sat.json()['status'] == 'SAT' and sat.json()['evidence_level'] == 'WITNESS_CHECKED'
    contradiction = {'n':3,'clauses':[[a,b,c] for a in (1,-1) for b in (2,-2) for c in (3,-3)], 'max_nodes':1}
    limited = client.post('/v1/certify/unsat',json=contradiction)
    assert limited.status_code == 200 and limited.json()['status'] == 'UNKNOWN'
    assert limited.json()['certificate'] is None
    bad = client.post('/v1/certificates/check', json={'n':1,'clauses':[[1]],'certificate':{}})
    assert bad.status_code == 200 and bad.json()['status'] == 'REJECTED'


def test_projected_endpoint(client):
    r = client.post('/v1/count/projected',json={'n':3,'clauses':[[1,2]],'projected':[1,2]})
    assert r.status_code == 200
    assert r.json()['count'] == '3' and r.json()['evidence_level'] == 'CROSS_CHECKED'
    assert r.json()['count_semantics'] == 'distinct_projected_valuations_with_existential_extension'
    r = client.post('/v1/count/projected',json={'n':3,'clauses':[[1,2]],'projected':[]})
    assert r.json()['count'] == '1'
    r = client.post('/v1/count/projected',json={'n':3,'clauses':[[1,2]],'projected':[1,1]})
    assert r.status_code == 422
    r = client.post('/v1/count/projected',json={'n':3,'clauses':[[1,2]],'projected':[3],'max_nodes':1})
    assert r.json()['status'] == 'UNKNOWN' and r.json()['count'] is None


def test_entailment_proof_and_equiv(client):
    r = client.post('/v1/counterexample',json={'premises':['A->B','A'],'conclusion':'B','request_unsat_certificate':True})
    assert r.status_code == 200 and r.json()['status'] == 'ENTAILED'
    assert r.json()['evidence_level'] == 'PROOF_CHECKED' and r.json()['certificate']
    eq = client.post('/v1/equivalent',json={'left':'A -> B','right':'!A | B', 'request_unsat_certificate':True})
    assert eq.status_code == 200, eq.text
    assert eq.json()['status'] == 'EQUIVALENT' and eq.json()['evidence_level'] == 'PROOF_CHECKED'
    ne = client.post('/v1/equivalent',json={'left':'A & B','right':'A | B'})
    assert ne.status_code == 200 and ne.json()['status'] == 'NOT_EQUIVALENT'
    assert ne.json()['left_value'] != ne.json()['right_value']
    assert ne.json()['evidence_level'] == 'WITNESS_CHECKED'
