"""Finite degree admission, whole-branch fallback and declared-variable counts."""
from itertools import product
from math import comb
import pytest
from veritas.research.manuscript import sparse_query as sq
from veritas.research.manuscript.sparse import normalize_system,idempotent_coefficients
from veritas.research.manuscript.resources import Budget,Limits,ResourceLimit


def exact_max(sizes,K):
    return max((sum((comb(N,d)-1).bit_length() for N,d in zip(sizes,ds))
                for ds in product(*(range(N+1) for N in sizes)) if sum(ds)<=K),default=0)


@pytest.mark.parametrize('K',range(11))
def test_admission_knapsack_matches_all_compositions(K):
    for sizes in product(range(5),repeat=3):
        assert sq._maximum_indexed_degree(sizes,K,Budget())==exact_max(sizes,K)


def test_tight_bound_avoids_loose_pair_maximum_false_positive():
    # Each pair can separately use one incidence, but only one can do so.
    assert sq._maximum_indexed_degree((2,2),1,Budget())==1
    assert sum((comb(2,1)-1).bit_length() for _ in range(2))==2


def wide():return normalize_system(20,[[[v] for v in range(20)] for _ in range(9)])


def test_actual_valid_array_exceeds_finite_source_admission():
    budget=Budget();system=wide();ell=21
    admission=sq._degree_admission(system,sq._blocks(range(9),3),sq._blocks(range(20),3),1,ell,60,budget)
    assert admission==dict(admitted=False,degree=57,limit=40,side='column',group=0,degree_cap=49)
    array=[[0,0,0],[0,0,0],[10,10,10]]
    network=sq.build_network(20,system,array,1<<21,ell,idempotent_coefficients(ell,budget),3,list(range(20)),budget)
    assert sum(map(sum,array))<=49 and network.wires==network.maximum_degree==54


def truth_count(system,free):
    return sum(all(sum(all(bits[free.index(v)] for v in m) for m in eq)%2==0 for eq in system)
               for bits in product((0,1),repeat=len(free)))


@pytest.mark.parametrize('free',[(3,7,18),(18,3,7),(),(4,)])
@pytest.mark.parametrize('which',('empty','constant_one','linear','product'))
def test_original_branch_enumeration_preserves_all_free_coordinates(free,which):
    if which=='empty':system=((),)
    elif which=='constant_one':system=((frozenset(),),)
    elif not free:system=()
    elif which=='linear':system=(tuple(frozenset((v,)) for v in free[:2]),)
    else:system=((frozenset(free[:2]),),)
    assert sq._exhaustive_free_zeros(system,free,Budget())==truth_count(system,free)


def test_branch_preflight_replaces_entire_tensor_sum_with_exact_count(monkeypatch):
    # Component test of noncontiguous substituted indices and an absent free
    # variable. It does not assert this particular free set is a heavy branch.
    system=tuple((frozenset((3,7)),) for _ in range(270));free=(3,7,18);budget=Budget()
    def forbidden(*args,**kwargs):raise RuntimeError('tensor work began before fallback')
    monkeypatch.setattr(sq,'_enumerate_arrays',forbidden);monkeypatch.setattr(sq,'contract',forbidden)
    value,admission=sq._branch_count(system,20,free,1<<21,21,(),60,budget,None)
    assert value==6 and admission['admitted'] is False and budget.calls==0


def affine_oracle(system,free,budget):
    # Independent GF(2) elimination, used only as a fast dispatcher test.
    mapping={v:i for i,v in enumerate(free)};basis={}
    for eq in system:
        row=constant=0
        for monomial in eq:
            if len(monomial)>1:raise RuntimeError('affine test scope')
            if not monomial:constant^=1
            else:row^=1<<mapping[next(iter(monomial))]
        while row:
            pivot=row.bit_length()-1
            if pivot not in basis:basis[pivot]=(row,constant);break
            other,c=basis[pivot];row^=other;constant^=c
        else:
            if constant:return 0
    return 1<<(len(free)-len(basis))


@pytest.mark.parametrize('heavy', [False,True])
def test_public_dispatch_reports_fallback_without_heavy_or_unused_double_factor(monkeypatch,heavy):
    equations=[[[v] for v in range(20)] for _ in range(9)]
    if heavy:equations += [[[0]]]*100
    calls=[]
    def independent(system,free,budget):
        calls.append(tuple(free));return affine_oracle(system,free,budget)
    monkeypatch.setattr(sq,'_exhaustive_free_zeros',independent)
    result=sq.common_zeros(20,equations)
    assert result['status']=='PASS_EXACT_COUNT' and result['count']==1<<(18 if heavy else 19)
    assert result['route']=='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT'
    assert result['degree_admission_fallback_branches']==1
    assert calls==[tuple(range(1 if heavy else 0,20))]
    assert result['ledger']['calls']==0


def test_preflight_and_branch_limits_fail_closed_without_reset():
    budget=Budget(Limits(max_work=1000));budget.tick(990)
    result=sq.common_zeros(20,wide(),budget=budget)
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in result
    assert result['ledger']['work_units']==budget.work>990
    with pytest.raises(ResourceLimit):sq._maximum_indexed_degree((20,20),20,Budget(Limits(max_items=2)))
    with pytest.raises(ResourceLimit):sq._maximum_indexed_degree((20,20),20,Budget(Limits(max_integer_bits=1)))
    with pytest.raises(ResourceLimit):sq._exhaustive_free_zeros((),tuple(range(20)),Budget(Limits(max_work=2)))


def test_fixed_coordinate_left_in_branch_is_not_ignored():
    with pytest.raises(ArithmeticError,match='fixed variable'):
        sq._exhaustive_free_zeros(((frozenset((1,)),),),(3,),Budget())
    with pytest.raises(ValueError):sq._exhaustive_free_zeros((),(3,3),Budget())
    with pytest.raises(ValueError):sq._maximum_indexed_degree((True,),1,Budget())


def test_pure_tensor_route_and_generic_errors_remain_distinct(monkeypatch):
    result=sq.common_zeros(20,[[[0],[1]],[[1],[2]]],limits=Limits(max_work=50000000))
    assert result['route']=='SPARSE_POLY_CONTRACT' and result['count']==1<<18
    assert 'degree_admission_fallback_branches' not in result
    def invalid(*args,**kwargs):raise ValueError('unrelated construction defect')
    monkeypatch.setattr(sq,'contract',invalid)
    with pytest.raises(ValueError,match='unrelated'):sq.common_zeros(20,[[[0]]])


def test_scaled_api_does_not_adopt_sparse_branch_fallback(monkeypatch):
    from veritas.research.manuscript.experimental import ScaledExperiment,count_scaled_cnf
    from veritas.research.manuscript.cnf import Formula
    def forbidden(*args,**kwargs):raise RuntimeError('scaled count used direct sparse fallback')
    monkeypatch.setattr(sq,'_exhaustive_free_zeros',forbidden)
    receipt=count_scaled_cnf(Formula(1,((1,),)),experiment=ScaledExperiment(certified_support=True))
    assert receipt['status']=='PASS_EXACT_COUNT' and receipt['count']==1
    assert receipt['route']=='EXPERIMENTAL_SCALED_CNF'


def test_admission_rejects_consumable_iterator_instead_of_losing_sizes():
    with pytest.raises(ValueError,match='sequence'):
        sq._maximum_indexed_degree(iter((2,2)),1,Budget())


def test_unused_factor_receipt_preserves_inner_degree_exception(monkeypatch):
    from veritas.research.manuscript import optimizations
    def completed(n,system,**kwargs):
        assert n==20
        return dict(status='PASS_EXACT_COUNT',count=1<<19,
            route='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT',
            degree_admission_fallback_branches=1,largest_fallback_degree=57,
            source_degree_limit=40,fallback_policy='EXACT_DEGREE_PREFLIGHT_AND_ORIGINAL_FREE_VARIABLE_COUNT')
    monkeypatch.setattr(optimizations,'common_zeros',completed)
    result=optimizations.common_zeros_factored(21,wide())
    assert result['count']==1<<20 and result['unused_variables']==1
    assert result['inner_route']=='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT'
    assert result['degree_admission_fallback_branches']==1
    assert result['source_degree_limit']==40


@pytest.fixture(scope='module')
def validator():
    import importlib.util
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_degree_exception.py'
    spec=importlib.util.spec_from_file_location('degree_exception_validator',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


@pytest.fixture(scope='module')
def checker_fixture():
    # Synthetic numerical checker fixture with explicitly unrecorded producer
    # provenance. Actual source/wheel runs are generated by the validator.
    return dict(schema='VERITAS_SPARSE_DEGREE_EXCEPTION_V1',producer_source_sha256=None,
        limits=dict(max_work=500000000,max_seconds=300,max_items=2000000,max_integer_bits=1000000),
        cases=[dict(name='parity',n=20,equations=[[[v] for v in range(20)] for _ in range(9)],
            report=dict(status='PASS_EXACT_COUNT',count=1<<19,route='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT',
                source_qualified=False,complexity_proven=False,degree_admission_fallback_branches=1,
                largest_fallback_degree=57,source_degree_limit=40,
                fallback_policy='EXACT_DEGREE_PREFLIGHT_AND_ORIGINAL_FREE_VARIABLE_COUNT',
                ledger=dict(work_units=210765164,elapsed_seconds=57,calls=0,interpolation_points=0,
                            exponent_tuples=0,maximum_depth=0,bit_operations=None,hard_memory_limit_enforced=False)))])


def test_independent_degree_replay_forbids_producer_calls(validator,checker_fixture,monkeypatch):
    def forbidden(*args,**kwargs):raise RuntimeError('producer dependency in checker')
    for name in ('common_zeros','_maximum_indexed_degree','_degree_admission','_exhaustive_free_zeros',
                 '_exhaustive_zeros','_branch_count','_enumerate_arrays','build_network','contract'):
        monkeypatch.setattr(sq,name,forbidden)
    monkeypatch.setattr(validator,'common_zeros',forbidden);monkeypatch.setattr(validator,'produce',forbidden)
    result=validator.replay(checker_fixture)
    assert result['status']=='PASS_INDEPENDENT_SPARSE_DEGREE_EXCEPTION_REPLAY'
    assert result['cases'][0]['count']==1<<19 and result['cases'][0]['checked_degree']==57
    assert result['producer_source_identity']=='UNRECORDED_DEVELOPMENT'


@pytest.mark.parametrize('fault',('count','degree','fallbacks','route','qualification','incomplete','variable','resource','ledger','unknown_claim'))
def test_degree_replay_tamper_and_resource_refusals(validator,checker_fixture,fault):
    from copy import deepcopy
    c=deepcopy(checker_fixture);case=c['cases'][0];r=case['report']
    if fault=='count':r['count']-=1
    elif fault=='degree':r['largest_fallback_degree']+=1
    elif fault=='fallbacks':r['degree_admission_fallback_branches']+=1
    elif fault=='route':r['route']='SPARSE_POLY_CONTRACT'
    elif fault=='qualification':r['source_qualified']=True
    elif fault=='incomplete':r['status']='INCONCLUSIVE_RESOURCE_LIMIT';r.pop('count')
    elif fault=='variable':case['equations'][0][0][0]=20
    elif fault=='ledger':r['ledger']['calls']=1
    elif fault=='unknown_claim':r['executable_refinement_proven']=True
    with pytest.raises(validator.ReplayError):
        validator.replay(c,max_work=1 if fault=='resource' else 100000000)


def test_exhausted_direct_branch_does_not_return_partial_count():
    result=sq.common_zeros(20,wide(),limits=Limits(max_work=5000))
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in result
    assert result['ledger']['calls']==0 and result['ledger']['work_units']>5000


def test_later_heavy_branch_exhaustion_discards_earlier_total(monkeypatch):
    calls=[]
    def branch(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise ResourceLimit('later branch exhausted')
        return 1<<18,None
    monkeypatch.setattr(sq,'_branch_count',branch)
    # Keep a nonzero free-variable constraint after substituting the two
    # heavy variables; zero equations now correctly bypass contraction.
    result=sq.common_zeros(20,[[[0],[1]]]*100+[[[2]]])
    assert len(calls)==2 and result['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in result


@pytest.mark.parametrize('optimized',(False,True))
def test_sparse_hash_wrapper_keeps_final_query_diagnostics(monkeypatch,optimized):
    from veritas.research.manuscript import hashes,optimizations
    monkeypatch.setattr(hashes,'sparse_check_parameters',lambda *args:(1,1,1))
    monkeypatch.setattr(hashes,'sparse_checks',lambda *args,**kwargs:())
    diagnostics=dict(degree_admission_fallback_branches=1,largest_fallback_degree=57,
                     source_degree_limit=40,fallback_policy='EXACT_DEGREE_PREFLIGHT_AND_ORIGINAL_FREE_VARIABLE_COUNT')
    def query(*args,**kwargs):
        return dict(status='PASS_EXACT_COUNT',count=524288,ledger=Budget().report(),
            route='EXACT_UNUSED_VARIABLE_FACTOR' if optimized else 'SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT',
            inner_route='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT',**diagnostics)
    if optimized:
        monkeypatch.setattr(optimizations,'greedy_rows_distinct',lambda *args,**kwargs:())
        monkeypatch.setattr(optimizations,'common_zeros_factored',query)
        result=optimizations.count_sparse_formula_optimized(20,((1,2),),1,2)
    else:
        monkeypatch.setattr(hashes,'greedy_rows',lambda *args,**kwargs:())
        monkeypatch.setattr(hashes,'common_zeros',query)
        result=hashes.count_sparse_formula(20,((1,2),),1,2)
    assert result['final_query_degree_fallback']==dict(route='SPARSE_POLY_CONTRACT_WITH_DIRECT_BRANCH_COUNT',**diagnostics)


def test_general_dispatcher_labels_final_query_summary_scope():
    from veritas.research.manuscript.cnf import Formula,_count
    def counter(*args,**kwargs):
        return dict(status='PASS_EXACT_COUNT',count=3*(1<<18),
                    final_query_degree_fallback=dict(degree_admission_fallback_branches=2))
    result=_count(Formula(20,((1,2),)),sparse_counter=counter)
    assert result['count']==3*(1<<18)
    assert result['final_query_degree_fallback_leaves']==1 and result['final_query_degree_fallback_branches']==2
    assert result['degree_fallback_summary_scope']=='FINAL_QUERY_PER_SPARSE_LEAF_EXCLUDES_GREEDY_SCORING_QUERIES'


def test_v2_replay_discards_zero_equations_without_reinterpreting_v1(validator,checker_fixture):
    from copy import deepcopy
    certificate=deepcopy(checker_fixture)
    certificate['schema']='VERITAS_SPARSE_DEGREE_EXCEPTION_V2'
    certificate['cases'][0]['equations'].insert(0, [])
    result=validator.replay(certificate)
    assert result['cases'][0]['checked_degree']==57
    # Under the historical V1 grouping, ten equations split 4/3/3 and
    # the empty first equation leaves 3/3/3 nonempty equations: same here.
    # Put the zero last instead, so the first group retains four equations.
    certificate['cases'][0]['equations'].append(certificate['cases'][0]['equations'].pop(0))
    assert validator.replay(certificate)['cases'][0]['checked_degree']==57
    certificate['schema']='VERITAS_SPARSE_DEGREE_EXCEPTION_V1'
    with pytest.raises(validator.ReplayError,match='degree diagnosis mismatch'):
        validator.replay(certificate)
