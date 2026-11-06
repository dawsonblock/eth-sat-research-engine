"""New v0.6 API regressions: independent count evidence and exact polynomials."""
from fastapi.testclient import TestClient
from veritas.api.main import app

client = TestClient(app)


def test_certified_count_api_and_checker():
    formula = {"n":3, "clauses":[[1,2],[-1,3]]}
    response = client.post('/v1/certify/count', json=formula)
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer['status'] == 'COUNT'
    assert answer['count'] == '4'
    assert answer['evidence_level'] == 'COUNT_PROOF_CHECKED'
    assert answer['generator_nodes'] == answer['checker_nodes']
    accepted = client.post('/v1/certificates/check-count',json={**formula,"certificate":answer['certificate']})
    assert accepted.status_code == 200 and accepted.json()['status'] == 'VALID'
    bad = {**answer['certificate'], "count":"7"}
    rejected = client.post('/v1/certificates/check-count',json={**formula,"certificate":bad})
    assert rejected.status_code == 200 and rejected.json()['status'] == 'REJECTED'


def test_certified_count_unknown():
    response = client.post('/v1/certify/count',json={"n":6,"clauses":[[1,2,3],[4,5,6]],"max_nodes":1})
    assert response.status_code == 200
    assert response.json()['status'] == 'UNKNOWN'
    assert response.json()['certificate'] is None


def test_violation_api_exact():
    formula = {"n":2,"clauses":[[1],[-1]]}
    answer = client.post('/v1/research/violation-spectrum',json=formula)
    assert answer.status_code == 200,answer.text
    obj = answer.json()
    assert obj['status']=='POLYNOMIAL'
    assert obj['coefficients']==['0','4','0']
    assert obj['satisfying_assignments']=='0'
    assert obj['min_violated_clauses']==1
    assert obj['max_satisfied_clauses']==1
    assert obj['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert obj['H_at_1']=='4'


def test_violation_api_modular_residues():
    formula = {"n":3,"clauses":[[1],[-1]],"precision_bits":1}
    obj = client.post('/v1/research/violation-spectrum',json=formula).json()
    assert obj['coefficients']==['0','0','0']
    assert obj['coefficient_semantics']=='residue_mod_2_power'
    assert obj['satisfying_assignments'] is None
    assert obj['min_violated_clauses'] is None
    obj2=client.post('/v1/research/violation-spectrum',json={**formula,"precision_bits":4}).json()
    assert obj2['coefficients']==['0','8','0']
    assert obj2['coefficient_semantics']=='exact_integer'


def test_reject_large_polynomial_network():
    obj = client.post('/v1/research/violation-spectrum',json={'n':1, 'clauses':[[1]]*14})
    assert obj.status_code == 422


def test_paper_audit_is_honest():
    obj = client.get('/v1/paper/audit').json()
    assert obj['status']=='INCOMPLETE_PAPER_REPRODUCTION'
    text = str(obj)
    assert 'Cauchy deformation' in text
    assert 'NOT_IMPLEMENTED' in text
