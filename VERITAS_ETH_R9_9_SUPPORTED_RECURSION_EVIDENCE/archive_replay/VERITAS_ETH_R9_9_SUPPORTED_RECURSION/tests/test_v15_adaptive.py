"""v1.5 deterministic differential tests, graph invariants, and fail-closed guards."""
import random
import pytest
from fastapi.testclient import TestClient
from veritas.audit.store import AuditStore
from veritas.api.main import app
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.tensor import Factor
from veritas.research.graph_decomposition import (
    primal_graph,components,small_separator,verify_decomposition,from_elimination_order)
from veritas.research.contraction_planner import (
    original_cnf_model,copy3_model,plan_portfolio,contract_order,
    choose_plan,ContractLimit)
from veritas.research.boundary_dp import boundary_contract
from veritas.research.adaptive_contract import adaptive_count


def test_edge_conditions_exact():
    examples=[(0,[]),(3,[]),(3,[[]]),(2,[[1,-1]]),
              (2,[[1,1,1],[-2]]),(3,[[1],[1],[-1]]),
              (5,[[1,2],[-2,3]]),(2,[[1,-1],[2,-2]]),
              (1,[[1]]*25)]
    for n,clauses in examples:
        cnf=CNF.from_lists(n,clauses)
        ref=exhaustive_count(cnf)
        for use_copy in (False,True):
            got=adaptive_count(cnf,include_copy3=use_copy)
            assert int(got['count'])==ref
            model=copy3_model(cnf) if use_copy else original_cnf_model(cnf)
            val,stats=boundary_contract(model)
            assert val==ref
            for bits in (1,2,4,8):
                rem,_=boundary_contract(model,modulus=1<<bits)
                assert rem==ref%(1<<bits)


def test_differential_random_350():
    rng=random.Random(15052026)
    for i in range(350):
        n=rng.randrange(0,8)
        clauses=([ [rng.choice((-1,1))*rng.randrange(1,n+1)
                    for _ in range(rng.randrange(0,5))]
                    for __ in range(rng.randrange(0,12))] if n else
                 ([[]] if rng.randrange(2) else []))
        cnf=CNF.from_lists(n,clauses)
        expected=exhaustive_count(cnf)
        model=original_cnf_model(cnf)
        for plan in plan_portfolio(model):
            assert plan.treewidth_verified
            got,stats=contract_order(model,plan)
            assert got==expected,(i,cnf.as_dict(),plan)
            assert stats.evaluated_assignments==plan.estimated_assignments
        result=adaptive_count(cnf,precision_bits=rng.randrange(1,10),timeout_s=5)
        assert int(result['count'])==expected%(1<<result['precision_bits'])
        assert result['status']=='COUNT_RESIDUE'
        assert result['planning']['treewidth_verified']


def test_copy3_vs_original_random_100():
    rng=random.Random(12315)
    for i in range(100):
        n=rng.randrange(1,7)
        cnf=CNF.from_lists(n,[[rng.choice((-1,1))*rng.randrange(1,n+1)
                                for j in range(rng.randrange(0,4))]
                                for k in range(rng.randrange(0,12))])
        ref=exhaustive_count(cnf)
        for model in (original_cnf_model(cnf),copy3_model(cnf)):
            for plan in plan_portfolio(model):
                got,_=contract_order(model,plan)
                assert got==ref,(i,model.representation)


def test_decomposition_running_intersection():
    model=original_cnf_model(CNF.from_lists(9,[[1,2],[-2,3],[3,4],
                                             [4,5],[5,6],[-7,8],[8,9]]))
    graph=primal_graph(model.variables,model.factors)
    assert len(components(graph))==2
    for plan in plan_portfolio(model):
        tree=from_elimination_order(graph,plan.order)
        assert verify_decomposition(graph,tree)
        assert tree.width==plan.induced_width
    corrupted=from_elimination_order(graph,plan_portfolio(model)[0].order)
    from dataclasses import replace
    assert not verify_decomposition(graph,replace(corrupted,bags=corrupted.bags[:-1]))


def test_articulation_separator_exact():
    cnf=CNF.from_lists(7,[[1,2],[2,3],[3,4],[4,5],[3,6],[6,7]])
    model=original_cnf_model(cnf)
    cut=small_separator(primal_graph(model.variables,model.factors),max_size=1)
    assert cut is not None and len(cut.components)>1
    count,stats=boundary_contract(model,max_separator=1)
    assert count==exhaustive_count(cnf)
    assert stats.separator_splits>0
    result=adaptive_count(cnf,max_separator=1)
    assert result['engine']=='EXACT_BOUNDARY_DP'


def test_strict_caps_and_no_partial_result():
    cnf=CNF.from_lists(8,[[1,2],[2,3],[3,4],[4,5],[5,6],[6,7],[7,8],[8,1]])
    with pytest.raises(ContractLimit):
        adaptive_count(cnf,max_table_entries=1,max_work_assignments=1,
                       enable_separators=False)
    model=original_cnf_model(cnf)
    plan=plan_portfolio(model)[0]
    with pytest.raises(ContractLimit):
        contract_order(model,plan,max_table_entries=1)
    with pytest.raises(ContractLimit):
        boundary_contract(model,max_calls=1)
    with pytest.raises(ValueError):
        adaptive_count(cnf,precision_bits=0)
    with pytest.raises(ValueError):
        boundary_contract(model,modulus=True)


def test_api_success_modulus_and_unknown(tmp_path):
    app.state.audit=AuditStore(tmp_path/'v15.sqlite3')
    c=TestClient(app)
    inp={'n':5,'clauses':[[1,2],[-2,3],[3,4],[-4,5]],'timeout_s':10}
    r=c.post('/v1/research/adaptive-contract',json=inp)
    assert r.status_code==200,r.text
    data=r.json()
    assert data['status']=='EXACT_COUNT'
    assert data['independent_count_checked'] is True
    assert int(data['count'])==exhaustive_count(CNF.from_lists(inp['n'],inp['clauses']))
    assert data['audit_sha256']
    assert c.get('/v1/audits/'+data['audit_sha256']).status_code==200
    rem=c.post('/v1/research/adaptive-contract',json={**inp,'precision_bits':2})
    assert rem.status_code==200
    assert rem.json()['status']=='COUNT_RESIDUE'
    assert int(rem.json()['count'])==int(data['count'])%4
    bad=c.post('/v1/research/adaptive-contract',json={**inp,'max_table_entries':1,
                                                        'max_work_assignments':1,'max_slices':0,
                                                        'enable_separators':False})
    assert bad.status_code==200 and bad.json()['status']=='UNKNOWN'
    assert 'count' not in bad.json()
    assert c.get('/health').json()['version']=='2.4.0'
    assert any('v1.5' in claim['claim'] for claim in c.get('/v1/paper/audit').json()['claims'])


def test_slicing_bounded_exact():
    cnf=CNF.from_lists(4,[[i,j] for i in range(1,5) for j in range(i+1,5)])
    res=adaptive_count(cnf,max_table_entries=4,max_slices=3,enable_separators=False)
    assert int(res['count'])==exhaustive_count(cnf)
    assert res['execution']['slice_splits']>=1
    assert res['execution']['peak_table_entries']<=4
