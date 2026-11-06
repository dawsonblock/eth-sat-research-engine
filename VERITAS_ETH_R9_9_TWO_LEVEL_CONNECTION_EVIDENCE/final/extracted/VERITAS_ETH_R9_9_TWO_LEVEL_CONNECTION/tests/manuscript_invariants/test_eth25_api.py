from fastapi.testclient import TestClient
from veritas.api.main import app


def test_parameters_endpoint_explicit_scope():
    c=TestClient(app)
    r=c.post('/v1/research/eth/parameters',json={'s':1000})
    assert r.status_code==200
    assert r.json()['mode']=='MANUSCRIPT_EXACT'
    assert not r.json()['eligible']
    assert c.get('/v1/research/eth/status').json()['subexponential_solver'] is False


def test_packing_endpoint_report():
    c=TestClient(app)
    r=c.post('/v1/research/eth/packing',json={'edges':[[0,1],[0,1]],'a':1,'r':2})
    assert r.status_code==200
    cert=r.json()
    r2=c.post('/v1/research/eth/packing/check',json={'certificate':cert})
    assert r2.status_code==200
    assert r2.json()['valid_structure']
    cert['packets'][0]['slots'][0]=10000
    assert c.post('/v1/research/eth/packing/check',json={'certificate':cert}).json()['status']=='INVALID_CERTIFICATE'


def test_ring_endpoint_exact():
    c=TestClient(app)
    r=c.post('/v1/research/eth/ring',json={'precision':8,'degree':4,'coefficients':[1,1]})
    assert r.status_code==200
    assert r.json()['is_unit']
    assert r.json()['status']=='EXACT_RING_REFERENCE'
