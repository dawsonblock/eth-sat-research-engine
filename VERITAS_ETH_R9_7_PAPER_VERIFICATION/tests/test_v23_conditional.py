from fractions import Fraction
from copy import deepcopy
import random
from veritas.core.cnf import CNF
from veritas.solvers.conditional import exact_conditional
from veritas.solvers.weighted_dag import check_weighted_dag_certificate, decode_fraction
from test_v23_weighted_dag import oracle


def test_exact_posterior_against_oracle():
    rng = random.Random(230050)
    for _ in range(210):
        n = rng.randint(1, 7)
        evidence = CNF.from_lists(n, [[rng.choice((-1,1))*rng.randint(1,n)
                                      for _ in range(rng.randint(1,3))]
                                     for _ in range(rng.randint(0,7))])
        query = CNF.from_lists(n, [[rng.choice((-1,1))*rng.randint(1,n)
                                   for _ in range(rng.randint(1,3))]
                                  for _ in range(rng.randint(0,5))])
        weights = {str(v):['1/4','3/4'] if rng.randrange(2) else ['1/2','1/2'] for v in range(1,n+1)}
        actual = exact_conditional(evidence,query,weights)
        den = decode_fraction(oracle(evidence,weights))
        num = decode_fraction(oracle(evidence.with_extra_clauses([list(c) for c in query.clauses]),weights))
        if den == 0:
            assert actual.status == 'UNDEFINED'
        else:
            assert actual.status == 'PROBABILITY'
            assert decode_fraction(actual.probability) == num/den
            assert check_weighted_dag_certificate(evidence,weights,actual.evidence_certificate)[0]
            assert check_weighted_dag_certificate(evidence.with_extra_clauses([list(c) for c in query.clauses]),weights,actual.joint_certificate)[0]


def test_zero_evidence_and_missing_prior():
    evidence = CNF.from_lists(2, [[1],[-1]])
    query = CNF.from_lists(2, [[2]])
    assert exact_conditional(evidence,query,{'1':['1/2','1/2'],'2':['1/2','1/2']}).status == 'UNDEFINED'
    try:
        exact_conditional(CNF.from_lists(2, [[1]]),query,{'1':['1/2','1/2']})
    except ValueError:
        pass
    else: raise AssertionError('missing normalized weight not rejected')


def test_api_conditional():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    with TestClient(app) as client:
        body={'n':2,'clauses':[[1,2]],'query_clauses':[[1]],'weights':{'1':['1/2','1/2'],'2':['1/2','1/2']}}
        result=client.post('/v1/probability/conditional',json=body)
        assert result.status_code==200,result.text
        j=result.json()
        assert j['status']=='PROBABILITY' and j['probability']=='2/3' and j['evidence_level']=='WEIGHTED_COUNT_PROOF_CHECKED'
        forged=deepcopy(j['joint_certificate']);forged['count']='100'
        check=client.post('/v1/certificates/check-weighted-count-dag',json={
            'n':2,'clauses':[[1,2],[1]],'weights':body['weights'],'certificate':forged})
        assert check.status_code==200 and check.json()['status']=='REJECTED'
