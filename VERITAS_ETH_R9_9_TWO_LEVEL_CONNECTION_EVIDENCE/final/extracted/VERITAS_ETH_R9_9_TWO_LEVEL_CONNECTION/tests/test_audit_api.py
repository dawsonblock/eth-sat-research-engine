from fastapi.testclient import TestClient
import pytest
from veritas.api.main import app
from veritas.audit.store import AuditStore

@pytest.fixture
def client(tmp_path):
    app.state.audit = AuditStore(tmp_path / 'audit.sqlite3')
    yield TestClient(app)
    app.state.audit = None


def test_end_to_end(client):
    h = client.get('/health'); assert h.status_code == 200 and h.json()['audit_chain_valid']
    v = client.post('/v1/verify',json={'n':2,'clauses':[[1],[-1,2]]})
    assert v.status_code == 200
    assert v.json()['status'] == 'SAT' and v.json()['evidence_level'] == 'WITNESS_CHECKED'
    u = client.post('/v1/verify',json={'n':1,'clauses':[[1],[-1]]})
    assert u.json()['status'] == 'UNSAT' and u.json()['evidence_level'] == 'SOLVER_ONLY'
    c = client.post('/v1/count',json={'n':3,'clauses':[[1,2],[-1,3]]})
    assert c.json()['count'] == '4' and c.json()['evidence_level'] == 'CROSS_CHECKED'
    a = client.get('/v1/audits/'+c.json()['audit_sha256'])
    assert a.json()['entry_valid'] and a.json()['entire_local_chain_valid']
    assert client.get('/health').json()['audit_records'] == 3


def test_entailment(client):
    r = client.post('/v1/counterexample',json={'premises':['A -> B','A'],'conclusion':'B'})
    assert r.status_code == 200 and r.json()['status'] == 'ENTAILED'
    r = client.post('/v1/counterexample',json={'premises':['A -> B'],'conclusion':'B'})
    assert r.json()['status'] == 'NOT_ENTAILED' and r.json()['counterexample'] == {'A':False,'B':False}


def test_formalize_and_research(client):
    f = client.post('/v1/formalize',json={'expression':'A & B'})
    assert f.json()['status'] == 'COMPILED_REVIEW_REQUIRED'
    t = client.post('/v1/research/contract',json={'n':3,'clauses':[[1,2],[-1,3]]})
    assert t.json()['count'] == '4'
    assert t.json()['evidence_level'] == 'RESEARCH_CROSS_CHECKED'
    assert client.get('/v1/paper/audit').json()['status'] == 'INCOMPLETE_PAPER_REPRODUCTION'
    assert client.get('/').status_code == 200


def test_rejections(client):
    assert client.post('/v1/count',json={'n':1,'clauses':[[2]]}).status_code == 422
    assert client.post('/v1/formalize',json={'expression':'A = B'}).status_code == 422
    assert client.post('/v1/count',json={'n':1,'clauses':[], 'backend':'nonexistent'}).status_code == 422
    assert client.get('/v1/audits/bad').status_code == 422


def test_audit_detection(tmp_path):
    import sqlite3
    db = AuditStore(tmp_path / 'tamper.db')
    h1 = db.add({'hello':1}); db.add({'hello':2})
    assert db.verify_chain()[0]
    with sqlite3.connect(db.path) as conn:
        conn.execute('UPDATE entries SET payload=? WHERE hash=?', ('{"hello":99}',h1))
    assert not db.verify_chain()[0]
