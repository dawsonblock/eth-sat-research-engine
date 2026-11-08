"""Adversarial coverage for the separate certified-zero finite experiment."""
from copy import deepcopy
from pathlib import Path
import runpy
from types import MappingProxyType

import pytest

from veritas.research.manuscript.cauchy import Point
from veritas.research.manuscript.experimental import ScaledExperiment
from veritas.research.manuscript.finite_replay import ReplayError
from veritas.research.manuscript.model import DenseTensor,Network,Vertex
from veritas.research.manuscript.packing import Layout
from veritas.research.manuscript.resources import Budget,Limits


@pytest.fixture(scope='module')
def implementation():
    return runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_certified_two_level.py'))


@pytest.fixture(scope='module')
def certificate(implementation):return implementation['produce']()


def test_two_active_levels_complete_and_replay(implementation,certificate):
    result=implementation['replay'](certificate)
    assert result['maximum_depth']==2
    assert result['independently_checked_nodes']==1057
    assert result['recovered_active_nodes']==33
    assert result['independently_checked_points']==264
    assert result['independently_checked_leaves']==1024
    assert result['root_modular_jet']==[1,3]
    assert result['certified_zero_tuples_at_executed_points']==117806400
    assert result['full_formal_domain_enumerated'] is False
    assert result['source_qualified'] is False


@pytest.mark.parametrize('mutation',['leaf','nested_recovery','point','coverage_count','coverage_class',
                                    'packet','missing_event','root','qualification','enumeration_claim'])
def test_recursive_replay_rejects_tampering(implementation,certificate,mutation):
    c=deepcopy(certificate)
    if mutation in ('leaf','nested_recovery','point'):
        kind={'leaf':'leaf','nested_recovery':'recovered','point':'point'}[mutation]
        event=next(e for e in c['events'] if e['kind']==kind and e['depth']>0)
        value=[list(row) for row in event['result']];value[0][0]^=1;event['result']=value
    elif mutation in ('coverage_count','coverage_class'):
        e=next(e for e in c['events'] if e['kind']=='point')
        if mutation=='coverage_count':e['zero_certificate']['certified_zero_tuple_count']-=1
        else:e['zero_certificate']['families'].pop()
    elif mutation=='packet':c['events'][0]['packets'][1]['slots']=[[1,0]]
    elif mutation=='missing_event':c['events'].pop(5)
    elif mutation=='root':c['report']['result']=((0,0,0,0),(0,0,0,0))
    elif mutation=='qualification':c['report']['source_qualified']=True
    else:c['report']['full_formal_domain_enumerated']=True
    with pytest.raises(ReplayError):implementation['replay'](c)


def _network():
    return Network(1,tuple(Vertex(side,0,(0,),DenseTensor(1,2,((1,2),(3,1))))
                           for side in ('row','column')))


def test_uncertified_geometry_is_refused(implementation):
    n=_network();b=Budget();layout=ScaledExperiment(column_shift=0).layout(n,b)
    with pytest.raises(implementation['ZeroCertificateError']):
        implementation['CertifiedOneWireDomain'](n,layout,Point(2,-1,(0,0,0,0),9,19,2),b)


def test_missing_label_coverage_is_refused(implementation):
    n=_network();b=Budget();layout=ScaledExperiment().layout(n,b)
    bad=Layout(layout.a,layout.r,MappingProxyType({}),layout.columns,layout.packets,layout.padded_height,layout.variance_scaled)
    with pytest.raises(implementation['ZeroCertificateError']):
        implementation['CertifiedOneWireDomain'](n,bad,Point(2,-1,(0,0,0,0),9,19,2),b)


@pytest.mark.parametrize('limits',[Limits(max_work=1),Limits(max_items=1),Limits(max_integer_bits=1)])
def test_resource_refusal_has_no_partial_answer(implementation,limits):
    report,_=implementation['run'](_network(),limits=limits)
    assert report['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in report


def test_unsupported_topology_has_no_result(implementation):
    report,_=implementation['run'](Network(0,()))
    assert report['status']=='REFUSED_ZERO_CERTIFICATE'
    assert 'result' not in report


def test_replay_does_not_call_production_components(implementation,certificate,monkeypatch):
    g=implementation['replay'].__globals__
    def forbidden(*args,**kwargs):raise AssertionError('production dependency invoked by replay')
    for name in ('recover','point_contraction','direct','CertifiedOneWireDomain','DenseTensor','Network','Vertex','Ring'):
        monkeypatch.setitem(g,name,forbidden)
    assert implementation['replay'](certificate)['root_modular_jet']==[1,3]


def test_independent_colored_partition_counts(implementation):
    assert implementation['_formal_count'](9)==4810
    assert implementation['_formal_count'](16)==460033


@pytest.mark.parametrize('p',[2,3,4,5])
@pytest.mark.parametrize('t',[-1,1])
def test_each_omitted_beta_is_zero_against_unpruned_children(implementation,p,t):
    from veritas.research.manuscript.children import child
    from veritas.research.manuscript.modes import Domain
    from veritas.research.manuscript.model import direct
    from veritas.research.manuscript.ring import Ring
    n=_network();budget=Budget(Limits(max_work=20000000,max_seconds=30))
    layout=ScaledExperiment().layout(n,budget);point=Point(2,t,(0,1,0,0),p,19,2)
    domain=Domain(layout,point,budget);ring=Ring(p,19,2,budget)
    retained={(0,)*domain.size,(1,)+(0,)*(domain.size-1)}
    for beta in domain.tuples():
        if beta in retained:continue
        term=ring.one
        for group in (0,1):
            graph=child(n,layout,domain,beta,group,require_bounds=False)
            term=ring.mul(term,direct(graph,ring))
        assert term==ring.zero


@pytest.mark.parametrize('seed',range(8))
def test_two_level_random_input_tables_independent_replay(implementation,seed):
    import random
    rng=random.Random(seed)
    fixture=dict(precision=2,ell=2,
                 row=[[rng.randrange(4) for _ in range(2)] for _ in range(2)],
                 column=[[rng.randrange(4) for _ in range(2)] for _ in range(2)])
    if seed%2:
        fixture['row_scalar']=[rng.randrange(4) for _ in range(2)]
        fixture['column_scalar']=[rng.randrange(4) for _ in range(2)]
    certificate=implementation['produce'](fixture)
    result=implementation['replay'](certificate)
    expected=[0,0]
    for bit in (0,1):
        a,b=fixture['row'][bit];c,d=fixture['column'][bit]
        expected[0]+=a*c;expected[1]+=a*d+b*c
    for side in ('row','column'):
        if side+'_scalar' in fixture:
            c,d=fixture[side+'_scalar'];a,b=expected
            expected=[a*c,a*d+b*c]
    assert result['independent_integer_jet']==expected
    assert result['root_modular_jet']==[v%4 for v in expected]


@pytest.mark.parametrize('kind',['active','leaf','point','recovered'])
def test_extra_event_fields_refused(implementation,certificate,kind):
    c=deepcopy(certificate);next(e for e in c['events'] if e['kind']==kind)['unchecked']='injected'
    with pytest.raises(ReplayError):implementation['replay'](c)


def test_label_transcript_tampering_refused(implementation,certificate):
    c=deepcopy(certificate);c['events'][0]['labels'][0]['word']=[1]
    with pytest.raises(ReplayError):implementation['replay'](c)
