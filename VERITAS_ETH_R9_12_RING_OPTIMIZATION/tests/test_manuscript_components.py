"""Independent original-input oracles for exact component optimizations."""
import itertools
import random
import pytest
from veritas.research.manuscript.cnf import Formula
from veritas.research.manuscript.optimizations import count_optimized,common_zeros_factored
from veritas.research.manuscript.resources import Limits


def cnf_oracle(n,clauses):
    return sum(all(any(bits[abs(v)-1] == (v>0) for v in c) for c in clauses)
               for bits in itertools.product((False,True),repeat=n))


def equation_oracle(n,equations):
    return sum(all(sum(all(bits[v] for v in m) for m in eq)%2==0 for eq in equations)
               for bits in itertools.product((False,True),repeat=n))


def test_random_original_cnf_oracle():
    rng=random.Random(91207)
    for case in range(250):
        n=rng.randrange(1,10);clauses=[]
        for group in (list(range(1,n//2+1)),list(range(n//2+1,n+1))):
            if group:
                for _ in range(rng.randrange(7)):
                    clauses.append(tuple(rng.choice(group)*rng.choice((-1,1)) for _ in range(rng.randrange(4))))
        result=count_optimized(Formula(n,tuple(clauses)))
        assert result['status']=='PASS_EXACT_COUNT',(case,result)
        assert result['count']==cnf_oracle(n,clauses),(case,clauses,result)


def test_random_original_equation_oracle():
    rng=random.Random(91208)
    for case in range(250):
        n=rng.randrange(2,10);equations=[]
        for group in (list(range(n//2)),list(range(n//2,n))):
            for _ in range(rng.randrange(5)):
                equations.append([tuple(rng.choice(group) for _ in range(rng.randrange(4))) for _ in range(rng.randrange(5))])
        result=common_zeros_factored(n,equations)
        assert result['status']=='PASS_EXACT_COUNT',(case,result)
        assert result['count']==equation_oracle(n,equations),(case,equations,result)


def test_repeated_cnf_components_and_unused_variables():
    result=count_optimized(Formula(100,tuple((v,v+1) for v in range(1,41,2))))
    assert result['count']==3**20 * 2**60
    assert result['reused_components']==19
    assert result['ledger']['calls']==0
    assert result['route']=='EXACT_INDEPENDENT_COMPONENT_PRODUCT'


def test_repeated_equation_components_and_unused_variables():
    # x*y = 0 on ten disjoint pairs, plus a zero equation.
    equations=[[(v,v+1)] for v in range(0,20,2)]+[[]]
    result=common_zeros_factored(40,equations)
    assert result['count']==3**10 * 2**20
    assert result['reused_components']==9


@pytest.mark.parametrize('equations',[[[()]],[[()],[(0,)],[(2,)]],[[],[(0,)],[(2,)]], [[(0,),(0,)],[(2,)]]])
def test_constants_and_cancelled_equations(equations):
    assert common_zeros_factored(4,equations)['count']==equation_oracle(4,equations)


@pytest.mark.parametrize('limits',[Limits(max_work=1),Limits(max_items=1),Limits(max_integer_bits=1),Limits(max_seconds=1e-12)])
def test_shared_limits_fail_without_partial_count(limits):
    for result in (count_optimized(Formula(20,((1,2),(3,4))),limits=limits),
                   common_zeros_factored(20,[[(0,1)],[(2,3)]],limits=limits)):
        assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
        assert 'count' not in result


def test_late_component_failure_has_no_partial_product(monkeypatch):
    from veritas.research.manuscript import cnf,optimizations
    original=cnf._count;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:return dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason='injected late failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(cnf,'_count',fail_second)
    result=count_optimized(Formula(4,((1,2),(-3,-4))))
    assert len(calls)==2 and 'count' not in result
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT'


def test_late_equation_failure_has_no_partial_product(monkeypatch):
    from veritas.research.manuscript import optimizations
    original=optimizations.common_zeros;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:return dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason='injected late failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(optimizations,'common_zeros',fail_second)
    result=common_zeros_factored(4,[[(0,1)],[(),(2,3)]])
    assert len(calls)==2 and 'count' not in result
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT'


def test_transitive_sharing_is_not_split():
    clauses=((1,2),(2,3),(3,4))
    result=count_optimized(Formula(4,clauses))
    assert result['route']=='BOUNDED_EXHAUSTIVE_SEARCH'
    assert result['count']==cnf_oracle(4,clauses)


def test_traced_cnf_retains_unsplit_trace():
    events=[]
    result=count_optimized(Formula(20,((1,2),(3,-4))),hash_event_sink=events.append)
    assert result['count']==589824
    assert sum(e['kind']=='hash_round' for e in events)==60
    assert result['route']!='EXACT_INDEPENDENT_COMPONENT_PRODUCT'
