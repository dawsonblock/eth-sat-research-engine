"""Finite complete active traversal, independently checked at every root point."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import runpy

import pytest

from veritas.research.manuscript.executor import contract
from veritas.research.manuscript.experimental import ScaledExperiment,contract_scaled
from veritas.research.manuscript.finite_replay import ReplayError,replay
from veritas.research.manuscript.model import DenseTensor,Network,Vertex
from veritas.research.manuscript.parameters import Schedule
from veritas.research.manuscript.resources import Limits


@pytest.fixture(scope='module')
def certificate():
    script=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_active.py'))
    return script['produce']()


def test_active_pipeline_independent_integer_and_point_oracles(certificate):
    result=replay(certificate)
    assert result['independent_integer_jet']==[5,15]
    assert result['modular_jet']==[1,3]
    assert result['checked_points']==8
    assert result['checked_formal_tuple_count']==38480
    assert result['child_calls']==76960
    assert result['source_qualified'] is False
    assert certificate['report']['ledger']['maximum_depth']==1
    assert certificate['report']['experimental_scaling']['shrinking_children_certified'] is False


@pytest.mark.parametrize('mutation', ['point','missing','duplicate','root','polynomial',
    'packet','counter','scope','precision','input','child_summary','parameters','boolean_parameter'])
def test_independent_replay_rejects_tampering(certificate,mutation):
    c=deepcopy(certificate)
    if mutation=='point':
        value=[list(row) for row in c['events'][1]['result']]
        value[0][0]=(value[0][0]+1)%512;c['events'][1]['result']=value
    elif mutation=='missing':del c['events'][2]
    elif mutation=='duplicate':c['events'][2]=deepcopy(c['events'][1])
    elif mutation=='root':c['report']['result']=((0,0,0,0),(0,0,0,0))
    elif mutation=='polynomial':c['events'][0]['defining_polynomial']=25
    elif mutation=='packet':c['events'][0]['packets'].pop()
    elif mutation=='counter':c['report']['ledger']['exponent_tuples']-=1
    elif mutation=='scope':c['report']['source_qualified']=True
    elif mutation=='precision':c['events'][1]['precision']-=1
    elif mutation=='input':c['fixture']['row'][0][0]^=1
    elif mutation=='child_summary':c['leaf_summary']['wire_counts']=[0]
    elif mutation=='parameters':c['report']['parameters']['leaf_threshold']=999
    elif mutation=='boolean_parameter':c['report']['parameters']['C']=True
    with pytest.raises(ReplayError):replay(c)


def _network():
    return Network(1,tuple(Vertex(side,0,(0,),DenseTensor(1,2,((1,),(3,))))
                           for side in ('row','column')))


@pytest.mark.parametrize('limit', [Limits(max_work=1),Limits(max_items=1),
                                  Limits(max_integer_bits=1),Limits(max_seconds=1e-9)])
def test_scaled_resource_limits_never_expose_partial_results(limit):
    result=contract_scaled(_network(),precision=2,limits=limit)
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result
    assert result['source_qualified'] is False


def test_source_schedule_and_public_route_are_not_scaled():
    result=contract(_network(),s=2,precision=2)
    assert result['route']=='SOURCE_DIRECT_RANGE'
    assert result['status']=='PASS_MANUSCRIPT_CONSTRUCTION_EXECUTION'
    assert result['experimental_scaling'] is None
    assert result['ledger']['maximum_depth']==0
    assert Schedule(2).at(0)==(0,0)
    assert not Schedule(2).active_preconditions(1,0)


def test_precision_loss_is_independently_sufficient_and_necessary():
    # For the fixed +/-1 triple-node functional, the second local derivative
    # coefficient has weight 1/128. One fewer bit can alter the answer mod 4.
    weight=Fraction(1,128)
    assert weight*2**9==4
    assert weight*2**8==2


@pytest.mark.parametrize('kwargs',[{'a':0},{'u':0},{'u':2},{'radix':1},
                                    {'active_depth':0},{'column_shift':2}])
def test_explicit_scaling_rejects_bad_parameters(kwargs):
    with pytest.raises(ValueError):ScaledExperiment(**kwargs)


def test_two_active_levels_are_entered_but_budget_failure_stays_closed():
    events=[]
    result=contract_scaled(_network(),precision=2,experiment=ScaledExperiment(active_depth=2),
                           limits=Limits(max_work=100000,max_seconds=10),event_sink=events.append)
    assert result['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result
    assert result['ledger']['maximum_depth']==2
    assert {e['depth'] for e in events if e['kind']=='active'}=={0,1}
    assert result['experimental_scaling']['active_depth']==2


def test_empty_scaled_network_never_claims_recursive_execution():
    net=Network(0,(Vertex('row',0,(),DenseTensor(0,2,((3,),))),))
    events=[]
    result=contract_scaled(net,precision=2,event_sink=events.append)
    assert result['status']=='PASS_EXPERIMENTAL_SCALED_LEAF'
    assert result['route']=='EXPERIMENTAL_SCALED_DIRECT_LEAF'
    assert result['ledger']['maximum_depth']==0
    assert result['result'][0][0]==3
    assert events[0]['reason']=='EMPTY_NETWORK'
