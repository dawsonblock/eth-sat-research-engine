"""Upgrade-specific independent exact equivalence, API and fail-closed tests."""
import random
import pytest
from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.contraction_planner import (copy3_model, original_cnf_model,
    elimination_order, choose_plan, ContractLimit)
from veritas.research.indexed_contract import indexed_contract_order
from veritas.research.sparse_contract import sparse_contract_order
from veritas.research.adaptive_contract import adaptive_count


def test_exact_modes_over_random_inputs():
    rng=random.Random(16062026)
    for _ in range(140):
        n=rng.randint(0,7)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n)
                  for __ in range(rng.randint(0,4))]
                 for _ in range(rng.randint(0,10))] if n else ([] if rng.randrange(2) else [[]])
        cnf=CNF.from_lists(n,clauses)
        expected=exhaustive_count(cnf)
        for model in (original_cnf_model(cnf), copy3_model(cnf)):
            plan=elimination_order(model,'min_degree')
            count,stat=indexed_contract_order(model,plan)
            assert count==expected
            assert stat.evaluated_assignments==plan.estimated_assignments
            sp,spstats=sparse_contract_order(model,plan)
            assert sp==expected
            assert spstats.peak_table_entries<=65536
            for bits in (1,4,9):
                got,_=indexed_contract_order(model,plan,modulus=1<<bits)
                sparse,_=sparse_contract_order(model,plan,modulus=1<<bits)
                assert got==sparse==expected%(1<<bits)


def test_auto_and_thorough_and_modes():
    cnf=CNF.from_lists(10,[[1,2],[1,-3],[-3,4],[4,-5],[6,7],[-7,8],[9,10]])
    expected=exhaustive_count(cnf)
    for mode in ('legacy','indexed','sparse'):
        for planner in ('auto','thorough'):
            result=adaptive_count(cnf,execution_mode=mode,portfolio_mode=planner)
            assert int(result['count'])==expected
            assert result['execution_mode']==mode
            assert result['portfolio_mode']==planner


def test_sparse_respects_resource_limits():
    cnf=CNF.from_lists(6,[[i,j] for i in range(1,7) for j in range(i+1,7)])
    model=original_cnf_model(cnf)
    plan=elimination_order(model)
    with pytest.raises(ContractLimit):
        sparse_contract_order(model,plan,max_work_assignments=1)
    with pytest.raises(ContractLimit):
        indexed_contract_order(model,plan,max_work_assignments=1)
    for planner in ('INVALID', '', 7):
        with pytest.raises(ValueError):
            adaptive_count(cnf,portfolio_mode=planner)
    with pytest.raises(ValueError):
        adaptive_count(cnf,execution_mode='nope')


def test_api_new_execution_modes(tmp_path):
    from veritas.audit.store import AuditStore
    app.state.audit=AuditStore(tmp_path/'v16.sqlite3')
    c=TestClient(app)
    inp={'n':3,'clauses':[[1,2],[-1,3]],'execution_mode':'sparse','portfolio_mode':'thorough'}
    r=c.post('/v1/research/adaptive-contract',json=inp)
    assert r.status_code==200,r.text
    assert r.json()['status']=='EXACT_COUNT'
    assert r.json()['count']=='4'
    assert r.json()['independent_count_checked'] is True
    assert r.json()['execution_mode']=='sparse'
    assert c.get('/health').json()['version']=='2.4.0'
    assert any('v1.6' in c['claim'] for c in c.get('/v1/paper/audit').json()['claims'])
    rejected=c.post('/v1/research/adaptive-contract',json={**inp,'execution_mode':'bad'})
    assert rejected.status_code==422
