from dataclasses import replace
from math import prod
import pytest

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.parent_child_r98.model import (Budget, Policy, PacketLayout, ModeSet, ExponentTuple,
                                                    Refusal, canonical, from_described)
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.packing import construct_layout, audit_layout
from veritas.research.parent_child_r98.shrinking_oracle import parent_point
from veritas.research.parent_child_r99 import (build_packet_modes, verify_packet_modes,
    evaluate_packet_point, verify_packet_term, contract_packet_recursion)
from veritas.research.parent_child_r99.recovery import make_packet_plan, packet_points, recover_packet_grid


def fixture(cross=True, u=1, degree=4):
    net = TensorNetwork(2, tuple(Factor((e,), values, side+str(e))
                                for e in range(2) for side, values in (("row:",(1,3)),("col:",(2,5)))))
    p = from_described(describe_integer_network(net, creation_precision=5,
                                               defining_polynomial=first_irreducible(degree)), root_s=16, precision=5)
    l = construct_layout(p, a=2, u=u, budget=Budget())
    src = l.source
    src['row_labels'] = {'0':[0,0], '1':[0,0]}
    src['column_labels'] = {'0':[int(cross),0], '1':[int(cross),0]}
    src['H_pad'] = 4
    src['packets'] = [{'symbol_pairs':[[0,int(cross)],[0,0]], 'index':0, 'occupied_slots':[[0,0],[2,1]]}]
    l = PacketLayout(p.content_digest, 2, u, canonical(src))
    audit_layout(p,l)
    return p,l


@pytest.fixture(scope='module')
def crossing():
    p,l=fixture(u=2)
    b=Budget()
    m=build_packet_modes(p,l,1,(1 << 40,0,0,0),budget=b)
    verify_packet_modes(p,l,m,budget=b)
    values=[0]*len(m.certificate['modes']); values[0]=2
    beta=ExponentTuple(m.content_digest,tuple(values))
    cs=construct_children(p,l,m,beta,budget=b,_admitted=True)
    r=JetRing(ExtensionRing(m.certificate['precision'],p.defining_polynomial),1)
    value=r.one
    for c in cs:
        value=r.mul(value,leaf(c.as_parent(p),b))
    assert value!=r.zero
    return p,l,m,beta,cs,value


def test_multislot_shared_mode_exponent_two_is_nonzero(crossing):
    p,l,m,beta,cs,value=crossing
    assert len(l.source['packets'][0]['occupied_slots'])==2
    assert len(m.certificate['modes'][0]['rows'])==2
    assert any(x['exponent']>0 for x in m.certificate['modes'])
    report=verify_packet_term(p,l,m,beta,cs,value,budget=Budget())
    assert report['status']=='PASS_FINITE_GENERAL_PACKET_COEFFICIENT'
    assert report['result']==value
    assert not report['complete_point_verified']
    assert not report['all_source_shrink']


@pytest.mark.parametrize('attack', ['drop','duplicate','source','target','weight','count','coefficient'])
def test_general_mode_mutations(crossing,attack):
    p,l,m,*_=crossing; d=m.certificate
    if attack=='drop':d['modes'].pop()
    elif attack=='duplicate':d['modes'].append(d['modes'][0])
    elif attack=='count':d['mode_tuple_count']+=1
    elif attack=='coefficient':d['modes'][0]['rows'][0][1][0][0]^=2
    else:d['modes'][0][{'source':'source_group','target':'target_group','weight':'weight'}[attack]]+=1
    with pytest.raises(ValueError):verify_packet_modes(p,l,ModeSet(l.content_digest,canonical(d)),budget=Budget())


def test_incomplete_tuple_budget_refuses_before_any_child(crossing):
    p,l,m,*_=crossing; b=Budget(Policy(max_tuples=1))
    with pytest.raises(Refusal,match='complete weighted tuple count'):
        evaluate_packet_point(p,l,m,budget=b)
    assert b.calls==b.tuples==0


@pytest.mark.parametrize('attack',['value','beta','omitted_child','creation'])
def test_term_mutations_return_no_result(crossing,attack):
    p,l,m,beta,cs,value=crossing
    if attack=='value':value=((0,0,0,0),)
    elif attack=='beta':beta=ExponentTuple(m.content_digest,(0,)*len(beta.values))
    elif attack=='omitted_child':cs=cs[:-1]
    else:
        cs=(replace(cs[0],precision=cs[0].precision+1),)+cs[1:]
    result=verify_packet_term(p,l,m,beta,cs,value,budget=Budget())
    assert 'result' not in result


def test_independent_term_checker_does_not_call_production(crossing,monkeypatch):
    import veritas.research.parent_child_r99.basis as builder
    import veritas.research.parent_child_r98.constructor as constructor
    def forbidden(*a,**k): raise AssertionError('production called')
    monkeypatch.setattr(builder,'build_packet_modes',forbidden)
    monkeypatch.setattr(constructor,'construct_children',forbidden)
    p,l,m,beta,cs,value=crossing
    assert verify_packet_term(p,l,m,beta,cs,value,budget=Budget())['status'].startswith('PASS')


def test_complete_multivaluation_grid_nonconstant_multislot():
    p,l=fixture(cross=False,u=2); b=Budget()
    plan=make_packet_plan(p,l,budget=b)
    assert {n.valuation for n in plan.nodes}=={0,1}
    rows=[]
    for t,z,precision in packet_points(p,l,plan,budget=b):
        m=build_packet_modes(p,l,t,z,budget=b)
        assert m.certificate['mode_tuple_count']==1
        value=evaluate_packet_point(p,l,m,budget=b)
        assert value==parent_point(p,l,m,budget=b)
        rows.append([t,list(z),precision,list(value[0])])
    result,cert=recover_packet_grid(p,l,rows,budget=b)
    assert result==((17**2 % 32,0,0,0),)
    assert len(rows)==6*15
    with pytest.raises(ValueError):recover_packet_grid(p,l,rows[:-1],budget=Budget())
    wrong=[list(row) for row in rows];wrong[0][2]-=1
    with pytest.raises(ValueError):recover_packet_grid(p,l,wrong,budget=Budget())


def test_production_leaf_does_not_call_oracle(monkeypatch):
    import veritas.research.parent_child_r99.engine as engine
    def forbidden(*a,**k):raise AssertionError('oracle called')
    monkeypatch.setattr(engine,'tuple_coefficient',forbidden)
    monkeypatch.setattr(engine,'verify_children',forbidden)
    p,_=fixture()
    report=contract_packet_recursion(p)
    assert report['result']==((1,0,0,0),)
    assert report['status']=='PASS_FINITE_SCALED_LEAF'


def test_active_strict_recursion_without_contraction_oracles(monkeypatch):
    from pathlib import Path
    from veritas.research.parent_child_r98.shrinking_cli import load_input
    from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
    from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
    import veritas.research.parent_child_r99.engine as engine
    def forbidden(*a,**k):raise AssertionError('production contraction oracle called')
    monkeypatch.setattr(engine,'tuple_coefficient',forbidden)
    monkeypatch.setattr(engine,'verify_children',forbidden)
    p=load_input(Path(__file__).resolve().parents[1]/'examples/r98_general_matching22.json')
    def layout(call,a,u,budget):
        assert (a,u)==(1,1)
        return construct_vertex_shrinking_layout(call,budget=budget)
    result=contract_packet_recursion(p,schedule=((1,1),),layout_factory=layout,
                                    policy=replace(DEFAULT_SHRINKING_POLICY,max_work=1_000_000_000))
    assert result['status']=='PASS_FINITE_GENERAL_PACKET_RECURSION',result
    assert result['result'][0][0]==31**22
    assert result['ledger']['maximum_depth']==1
    assert result['ledger']['point_evaluations']==134
    assert not result['source_qualified']


def test_active_invalid_packing_has_no_result():
    from pathlib import Path
    from veritas.research.parent_child_r98.shrinking_cli import load_input
    from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
    p=load_input(Path(__file__).resolve().parents[1]/'examples/r98_general_matching22.json')
    result=contract_packet_recursion(p,policy=DEFAULT_SHRINKING_POLICY)
    assert not result['status'].startswith('PASS')
    assert 'result' not in result
