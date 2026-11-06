"""Independent enumeration verifies global optimality on tiny primal graphs."""
import itertools
import random
import pytest
from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.audit.store import AuditStore
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.contraction_planner import (original_cnf_model, ContractLimit,
                                                  elimination_order)
from veritas.research.optimal_order import optimize_small_model, replay_order
from veritas.research.adaptive_contract import adaptive_count


def test_exact_dp_vs_all_orders_independent():
    rng=random.Random(17002026)
    for _ in range(35):
        n=rng.randrange(0,7)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n)
                  for _ in range(rng.randrange(0,4))]
                 for _ in range(rng.randrange(0,9))] if n else [[]] if rng.randrange(2) else []
        model=original_cnf_model(CNF.from_lists(n,clauses))
        replay=[replay_order(model,perm) for perm in itertools.permutations(model.variables)]
        opt_work,proof=optimize_small_model(model,objective='work')
        opt_width,_=optimize_small_model(model,objective='width')
        assert opt_work.estimated_assignments==min(c for c,w in replay)
        assert opt_width.induced_width==min(w for c,w in replay)
        assert opt_width.estimated_assignments==min(c for c,w in replay if w==opt_width.induced_width)
        assert replay_order(model,opt_work.order)==(opt_work.estimated_assignments,opt_work.induced_width)
        assert proof.certificate_type=='EXACT_SUBSET_DYNAMIC_PROGRAM_RECOMPUTABLE'


def test_optimal_count_and_modulus():
    rng=random.Random(17012026)
    for _ in range(55):
        n=rng.randrange(0,9)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randrange(0,4))]
                 for _ in range(rng.randrange(0,10))] if n else [[]]
        cnf=CNF.from_lists(n,clauses)
        expected=exhaustive_count(cnf)
        result=adaptive_count(cnf,portfolio_mode='optimal_small',include_copy3=False,
                              enable_separators=False,execution_mode='indexed')
        assert result['status']=='EXACT_COUNT'
        assert int(result['count'])==expected
        assert result['selected_heuristic']=='exact_subset_dp_work'
        assert result['optimal_order_work_certified']
        assert result['candidates'][0]['globally_optimal_dense_work']
        modular=adaptive_count(cnf,portfolio_mode='optimal_small',precision_bits=5,
                               include_copy3=False,enable_separators=False,execution_mode='sparse')
        assert int(modular['count'])==expected%32


def test_limits_and_invalid_input():
    big=original_cnf_model(CNF.from_lists(13,[[1,2],[4,5]]))
    with pytest.raises(ContractLimit):
        optimize_small_model(big)
    small=original_cnf_model(CNF.from_lists(3,[[1,2]]))
    for objective in ('fastest_runtime','nonsense',None):
        with pytest.raises(ValueError):
            optimize_small_model(small,objective=objective)
    with pytest.raises(ValueError):
        replay_order(small,(0,0,1))
    with pytest.raises(ContractLimit):
        adaptive_count(CNF.from_lists(13,[[1,2]]),portfolio_mode='optimal_small',
                       enable_separators=False)


def test_api_optimal_small_and_failure(tmp_path):
    app.state.audit=AuditStore(tmp_path/'v17.sqlite3')
    c=TestClient(app)
    payload={'n':4,'clauses':[[1,2],[-1,3],[3,4]],
             'portfolio_mode':'optimal_small','enable_separators':False,
             'execution_mode':'indexed','cross_check':True}
    r=c.post('/v1/research/adaptive-contract',json=payload)
    assert r.status_code==200,r.text
    body=r.json()
    assert body['count']==str(exhaustive_count(CNF.from_lists(4,payload['clauses'])))
    assert body['independent_count_checked'] is True
    assert body['optimal_order_work_certified'] is True
    assert c.get('/health').json()['version']=='2.4.0'
    assert c.post('/v1/research/adaptive-contract',json={**payload,'portfolio_mode':'foo'}).status_code==422
    denied=c.post('/v1/research/adaptive-contract',json={**payload,'n':13})
    assert denied.status_code==200 and denied.json()['status']=='UNKNOWN'
    assert 'count' not in denied.json()


def test_optimization_is_strictly_better_on_fixed_counterexample(tmp_path):
    clauses=[[-7,9],[-2,4],[3,-5],[8,1],[3,-7],[-4,8],[1,5,-8],
             [8,-5],[-3,7,2],[-9,1,5],[5,-7],[-3,7],[-1,6,4],
             [2,6],[1,-3],[-7,-5],[-1,8,-5],[-8,4,7],[-9,3,-7],
             [-7,2],[-8,-6]]
    cnf=CNF.from_lists(9,clauses)
    model=original_cnf_model(cnf)
    quick=elimination_order(model,'min_degree')
    optimum,evidence=optimize_small_model(model)
    assert quick.estimated_assignments==222
    assert optimum.estimated_assignments==190
    assert optimum.induced_width==4 and quick.induced_width==5
    assert evidence.exhaustive_subset_states==512
    # Verified results still come from the exact evaluator, not the proxy.
    result=adaptive_count(cnf,portfolio_mode='optimal_small',enable_separators=False,
                          execution_mode='indexed')
    assert int(result['count'])==exhaustive_count(cnf)
    app.state.audit=AuditStore(tmp_path/'order.sqlite3')
    c=TestClient(app)
    r=c.post('/v1/research/optimal-order',json={'n':9,'clauses':clauses})
    assert r.status_code==200,r.text
    data=r.json()
    assert data['status']=='FINITE_GRAPH_OPTIMAL_ORDER'
    assert data['plan']['estimated_assignments']==190
    assert data['count'] is None
    assert data['replay_verified']
    denied=c.post('/v1/research/optimal-order',json={'n':13,'clauses':clauses})
    assert denied.status_code==200 and denied.json()['status']=='UNKNOWN'
