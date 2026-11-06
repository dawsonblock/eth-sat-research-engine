"""Differential exact-rational checks and adversarial certificate tampering."""
from copy import deepcopy
from fractions import Fraction
from itertools import product
import random
import pytest

from veritas.core.cnf import CNF
from veritas.solvers.count_dag import make_dag_count_certificate
from veritas.solvers.weighted_dag import (
    make_weighted_dag_certificate, check_weighted_dag_certificate,
    parse_weights, encode_fraction, decode_fraction,
)


def oracle(cnf, supplied):
    weights = parse_weights(cnf.n, supplied)
    value = Fraction(0)
    for bits in product((False, True), repeat=cnf.n):
        model = {i + 1: v for i, v in enumerate(bits)}
        if cnf.evaluate(model):
            weight = Fraction(1)
            for i, bit in enumerate(bits, 1):
                weight *= weights[i][int(bit)]
            value += weight
    return encode_fraction(value)


def verify(cnf, weights):
    result = make_weighted_dag_certificate(cnf, weights, timeout_s=5)
    assert result.status == 'WEIGHTED_COUNT', result.reason
    accepted, why, count, nodes = check_weighted_dag_certificate(cnf, weights, result.certificate)
    assert accepted, why
    assert count == result.count == oracle(cnf, weights)
    assert nodes == result.nodes
    return result


def test_edge_cases():
    for cnf in (CNF.from_lists(0, []), CNF.from_lists(0, [[]]),
                CNF.from_lists(4, []), CNF.from_lists(4, [[]]),
                CNF.from_lists(3, [[1,2],[-1,3]]), CNF.from_lists(4, [[1,-1], [2,-2]]),
                CNF.from_lists(3, [[1],[-1]])):
        verify(cnf, {str(v): ['0', '1'] if v % 2 else ['1/3', '2/3']
                     for v in range(1, cnf.n + 1)})
        verify(cnf, {})


def test_random_differential():
    rng = random.Random(230026)
    weights = ['0', '1', '2', '1/2', '2/3', '3/4', '5/2', '1/4']
    for _ in range(1350):
        n = rng.randint(0, 8)
        clauses = [[rng.choice([-1, 1]) * rng.randint(1, n)
                    for _ in range(rng.randint(0, 4))] if n else []
                   for _ in range(rng.randint(0, 10))]
        cnf = CNF.from_lists(n, clauses)
        assigned = {str(v): [rng.choice(weights), rng.choice(weights)]
                    for v in range(1, n + 1) if rng.randrange(4) != 0}
        verify(cnf, assigned)


def test_ones_equals_existing_unweighted_count():
    rng = random.Random(230077)
    for _ in range(150):
        n = rng.randint(0, 9)
        cnf = CNF.from_lists(n, [[rng.choice([-1, 1]) * rng.randint(1, n)
                                 for _ in range(rng.randint(0, 3))] if n else []
                                for _ in range(rng.randint(0, 10))])
        old = make_dag_count_certificate(cnf)
        current = verify(cnf, {})
        assert old.status == 'COUNT' and str(old.count) == current.count


def test_weights_are_bound_to_proof():
    cnf = CNF.from_lists(5, [[1,2],[-1,3],[4,5]])
    weights = {'1': ['1/2', '1/2'], '4': ['2/3', '1/3']}
    result = verify(cnf, weights)
    cert = result.certificate
    mutations = []
    def mutated(change):
        item = deepcopy(cert)
        change(item)
        mutations.append(item)
    mutated(lambda p: p.update(count='999'))
    mutated(lambda p: p.update(weights_sha256='0'*64))
    mutated(lambda p: p['nodes'][-1].update(count='4'))
    mutated(lambda p: p['nodes'][-1].update(kind='satisfied'))
    mutated(lambda p: p['nodes'][-1].update(children=[]))
    mutated(lambda p: p['nodes'][-1].update(children=[len(p['nodes'])-1]))
    mutated(lambda p: p['nodes'].append({'kind':'conflict','count':'0','children':[]}))
    mutated(lambda p: p.update(count='02'))
    mutated(lambda p: p.update(count='2/4'))
    for item in mutations:
        assert not check_weighted_dag_certificate(cnf, weights, item)[0]
    assert not check_weighted_dag_certificate(cnf, {'1': ['1/3', '2/3']}, cert)[0]
    assert not check_weighted_dag_certificate(CNF.from_lists(5, [[1]]), weights, cert)[0]


def test_input_constraints_and_budget():
    cnf = CNF.from_lists(5, [[1,2], [3,4]])
    for weights in ({'0': ['1', '1']}, {'1': ['-1', '2']}, {'1': ['1/0', '1']},
                    {'1': ['01', '1']}, {'1': [0, '1']}, {'6': ['1', '1']},
                    {'1': ['1e2', '1']}, {'1': ['1/1000001', '1']}):
        with pytest.raises(ValueError):
            make_weighted_dag_certificate(cnf, weights)
    assert make_weighted_dag_certificate(cnf, {}, max_nodes=1).status == 'UNKNOWN'
    assert make_weighted_dag_certificate(cnf, {}, max_bytes=256).status == 'UNKNOWN'
    assert decode_fraction('1/2') == Fraction(1,2)
    with pytest.raises(ValueError):decode_fraction('2/4')


def test_api_v23():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    with TestClient(app) as client:
        body={'n':3, 'clauses':[[1,2],[-1,3]],
              'weights':{'1':['1/2','1/2'],'2':['1/3','2/3'],'3':['2/3','1/3']}}
        response=client.post('/v1/certify/weighted-count-dag', json=body)
        assert response.status_code==200,response.text
        item=response.json()
        assert item['status']=='WEIGHTED_COUNT' and item['count']==oracle(CNF.from_lists(3,body['clauses']),body['weights'])
        assert item['evidence_level']=='WEIGHTED_COUNT_PROOF_CHECKED' and item['normalized_distribution']
        checked=client.post('/v1/certificates/check-weighted-count-dag', json={**body, 'certificate':item['certificate']})
        assert checked.status_code==200 and checked.json()['status']=='VALID'
        bad=deepcopy(item['certificate']); bad['count']='123'
        refused=client.post('/v1/certificates/check-weighted-count-dag',json={**body,'certificate':bad})
        assert refused.status_code==200 and refused.json()['status']=='REJECTED'
        bad_w=client.post('/v1/certify/weighted-count-dag',json={**body,'weights':{'1':['-1','1']}})
        assert bad_w.status_code==422
