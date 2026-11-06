"""HTTP contracts for the v0.9 small reference research endpoints."""
from fastapi.testclient import TestClient
from veritas.api.main import app

client=TestClient(app)


def test_modes_matches_original_local_evaluation_and_evidence():
    response=client.post('/v1/research/cauchy-modes',json={
        'n':3,'clauses':[[1,2],[-2]], 'packet_size':2, 'node':1,
        'precision_bits':7,'jet_order':7})
    assert response.status_code==200, response.text
    data=response.json()
    assert data['status']=='JET_RESIDUES'
    assert data['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert len(data['jet_coefficients_mod_2_power'])==7
    assert data['stats']['available_cross_modes']==len(data['cross_modes'])
    assert data['audit_sha256']


def test_modular_hermite_count_and_precision_contract():
    response=client.post('/v1/research/cauchy-hermite',json={
        'n':3,'clauses':[[1,2],[-2]],'packet_size':2,'precision_bits':6})
    assert response.status_code==200, response.text
    data=response.json()
    assert data['status']=='COUNT_RESIDUE'
    assert data['evidence_level']=='RESEARCH_CROSS_CHECKED'
    assert int(data['recovered_constant_mod_2_power'])==int(data['independently_contracted_original_count'])%64
    assert data['input_precision_bits']>=data['target_precision_bits']+data['guard_bits']
    assert 0 not in data['nodes']


def test_strict_rejection_and_audit_scope():
    bad=client.post('/v1/research/cauchy-modes',json={'n':1,'clauses':[[1]],'node':3})
    assert bad.status_code==422
    many=client.post('/v1/research/cauchy-hermite',json={'n':5,'clauses':[[1,2,3,4,5]]})
    assert many.status_code==422
    audit=client.get('/v1/paper/audit').json()
    assert audit['status']=='INCOMPLETE_PAPER_REPRODUCTION'
    assert any(x['implementation']=='SMALL_EXACT_VALUATION_CERTIFIED_REFERENCE_NOT_D4_4' for x in audit['claims'])
    assert any(x['implementation']=='EXACT_BOUNDED_RECONSTRUCTION_NOT_FULL_D5' for x in audit['claims'])
    assert client.get('/health').json()['version']=='2.4.0'
