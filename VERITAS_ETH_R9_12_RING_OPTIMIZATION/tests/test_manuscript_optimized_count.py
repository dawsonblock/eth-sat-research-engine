"""Public exact-optimized counting API, independent traces and legacy isolation."""
from pathlib import Path
import runpy
import pytest
from veritas.research.manuscript.cnf import Formula,count,direct_count
from veritas.research.manuscript.optimizations import count_optimized,common_zeros_factored,distinct_parity_rows,greedy_rows_distinct
from veritas.research.manuscript.resources import Budget,Limits
from veritas.research.manuscript.hashes import greedy_rows


@pytest.mark.parametrize('clauses',[(),((),),((1,),),((1,),(-1,)),((1,2),(3,-4)),((1,-2),),((-1,-2),(1,3)),((1,2),(1,2))])
def test_public_general_route_exact_with_unused_variables(clauses):
    f=Formula(20,clauses);result=count_optimized(f)
    small=Formula(4,clauses)
    expected=direct_count(small,Budget()) << 16
    assert result['status']=='PASS_EXACT_COUNT' and result['count']==expected
    assert result['optimization_policy']=='DISTINCT_PARITY_ROWS_AND_UNUSED_VARIABLE_FACTOR'
    assert result['source_qualified'] is False and result['complexity_proven'] is False
    assert result['executable_refinement_proven'] is False


def test_original_ordered_list_reference_remains_unchanged():
    f=Formula(20,((1,2),(3,-4)))
    before=count(f);improved=count_optimized(f);after=count(f)
    assert before['status']==after['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert before['reason']==after['reason']=='greedy candidate enumeration exceeds allowance'
    assert improved['count']==589824


def test_public_trace_replays_independently():
    driver=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_hash_quotient.py'))
    certificate=driver['produce'](integrated=True)
    result=driver['replay'](certificate)
    assert result['exact_count']==589824
    assert result['independently_checked_candidate_scores']==240


@pytest.mark.parametrize('P',[0,1,2,3])
def test_production_greedy_choices_equal_original_ordered_lists(P):
    clauses=((1,2),(-1,3))
    expected=greedy_rows(3,clauses,(),P,limits=Limits(max_work=10000000))
    actual=greedy_rows_distinct(3,clauses,(),P)
    assert actual==expected


@pytest.mark.parametrize('limits',[Limits(max_work=1),Limits(max_items=1),Limits(max_integer_bits=1)])
def test_optimized_resource_refusal_has_no_count(limits):
    result=count_optimized(Formula(20,((1,2),(3,-4))),limits=limits)
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'count' not in result


@pytest.mark.parametrize('system',[[],[[]],[[frozenset()]],[[frozenset(),frozenset()]],[[frozenset({0})]]])
def test_production_factor_edge_cases(system):
    from veritas.research.manuscript.sparse_query import common_zeros
    expected=common_zeros(4,system)['count'] << 16
    assert common_zeros_factored(20,system)['count']==expected


def test_cli_optimized_mode(capsys):
    import json
    from veritas.research.manuscript.cli import main
    main(['count-optimized','--n','20','--clauses-json','[[1,2],[3,-4]]'])
    result=json.loads(capsys.readouterr().out)
    assert result['count']==589824
    assert result['optimization_policy']=='DISTINCT_PARITY_ROWS_AND_UNUSED_VARIABLE_FACTOR'


def test_tiny_api_does_not_claim_recursive_work():
    result=count_optimized(Formula(2,((1,2),)))
    assert result['count']==3 and result['route']=='BOUNDED_EXHAUSTIVE_SEARCH'
    assert result['ledger']['calls']==0


def test_zero_fixed_point_solves_five_clauses_under_default_cap():
    result=count_optimized(Formula(20,((1,2),(3,-4),(-5,6),(7,8),(9,-10))))
    assert result['status']=='PASS_EXACT_COUNT' and result['count']==248832
    assert result['ledger']['work_units']<10000000


def test_zero_fixed_point_stops_queries_but_preserves_rows_and_trace(monkeypatch):
    from veritas.research.manuscript import optimizations
    original=optimizations.common_zeros_factored;calls=[];events=[]
    def query(*args,**kwargs):calls.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(optimizations,'common_zeros_factored',query)
    rows=greedy_rows_distinct(1,((1,),),(1,),1,hash_event_sink=events.append)
    rounds=[e for e in events if e['kind']=='hash_round']
    assert rows==(1,0,0,0) and len(calls)==2
    assert len(rounds)==3 and [e['index'] for e in rounds]==[0,1,2]
    assert all(e['scores']==[[0,1],[1,1]] for e in rounds)


def test_reused_trace_snapshots_survive_callback_mutation():
    events=[]
    def trace(event):
        events.append(event)
        if event['kind']=='hash_round' and event['index']==0:event['scores'][0][1]=999
    assert greedy_rows_distinct(1,((1,),),(1,),1,hash_event_sink=trace)==(1,0,0,0)
    rounds=[e for e in events if e['kind']=='hash_round']
    assert rounds[1]['scores']==rounds[2]['scores']==[[0,1],[1,1]]
    rounds[1]['scores'][0][1]=555
    assert rounds[2]['scores']==[[0,1],[1,1]]


def test_zero_semantic_guard_fails_loud(monkeypatch):
    from veritas.research.manuscript import hashes
    original=hashes.system_equations
    def changed(rows,violation):
        if type(rows) is tuple and rows==(0,):return ((frozenset(),),)
        return original(rows,violation)
    monkeypatch.setattr(hashes,'system_equations',changed)
    with pytest.raises(ArithmeticError,match='zero parity row'):
        greedy_rows_distinct(1,((1,),),(1,),1)


def test_zero_reuse_tail_remains_budgeted():
    from veritas.research.manuscript.resources import ResourceLimit
    baseline=Budget();greedy_rows_distinct(1,((1,),),(1,),1,budget=baseline,hash_event_sink=lambda e:None)
    limited=Budget(Limits(max_work=baseline.work-1));events=[]
    with pytest.raises(ResourceLimit):
        greedy_rows_distinct(1,((1,),),(1,),1,budget=limited,hash_event_sink=events.append)
    assert len([e for e in events if e['kind']=='hash_round'])==2
