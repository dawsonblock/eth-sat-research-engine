"""Independent exhaustive checks, edge cases, CLI/API and forged certificates."""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from itertools import product
import json
import random
from fastapi.testclient import TestClient
import pytest

from veritas.core.cnf import CNF
from veritas.solvers.marginals import exact_marginals, check_marginal_certificate
from veritas.solvers.weighted_dag import parse_weights, decode_fraction


def oracle(cnf, raw):
    weights = parse_weights(cnf.n, raw)
    z = Fraction(0)
    joints = [[Fraction(0), Fraction(0)] for _ in range(cnf.n + 1)]
    for bits in product((0, 1), repeat=cnf.n):
        if not cnf.evaluate({v: bool(bits[v-1]) for v in range(1,cnf.n+1)}):
            continue
        mass = Fraction(1)
        for v, b in enumerate(bits, 1):
            mass *= weights[v][b]
        z += mass
        for v, b in enumerate(bits, 1):
            joints[v][b] += mass
    return z, {str(v): [joints[v][0]/z, joints[v][1]/z] for v in range(1,cnf.n+1)} if z else None


def test_random_oracle_all_marginals():
    rng = random.Random(240024)
    options = [('0','1'),('1','0'),('1/2','1/2'),('1/3','2/3'),('2/5','3/5'),('3/4','1/4')]
    for _ in range(225):
        n = rng.randrange(0,8)
        clauses = [[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randrange(1,5))]
                   for _ in range(rng.randrange(0,9))] if n else [[]] if rng.randrange(2) else []
        cnf = CNF.from_lists(n,clauses)
        weights = {str(v):list(rng.choice(options)) for v in range(1,n+1)}
        result = exact_marginals(cnf, weights)
        z, expected = oracle(cnf,weights)
        assert decode_fraction(result.evidence_weight) == z
        assert result.status == ('POSTERIORS' if z else 'UNDEFINED')
        if z:
            assert {v:[decode_fraction(x) for x in pair] for v,pair in result.marginals.items()} == expected
            assert all(sum(pair) == 1 for pair in expected.values())
        else:
            assert result.marginals is None
        ok, message, status, marginals, nodes = check_marginal_certificate(cnf, weights, result.certificate)
        assert ok, message
        assert status == result.status and marginals == result.marginals and nodes == result.nodes


def test_independent_components_unused_variables_zero_weights():
    cnf = CNF.from_lists(7,[[1,2],[3,4],[-3,5]])  # 6 and 7 unused
    weights = {'1':['1/2','1/2'],'2':['1/3','2/3'],'3':['1/2','1/2'],
               '4':['0','1'],'5':['1/5','4/5'],'6':['1/4','3/4'],'7':['1','0']}
    result = exact_marginals(cnf,weights)
    z, expected = oracle(cnf, weights)
    assert result.status == 'POSTERIORS'
    assert decode_fraction(result.evidence_weight) == z
    assert {v: [decode_fraction(x) for x in a] for v,a in result.marginals.items()} == expected
    assert result.marginals['6'] == ['1/4','3/4']
    assert result.marginals['7'] == ['1','0']


def test_tampering_weight_binding_and_counts_rejected():
    cnf = CNF.from_lists(3,[[1,2],[-2,3]])
    weights = {str(v): ['1/2','1/2'] for v in range(1,4)}
    result = exact_marginals(cnf,weights)
    for mutate in ('posterior','binding','dag','count','shape'):
        forged = deepcopy(result.certificate)
        if mutate=='posterior': forged['marginals']['1']=['0','1']
        if mutate=='binding': forged['binding_sha256']='0'*64
        if mutate=='dag': forged['dag']['nodes'][-1]['count']='0'
        if mutate=='count': forged['evidence_weight']='1'
        if mutate=='shape': forged['unexpected']=True
        assert not check_marginal_certificate(cnf, weights, forged)[0]
    wrong = dict(weights); wrong['1']=['1/4','3/4']
    assert not check_marginal_certificate(cnf, wrong, result.certificate)[0]
    assert not check_marginal_certificate(CNF.from_lists(3,[[1]]), weights, result.certificate)[0]


def test_invalid_and_bounded_failures():
    c = CNF.from_lists(2,[[1,2]])
    with pytest.raises(ValueError,match='normalized'):
        exact_marginals(c, {'1':['1/2','1/2']})
    assert exact_marginals(c, {'1':['1/2','1/2'],'2':['1/2','1/2']}, max_nodes=1).status == 'UNKNOWN'
    assert exact_marginals(c, {'1':['1/2','1/2'],'2':['1/2','1/2']}, max_reverse_ops=1).status == 'UNKNOWN'


def test_api_marginals_and_checked_certificate():
    from veritas.api.main import app
    with TestClient(app) as client:
        body = {'n':2,'clauses':[[1,2]],'weights':{'1':['1/2','1/2'],'2':['1/2','1/2']}}
        response = client.post('/v1/probability/marginals',json=body)
        assert response.status_code==200,response.text
        payload=response.json()
        assert payload['status']=='POSTERIORS' and payload['marginals']=={'1':['1/3','2/3'],'2':['1/3','2/3']}
        assert payload['evidence_level']=='WEIGHTED_DAG_AND_MARGINAL_REPLAY_CHECKED'
        verified = client.post('/v1/certificates/check-marginals',json={**body,'certificate':payload['certificate']})
        assert verified.status_code==200 and verified.json()['status']=='VALID'
        forged=deepcopy(payload['certificate']);forged['marginals']['1']=['1','0']
        bad=client.post('/v1/certificates/check-marginals',json={**body,'certificate':forged})
        assert bad.status_code==200 and bad.json()['status']=='REJECTED'
        invalid=client.post('/v1/probability/marginals',json={'n':2,'clauses':[],'weights':{}})
        assert invalid.status_code==422
        assert client.get('/health').json()['version']=='2.4.0'
