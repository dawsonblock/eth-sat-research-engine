"""Connected recursive experiment: full replay, zero proof and hostile metadata."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import runpy
import pytest
from veritas.research.manuscript.cauchy import Point
from veritas.research.manuscript.children import child,point_contraction
from veritas.research.manuscript.experimental import ScaledExperiment
from veritas.research.manuscript.finite_replay import ReplayError
from veritas.research.manuscript.model import DenseTensor,Network,Vertex,direct
from veritas.research.manuscript.modes import Domain
from veritas.research.manuscript.resources import Budget,Limits
from veritas.research.manuscript.ring import Ring


@pytest.fixture(scope='module')
def implementation():
    return runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_connected_two_level.py'))


@pytest.fixture(scope='module')
def certificate(implementation):return implementation['produce']()


def test_connected_two_level_exact_replay(implementation,certificate):
    result=implementation['replay'](certificate)
    assert result['root_modular_jet']==[1,2]
    assert result['independent_integer_jet']==[25,74]
    assert result['independently_checked_nodes']==3193
    assert result['independently_checked_points']==798
    assert result['independently_checked_leaves']==3136
    assert result['recovered_active_nodes']==57
    assert result['certified_zero_tuples_at_executed_points']==44865517886504
    assert result['node_wire_counts']==[1,2,3]
    assert result['node_precisions']==[2,18,25,43]
    for key in ('source_qualified','executable_refinement_proven','complexity_proven',
                'full_formal_domain_enumerated','shrinking_children_certified'):
        assert result[key] is False


@pytest.mark.parametrize('mutation',['leaf','point','recovered','labels','packets','padding','count','family','support',
                                    'extra_key','missing','duplicate','bool_metadata','root','claim','fixture'])
def test_replay_fails_closed_on_tampering(implementation,certificate,mutation):
    c=deepcopy(certificate)
    if mutation in ('leaf','point','recovered'):
        e=next(e for e in c['events'] if e['kind']==mutation);value=[list(r) for r in e['result']];value[0][0]^=1;e['result']=value
    elif mutation=='labels':c['events'][0]['layout']['labels'][0]['group']^=1
    elif mutation=='packets':c['events'][0]['layout']['packets'].pop()
    elif mutation=='padding':c['events'][0]['layout']['padded_height']+=2
    elif mutation in ('count','family','support'):
        z=next(e for e in c['events'] if e['kind']=='point')['zero_certificate']
        if mutation=='count':z['formal_tuple_count']-=1
        elif mutation=='family':z['families'].pop()
        else:z['eligible_channels'].append(99)
    elif mutation=='extra_key':c['events'][2]['ignored']=123
    elif mutation=='missing':c['events'].pop(5)
    elif mutation=='duplicate':c['events'].insert(5,deepcopy(c['events'][5]))
    elif mutation=='bool_metadata':c['events'][0]['depth']=False
    elif mutation=='root':c['report']['result']=((0,0,0,0),(0,0,0,0))
    elif mutation=='claim':c['report']['source_qualified']=True
    else:c['fixture']['vertices'][0]['values'][0][0]^=1
    with pytest.raises(ReplayError):implementation['replay'](c)


def _cycle_fixture():
    return dict(wires=4,precision=2,ell=2,vertices=[
        dict(side='row',identity=0,ports=[0,1],values=[[1,2],[3,1],[2,0],[1,2]]),
        dict(side='row',identity=1,ports=[2,3],values=[[2,1],[1,3],[0,2],[3,1]]),
        dict(side='column',identity=0,ports=[0,2],values=[[3,2],[2,1],[1,0],[2,3]]),
        dict(side='column',identity=1,ports=[1,3],values=[[1,1],[2,3],[3,2],[1,2]])])


def _network(fixture):
    return Network(fixture['wires'],tuple(Vertex(v['side'],v['identity'],tuple(v['ports']),
        DenseTensor(len(v['ports']),2,tuple(map(tuple,v['values'])))) for v in fixture['vertices']))


@pytest.mark.parametrize('p',[2,3,4])
@pytest.mark.parametrize('t',[-1,1])
def test_cycle_all_omitted_betas_vanish_and_full_point_agrees(implementation,p,t):
    fixture=_cycle_fixture();n=_network(fixture);budget=Budget(Limits(max_work=300000000,max_seconds=120))
    layout=ScaledExperiment().layout(n,budget);point=Point(2,t,(0,1,0,0),p,19,2);ring=Ring(p,19,2,budget)
    domain=Domain(layout,point,budget);optimized=implementation['CertifiedSlotDomain'](n,layout,point,budget)
    kept=set(optimized.tuples());total=ring.zero
    for beta in domain.tuples():
        term=ring.one
        for group in (0,1):term=ring.mul(term,direct(child(n,layout,domain,beta,group,require_bounds=False),ring))
        if beta not in kept:assert term==ring.zero
        total=ring.add(total,term)
    reduced=point_contraction(n,layout,optimized,ring,lambda g,q:direct(g,ring),require_bounds=False)
    graph=implementation['decode_fixture'](fixture)
    description=implementation['layout_data'](n,layout)
    oracle_layout=implementation['verify_layout'](graph,description)
    assert len(oracle_layout[3])==2  # both orientations share an occupied active packet
    assert total==reduced==implementation['point_exact'](graph,oracle_layout,p,t,point.zeta)


@pytest.mark.parametrize('t',[-1,1])
def test_every_retained_cycle_child_entry_matches_independent_oracle(implementation,t):
    fixture=_cycle_fixture();n=_network(fixture);budget=Budget();layout=ScaledExperiment().layout(n,budget)
    point=Point(2,t,(1,1,0,0),3,19,2);ring=Ring(3,19,2,budget)
    domain=implementation['CertifiedSlotDomain'](n,layout,point,budget)
    original=implementation['decode_fixture'](fixture)
    oracle_layout=implementation['verify_layout'](original,implementation['layout_data'](n,layout))
    for beta in domain.tuples():
        selected={(pid,slot) for channel,pid,slot in oracle_layout[3] if beta[channel]}
        for group in (0,1):
            actual=child(n,layout,domain,beta,group,require_bounds=False)
            oracle=implementation['child_oracle'](original,oracle_layout,3,t,point.zeta,selected,group)
            assert actual.wires==oracle['wires']
            assert len(actual.vertices)==len(oracle['vertices'])
            for vertex,expected in zip(actual.vertices,oracle['vertices']):
                assert (vertex.side,vertex.identity,vertex.ports)==(expected['side'],expected['identity'],expected['ports'])
                for index in range(2**len(vertex.ports)):
                    bits=tuple((index>>j)&1 for j in range(len(vertex.ports)))
                    assert vertex.tensor.entry(bits,ring)==expected['table'][index]


def test_replay_does_not_use_producer(implementation,certificate,monkeypatch):
    g=implementation['replay'].__globals__
    def forbidden(*args,**kwargs):raise AssertionError('producer invoked by replay')
    for name in ('recover','point_contraction','direct','CertifiedSlotDomain','DenseTensor','Network','Vertex','Ring','layout_data','ScaledExperiment'):
        monkeypatch.setitem(g,name,forbidden)
    assert implementation['replay'](certificate)['root_modular_jet']==[1,2]


@pytest.mark.parametrize('limits',[Limits(max_work=1),Limits(max_items=1),Limits(max_integer_bits=1)])
def test_execution_resource_caps_return_no_result(implementation,limits):
    c=implementation['produce'](limits=limits)
    assert c['report']['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in c['report']


def test_replay_resource_caps_refuse(implementation,certificate):
    with pytest.raises(ReplayError):implementation['replay'](certificate,max_events=1)
    with pytest.raises(ReplayError):implementation['replay'](certificate,max_seconds=0)


def test_independent_precision_loss(implementation):
    assert implementation['hermite_losses'](1)==(7,7)
    assert implementation['hermite_losses'](2)==(16,16)
    assert implementation['hermite_losses'](3)==(25,25)


@pytest.mark.parametrize('seed',range(3))
def test_random_connected_root_values(implementation,seed):
    import random
    rng=random.Random(seed);fixture=implementation['fixture_default']()
    for vertex in fixture['vertices']:
        vertex['values']=[[rng.randrange(4),rng.randrange(4)] for _ in vertex['values']]
    certificate=implementation['produce'](fixture)
    result=implementation['replay'](certificate)
    expected=direct(_network(fixture),Ring(2,19,2,Budget()))
    assert result['root_modular_jet']==[r[0] for r in expected]


def test_literal_hermite_weights_and_empty_partition(implementation):
    from fractions import Fraction
    assert implementation['hermite_weights'](1)==(Fraction(1,2),Fraction(5,64),Fraction(1,128),
                                                 Fraction(1,2),Fraction(-5,64),Fraction(1,128))
    assert implementation['partition_count'](8,0)==1


def test_disconnected_root_refused(implementation):
    fixture=implementation['fixture_default']()
    fixture['vertices'][0]['ports']=[0]
    fixture['vertices'][0]['values']=fixture['vertices'][0]['values'][:2]
    fixture['vertices'].append(dict(side='row',identity=1,ports=[1],values=[[1,0],[1,0]]))
    with pytest.raises(ValueError,match='disconnected'):implementation['produce'](fixture)
