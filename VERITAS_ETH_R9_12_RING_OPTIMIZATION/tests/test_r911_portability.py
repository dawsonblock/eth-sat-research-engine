"""Policy exhaustion is inconclusive; incomplete numerical checks never pass."""
from dataclasses import replace

import pytest

from veritas.research.independent_r82 import point_mode_oracle as oracle
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic, ReferenceLimit
from veritas.research.parent_child_r98.model import Budget, Refusal
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r910.accounting import AccountedBudget
from veritas.research.parent_child_r910.checker import verify, R910_PRODUCER_SHA256
from veritas.research.parent_child_r910.engine import contract


@pytest.mark.parametrize('work,seconds', [(0,60),(True,60),(1_000_000_001,60),
    (5,0),(5,3601),(5,True),(5,float('nan')),(5,1.5)])
def test_invalid_oracle_policy(work, seconds):
    with pytest.raises(ValueError):
        oracle.OracleLimits(work, seconds)


def test_separate_work_and_time_refusals(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(oracle, 'monotonic', lambda: clock[0])
    meter = oracle._Meter(2, 10, limits=oracle.OracleLimits(2,10), scope='test')
    meter.tick(2)
    with pytest.raises(oracle.OracleBudgetExceeded) as caught:
        meter.tick()
    assert caught.value.status == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert caught.value.resource_failure['resource'] == 'WORK_UNITS'
    assert caught.value.resource_failure['observed'] == 3
    meter = oracle._Meter(20,10,limits=oracle.OracleLimits(20,10))
    clock[0] += 11
    with pytest.raises(oracle.OracleBudgetExceeded) as caught:
        meter.tick(0)
    assert caught.value.resource_failure['resource'] == 'WALL_TIME_US'
    assert caught.value.resource_failure['observed'] == 11_000_000


def test_global_remainder_and_legacy_defaults():
    policy = replace(DEFAULT_SHRINKING_POLICY,max_work=100,max_seconds=90)
    budget = AccountedBudget(policy,oracle.OracleLimits(200,100))
    budget.tick(10)
    meter = oracle.meter_from_budget(budget,'clamp')
    assert meter.maximum == 90 and 0 < meter.timeout_s <= 90
    assert meter.work_limit_scope == meter.time_limit_scope == 'GLOBAL_REMAINDER'
    legacy = oracle.meter_from_budget(Budget(DEFAULT_SHRINKING_POLICY),'legacy')
    assert legacy.maximum == 5_000_000 and legacy.timeout_s == 60
    current = AccountedBudget(policy)
    assert current.oracle_limits.max_seconds == policy.max_seconds
    with pytest.raises(TypeError):
        AccountedBudget(policy,False)


def test_independent_arithmetic_resource_status():
    ar = ReferenceArithmetic(5,7,1,1)
    with pytest.raises(ReferenceLimit) as caught:
        ar.mul(ar.one,ar.one)
    assert caught.value.status == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert caught.value.resource_failure['resource'] == 'WORK_UNITS'


def test_global_oracle_work_refusal_preserves_legacy_exception_contract():
    policy=replace(DEFAULT_SHRINKING_POLICY,max_work=1)
    budget=Budget(policy)
    meter=oracle.meter_from_budget(budget,'legacy global cap')
    with pytest.raises(Refusal) as caught:
        meter.tick(2)
    assert caught.value.status=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert caught.value.resource_failure['limit_scope']=='GLOBAL_REMAINDER'
    assert caught.value.resource_failure['resource']=='WORK_UNITS'
    assert budget.work==2


def test_global_oracle_time_refusal_preserves_legacy_exception_contract(monkeypatch):
    import veritas.research.parent_child_r98.model as model
    clock=[0.0]
    monkeypatch.setattr(model,'monotonic',lambda:clock[0])
    monkeypatch.setattr(oracle,'monotonic',lambda:clock[0])
    budget=Budget(replace(DEFAULT_SHRINKING_POLICY,max_seconds=2))
    meter=oracle.meter_from_budget(budget,'legacy global time cap')
    clock[0]=3.0
    with pytest.raises(Refusal) as caught:
        meter.tick()
    assert caught.value.resource_failure['limit_scope']=='GLOBAL_REMAINDER'
    assert caught.value.resource_failure['resource']=='WALL_TIME_US'
    assert budget.work==1


def test_replay_no_pass_after_required_oracle_refusal(monkeypatch):
    from test_r99_general_packets import fixture
    import veritas.research.parent_child_r910.checker as checker
    parent,_ = fixture()
    events=[]
    report=contract(parent,evidence_sink=events.append)
    assert report['status'].startswith('PASS_')
    def exhausted(*args,**kwargs):
        raise oracle.OracleBudgetExceeded('test time cap',resource_failure={
            'scope':'required leaf','resource':'WALL_TIME_US','limit':1,'observed':2})
    monkeypatch.setattr(checker,'contract_independent',exhausted)
    checked=verify(parent,events,report)
    assert checked['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert checked['resource_failure']['resource']=='WALL_TIME_US'
    assert 'result' not in checked


def test_source_provenance_is_explicit_and_unknown_digest_rejected():
    from test_r99_general_packets import fixture
    parent,_=fixture()
    events=[]
    report=contract(parent,evidence_sink=events.append)
    current=verify(parent,events,report)
    assert current['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
    assert current['producer_source_sha256']==current['checker_source_sha256']
    # Synthetic schema compatibility test, not historical artifact evidence.
    report['implementation_source_sha256']=R910_PRODUCER_SHA256
    legacy=verify(parent,events,report)
    assert legacy['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
    assert legacy['source_compatibility']=='PINNED_R910_SCHEMA'
    assert legacy['producer_source_sha256']!=legacy['checker_source_sha256']
    report['implementation_source_sha256']='f'*64
    invalid=verify(parent,events,report)
    assert invalid['status']=='INVALID_STREAMED_RECURSION' and 'result' not in invalid


def test_global_work_failure_has_limit_and_no_answer():
    from test_r99_general_packets import fixture
    parent,_=fixture()
    result=contract(parent,policy=replace(DEFAULT_SHRINKING_POLICY,max_work=1))
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert result['resource_failure']['resource']=='WORK_UNITS'
    assert result['resource_failure']['limit_scope']=='GLOBAL'
    assert 'result' not in result
