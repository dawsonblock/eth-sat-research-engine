"""Distinct-row quotient preserves ordered-list minima and exact counts."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import random
import runpy
import pytest
from veritas.research.manuscript import hashes
from veritas.research.manuscript.resources import Budget,Limits,ResourceLimit
from veritas.research.manuscript.sparse_query import common_zeros


@pytest.fixture(scope='module')
def implementation():
    return runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_hash_quotient.py'))


@pytest.mark.parametrize('m',range(1,5))
@pytest.mark.parametrize('P',range(5))
def test_quotient_matches_first_occurrence_and_minimizer(implementation,m,P):
    seen=[];all_rows=[]
    for gamma in product(range(2*m),repeat=P):
        row=0
        for code in gamma:
            if code%2:row^=1<<(code//2)
        all_rows.append(row)
        if row not in seen:seen.append(row)
    actual=list(implementation['distinct_rows'](m,P,Budget()))
    assert actual==seen
    rng=random.Random(100*m+P)
    for _ in range(5):
        score={row:rng.randrange(3) for row in seen}
        assert min(all_rows,key=lambda row:score[row])==min(actual,key=lambda row:score[row])


def test_distinct_domain_resource_cap(implementation):
    with pytest.raises(ResourceLimit):list(implementation['distinct_rows'](100,20000,Budget(Limits(max_work=1000))))


@pytest.mark.parametrize('system',[[],[[]],[[frozenset()]],[[frozenset(),frozenset()]],[[frozenset({1})]],
    [[frozenset(),frozenset({0}),frozenset({3}),frozenset({0,3})]],
    [[frozenset({2})],[frozenset({2}),frozenset({5})]]])
def test_unused_variable_factor_matches_direct_original_query(implementation,system):
    expected=common_zeros(6,system)
    actual=implementation['factor_query'](common_zeros,6,system)
    assert actual['count']==expected['count']


def test_large_declared_support_factor(implementation):
    actual=implementation['factor_query'](common_zeros,20,[[frozenset({0})]])
    assert actual['count']==2**19
    assert actual['active_variables']==1 and actual['unused_variables']==19


@pytest.fixture(scope='module')
def certificate(implementation):return implementation['produce']()


def test_general_twenty_variable_case_now_completes_experiment(implementation,certificate):
    result=implementation['replay'](certificate)
    assert result['exact_count']==589824
    assert result['independently_checked_candidate_scores']==240
    assert result['distinct_candidates_per_round']==4
    assert result['original_ordered_list_length']==21135680000
    assert certificate['report']['route']=='SPARSIFY_SPARSE_QUERY'
    assert certificate['report']['ledger']['calls']==0  # no claim of active contraction


@pytest.mark.parametrize('mutation',['score','tie','missing','P','initial','formula','count','claim','extra'])
def test_hash_certificate_tampering_refused(implementation,certificate,mutation):
    c=deepcopy(certificate);event=c['greedy_events'][0]
    if mutation=='score':event['rounds'][0]['scores'][0][1]-=1
    elif mutation=='tie':event['rounds'][2]['selected']=1
    elif mutation=='missing':event['rounds'].pop()
    elif mutation=='P':event['P']-=1
    elif mutation=='initial':event['initial_rows']=[1,0]
    elif mutation=='formula':c['formula']['clauses'][0]=[1]
    elif mutation=='count':c['report']['count']-=1
    elif mutation=='claim':c['complexity_proven']=True
    else:c['unchecked']=True
    with pytest.raises(implementation['ReplayError']):implementation['replay'](c)


def test_temporary_substitution_restores_production_functions(implementation):
    before=hashes.greedy_rows,hashes.common_zeros
    implementation['produce'](limits=Limits(max_work=1))
    assert (hashes.greedy_rows,hashes.common_zeros)==before


def test_replay_does_not_call_production_counting(implementation,certificate,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('producer invoked')
    g=implementation['replay'].__globals__
    for name in ('count','factor_query','distinct_rows','normalize_system'):
        monkeypatch.setitem(g,name,forbidden)
    assert implementation['replay'](certificate)['exact_count']==589824
