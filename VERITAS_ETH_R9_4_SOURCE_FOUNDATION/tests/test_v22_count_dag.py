import copy
import random

from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.solvers.count_certificates import make_count_certificate
from veritas.solvers.count_dag import (
    make_dag_count_certificate, check_dag_count_certificate, _root_state, _rule,
)


def prove(cnf):
    proof = make_dag_count_certificate(cnf, timeout_s=5)
    assert proof.status == 'COUNT', proof.reason
    valid, why, counted, nodes = check_dag_count_certificate(cnf, proof.certificate)
    assert valid, why
    assert counted == proof.count == exhaustive_count(cnf, max_vars=12)
    assert nodes == proof.nodes
    return proof


def test_edge_cases():
    for cnf in (
        CNF.from_lists(0, []), CNF.from_lists(0, [[]]),
        CNF.from_lists(4, []), CNF.from_lists(4, [[]]),
        CNF.from_lists(5, [[1,2],[-1,3]]),
        CNF.from_lists(5, [[1,-1],[2,-2]]),
        CNF.from_lists(4, [[1],[1,-1],[-2,3],[-3,4]]),
        CNF.from_lists(4, [[1,2],[-1,-2],[3,4]]),
    ):
        prove(cnf)


def test_random_exact():
    rng=random.Random(220026)
    for _ in range(1500):
        n=rng.randint(0,9)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(0,4))]
                 if n else [] for _ in range(rng.randint(0,12))]
        prove(CNF.from_lists(n,clauses))


def test_component_dag_is_much_smaller_than_shannon_tree():
    # 12 disjoint binary OR constraints, plus unused variables. Producing a
    # component product certificate is much smaller than a Shannon tree.
    cnf=CNF.from_lists(26,[[2*i+1,2*i+2] for i in range(12)])
    dag=make_dag_count_certificate(cnf)
    old=make_count_certificate(cnf)
    assert dag.status=='COUNT'
    assert dag.count==3**12*4
    assert check_dag_count_certificate(cnf,dag.certificate)[0]
    assert old.status=='COUNT'
    assert dag.nodes < old.nodes/5


def test_verifier_rejects_tampering_and_cross_formula_reuse():
    cnf=CNF.from_lists(6,[[1,2],[3,4],[5,6]])
    proof=prove(cnf).certificate
    corruptions=[]
    a=copy.deepcopy(proof);a['count']='999';corruptions.append(a)
    a=copy.deepcopy(proof);a['cnf_sha256']='0'*64;corruptions.append(a)
    a=copy.deepcopy(proof);a['nodes'][-1]['count']='4';corruptions.append(a)
    a=copy.deepcopy(proof);a['nodes'][-1]['children']=[];corruptions.append(a)
    a=copy.deepcopy(proof);a['nodes'][-1]['kind']='satisfied';corruptions.append(a)
    a=copy.deepcopy(proof);a['nodes'][-1]['children']=[len(a['nodes'])-1];corruptions.append(a)
    a=copy.deepcopy(proof);a['nodes'][0]['children']=[999999];corruptions.append(a)
    a=copy.deepcopy(proof);a['nodes'].append({'kind':'conflict','count':'0','children':[]});corruptions.append(a)
    for bad in corruptions:
        assert not check_dag_count_certificate(cnf,bad)[0]
    assert not check_dag_count_certificate(CNF.from_lists(6,[[1]]), proof)[0]


def test_budget_fail_closed():
    cnf=CNF.from_lists(6,[[1,2],[3,4],[5,6]])
    p=make_dag_count_certificate(cnf,max_nodes=1)
    assert p.status=='UNKNOWN' and p.certificate is None
    assert make_dag_count_certificate(cnf,max_bytes=256).status=='UNKNOWN'


def test_api_v22():
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    with TestClient(app) as client:
        body={'n':6,'clauses':[[1,2],[3,4],[5,6]]}
        result=client.post('/v1/certify/count-dag',json=body)
        assert result.status_code==200, result.text
        data=result.json()
        assert data['status']=='COUNT' and data['count']=='27'
        assert data['evidence_level']=='COUNT_PROOF_CHECKED'
        check=client.post('/v1/certificates/check-count-dag',json={**body,'certificate':data['certificate']})
        assert check.status_code==200
        assert check.json()['status']=='VALID'
        forged=copy.deepcopy(data['certificate']);forged['count']='25'
        reject=client.post('/v1/certificates/check-count-dag',json={**body,'certificate':forged})
        assert reject.status_code==200
        assert reject.json()['status']=='REJECTED'
