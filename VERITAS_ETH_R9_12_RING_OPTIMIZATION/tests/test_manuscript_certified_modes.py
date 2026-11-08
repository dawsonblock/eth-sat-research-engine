"""Independent support, coefficient and cache checks beyond the L=2 shortcut."""
from dataclasses import replace
from itertools import product
from pathlib import Path
import runpy
from types import MappingProxyType

import pytest
from veritas.research.manuscript.cauchy import Point,Kernel
from veritas.research.manuscript.certified_modes import DegreeCertifiedDomain,SupportCertificateError
from veritas.research.manuscript.children import child,point_contraction
from veritas.research.manuscript.modes import Domain
from veritas.research.manuscript.model import direct
from veritas.research.manuscript.resources import Budget,Limits,ResourceLimit
from veritas.research.manuscript.ring import Ring

DRIVER=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_four_slot.py'))


def setup(p=8,t=1,z=(1,0,0,0),cache=True):
    b=Budget(Limits(max_work=100_000_000,max_seconds=120))
    n=DRIVER['fixture_network'](DRIVER['FIXTURE']);layout=DRIVER['fixture_layout']()
    point=Point(4,t,z,p,19,2)
    domain=DegreeCertifiedDomain(n,layout,point,b,cache_kernel=cache)
    return n,layout,domain,Ring(p,19,2,b),DRIVER['PointOracle'](DRIVER['FIXTURE'],p,t,z)


def sparse(beta):return tuple((j,v) for j,v in enumerate(beta) if v)


@pytest.mark.parametrize('p',[2,3,4,8,35])
@pytest.mark.parametrize('t',[-3,-2,-1,1,2,3])
def test_retained_domain_matches_independent_degree_enumeration(p,t):
    n,l,d,r,o=setup(p,t)
    values=list(d.tuples());expected=list(o.selected())
    assert [sparse(beta) for beta in values]==expected
    assert len(values)==len(set(values))
    assert all(sum((j//d.per_weight+1)*v for j,v in enumerate(beta))<p for beta in values)


@pytest.mark.parametrize('p',[2,3,4])
def test_every_omitted_formal_tuple_has_identically_zero_packet_tensor(p):
    n,l,d,r,o=setup(p);kept=set(d.tuples());formal=Domain(l,d.point,r.budget)
    omitted=0
    for beta in formal.tuples():
        if beta in kept:continue
        omitted+=1;found=False
        for group in (0,1):
            g=child(n,l,d,beta,group,require_bounds=False)
            for v in g.vertices:
                if v.side=='column' and all(v.tensor.entry(bits,r)==r.zero for bits in product((0,1),repeat=len(v.ports))):
                    found=True;break
            if found:break
        assert found, sparse(beta)
    assert omitted and len(kept)+omitted==formal.count()


@pytest.mark.parametrize('p,t,z',[(3,1,(1,0,0,0)),(4,-3,(0,1,0,0)),(8,1,(1,0,0,0)),(8,-1,(1,1,0,0)),(5,2,(0,1,0,0))])
def test_each_retained_child_and_complete_point_against_independent_oracle(p,t,z):
    n,l,d,r,o=setup(p,t,z);total=(o.r.zero,o.r.zero)
    for beta in d.tuples():
        term=(o.r.one,o.r.zero)
        for group in (0,1):
            actual=direct(child(n,l,d,beta,group,require_bounds=False),r)
            expected=o.child(sparse(beta),group)
            assert actual==expected
            term=DRIVER['jetmul'](term,expected,o.r)
        total=DRIVER['jetadd'](total,term,o.r)
    assert total==o.half_edge()


@pytest.mark.parametrize('selected',[(),((0,1),),((16,1),),((0,2),),((0,1),(16,1)),((16,2),)])
def test_all_packet_entries_and_creation_lifts(selected):
    n,l,d,r,o=setup();beta=[0]*d.size
    for index,power in selected:beta[index]=power
    beta=tuple(beta)
    for group in (0,1):
        g=child(n,l,d,beta,group,require_bounds=False);packet=next(v.tensor for v in g.vertices if v.side=='column' and v.identity==4)
        for bits in product((0,1),repeat=2):
            if group==1:
                expected=o.r.one
                for index,power in selected:
                    b=index//d.per_weight
                    linear=sum((slot//2)**b*bit for slot,bit in zip((0,2),bits))
                    expected=o.r.mul(expected,o.r.elem([linear**power]))
            else:
                powers=sum(power for index,power in selected)
                if not selected:expected=o.r.elem([(1-bits[0])*(1-bits[1])])
                elif powers==1:
                    b=selected[0][0]//d.per_weight
                    expected=o.r.add(o.r.mul(o.mode(0,0,b),o.r.elem([(1 if bits[0] else -1)*(1-bits[1])])),
                                     o.r.mul(o.mode(2,0,b),o.r.elem([(1 if bits[1] else -1)*(1-bits[0])])))
                elif powers==2:
                    modes=[index//d.per_weight for index,power in selected for _ in range(power)]
                    expected=o.r.mul(o.mode(0,0,modes[0]),o.mode(2,0,modes[1]))
                    if len(selected)==2:expected=o.r.add(expected,o.r.mul(o.mode(0,0,modes[1]),o.mode(2,0,modes[0])))
                    expected=o.r.mul(expected,o.r.elem([(1 if bits[0] else -1)*(1 if bits[1] else -1)]))
                else:expected=o.r.zero
            expected=(expected,o.r.zero)
            assert packet.entry(bits,r)==expected
            assert packet.entry(bits,Ring(11,19,2,r.budget))==expected


def test_higher_modes_and_power_two_are_genuinely_nonzero():
    o=setup()[4]
    for selected in (((16,1),),((0,2),)):
        term=DRIVER['jetmul'](o.child(selected,0),o.child(selected,1),o.r)
        assert term!=(o.r.zero,o.r.zero)


@pytest.mark.parametrize('mutation',[
    lambda l:replace(l,packets=l.packets[:-1]),
    lambda l:replace(l,padded_height=8),
    lambda l:replace(l,variance_scaled=0),
    lambda l:replace(l,rows=MappingProxyType({0:(False,0)})),
    lambda l:replace(l,columns=MappingProxyType({0:(0,1)})),
    lambda l:replace(l,packets=tuple(replace(p,slots=((0,0),(1,1))) if p.slots else p for p in l.packets)),
])
def test_malformed_support_geometry_refused(mutation):
    n,l,d,r,o=setup()
    with pytest.raises((SupportCertificateError,ValueError)):
        DegreeCertifiedDomain(n,mutation(l),d.point,r.budget)


def test_cache_bound_context_and_exact_immutability():
    n,l,d,r,o=setup();cache=d.packet_kernel(r)
    first=cache.mode_coefficient(0,0,1);work=r.budget.work
    assert cache.mode_coefficient(0,0,1) is first
    assert r.budget.work==work+1
    assert type(first) is tuple
    for other in (Ring(9,19,2,r.budget),Ring(8,19,1,r.budget),Ring(8,19,2,Budget())):
        with pytest.raises(SupportCertificateError):d.packet_kernel(other)
    r.budget.limits=replace(r.budget.limits,max_items=1)
    with pytest.raises(ResourceLimit):cache.mode_coefficient(2,0,2)


def test_cache_disabled_preserves_values():
    n,l,d,r,o=setup(cache=False)
    assert type(d.packet_kernel(r)) is Kernel
    for beta in d.tuples():
        for group in (0,1):assert direct(child(n,l,d,beta,group,require_bounds=False),r)==o.child(sparse(beta),group)


def test_sparse_mode_cache_does_not_hide_unsupported_manual_beta():
    n,l,d,r,o=setup();eligible={j for j,w,k in d.eligible}
    index=next(j for j in range(d.size) if j not in eligible)
    beta=tuple(int(i==index) for i in range(d.size));pid=d.mode(index).packet
    assert list(d.packet_modes(pid,beta))==[(d.mode(index),1)]
    zero=(0,)*d.size
    assert list(d.packet_modes(pid,zero))==[]
    assert list(d.packet_modes(pid,beta))==[(d.mode(index),1)]


def test_support_iterator_fails_closed_on_budget():
    n,l,d,r,o=setup();r.budget.limits=replace(r.budget.limits,max_work=r.budget.work+1)
    iterator=d.tuples();next(iterator)
    with pytest.raises(ResourceLimit):next(iterator)


def test_independent_hermite_precision_and_finite_producer_refusal():
    assert [DRIVER['required_precision'](t) for t in (-3,-2,-1,1,2,3)]==[35,9,35,35,9,35]
    receipt=DRIVER['produce'](limits=Limits(max_work=1))
    assert receipt['report']['status']=='INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in receipt['report']


def custom_parallel(a,coordinate,wires=2):
    from veritas.research.manuscript.packing import Layout,Packet
    from veritas.research.manuscript.model import Network,Vertex,DenseTensor
    # The other equal-coordinate bits encode the copy offset independently.
    pattern=tuple((0,1) if j==coordinate else (0,0) for j in range(a))
    equal=[j for j in range(a) if j!=coordinate]
    slots=tuple((sum(((offset>>k)&1)<<j for k,j in enumerate(equal)),offset) for offset in range(wires))
    packets=[];L=2**a
    for pat in product(((0,0),(0,1),(1,1)),repeat=a):
        for index in range(L//2**sum(lo==hi for lo,hi in pat)):
            packets.append(Packet(pat,index,slots if (pat,index)==(pattern,0) else ()))
    labels=(0,)*a;columns=tuple(int(j==coordinate) for j in range(a))
    layout=Layout(a,2,MappingProxyType({0:labels}),MappingProxyType({0:columns}),tuple(packets),L,(2**(2*a)-1)*wires*wires)
    values=tuple((i%4,(i+1)%4) for i in range(2**wires))
    n=Network(wires,tuple(Vertex(side,0,tuple(range(wires)),DenseTensor(wires,2,values)) for side in ('row','column')))
    return n,layout,slots


def test_occupied_second_coordinate_uses_group_cap_not_tile_cap():
    n,l,slots=custom_parallel(2,1);b=Budget(Limits(max_work=10000000));r=Ring(9,19,2,b)
    d=DegreeCertifiedDomain(n,l,Point(4,2,(1,0,0,0),9,19,2),b)
    assert len(d.eligible)==2 and set(d.capacities.values())=={2}
    assert all(d.mode(index).exponent==0 for index,w,key in d.eligible)
    index=d.eligible[0][0];mode=d.mode(index);beta=tuple(2 if j==index else 0 for j in range(d.size))
    assert beta in set(d.tuples())  # Two rows can target the same one-column tile.
    oracle=DRIVER['PointOracle'](DRIVER['FIXTURE'],9,2,(1,0,0,0))
    row_packet=next(v.tensor for v in child(n,l,d,beta,0,require_bounds=False).vertices if v.side=='column' and v.identity==mode.packet)
    expected=oracle.r.mul(oracle.mode(0,mode.tile,0),oracle.mode(1,mode.tile,0))
    assert expected!=oracle.r.zero
    for bits in product((0,1),repeat=2):
        sign=(1 if bits[0] else -1)*(1 if bits[1] else -1)
        assert row_packet.entry(bits,r)==(oracle.r.mul(expected,oracle.r.elem([sign])),oracle.r.zero)
    # The shared target degree cap rejects total 3 across distinct tiles.
    beta=[0]*d.size;beta[d.eligible[0][0]]=2;beta[d.eligible[1][0]]=1
    assert tuple(beta) not in set(d.tuples())


@pytest.mark.parametrize('exponent,expected',[(1,2),(2,4),(3,8)])
def test_eight_slot_source_uses_true_geometric_j_not_boolean_j(exponent,expected):
    n,l,slots=custom_parallel(3,0,4);b=Budget(Limits(max_work=10000000));r=Ring(8,19,2,b)
    d=DegreeCertifiedDomain(n,l,Point(8,1,(1,0,0,0),8,19,2),b)
    index=next(index for index,w,key in d.eligible if d.mode(index).exponent==exponent)
    beta=tuple(int(i==index) for i in range(d.size));mode=d.mode(index)
    column_packet=next(v.tensor for v in child(n,l,d,beta,1,require_bounds=False).vertices if v.side=='column' and v.identity==mode.packet)
    assert [slot for slot,e in slots]==[0,2,4,6]
    assert column_packet.entry((0,0,1,0),r)==r.integer(expected)


@pytest.mark.parametrize('mutation',[
    lambda l:replace(l,rows=MappingProxyType({False:(0,0)})),
    lambda l:replace(l,packets=(replace(l.packets[0],pattern=((False,False),(0,0))),)+l.packets[1:]),
])
def test_boolean_identifiers_and_patterns_refused(mutation):
    n,l,d,r,o=setup()
    with pytest.raises(SupportCertificateError):DegreeCertifiedDomain(n,mutation(l),d.point,r.budget)


def test_mutable_point_coordinates_and_boolean_precision_refused():
    n,l,d,r,o=setup()
    for point in (replace(d.point,zeta=list(d.point.zeta)),replace(d.point,precision=True,zeta=(0,0,0,0))):
        with pytest.raises(ValueError):DegreeCertifiedDomain(n,l,point,r.budget)


@pytest.mark.parametrize('p',[2,3,5,8])
def test_multiple_target_groups_match_independent_l2_certificate(p):
    from veritas.research.manuscript.experimental import ScaledExperiment
    from veritas.research.manuscript.model import Network,Vertex,DenseTensor
    old=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_connected_two_level.py'))
    vertices=tuple(Vertex(side,i,(2*i,2*i+1) if side=='row' else (i,i+2),
                          DenseTensor(2,2,((1,2),(3,1),(2,0),(1,2)))) for side in ('row','column') for i in (0,1))
    n=Network(4,vertices);b=Budget(Limits(max_work=10000000));l=ScaledExperiment().layout(n,b);point=Point(2,1,(1,0,0,0),p,19,2)
    new=DegreeCertifiedDomain(n,l,point,b);reference=old['CertifiedSlotDomain'](n,l,point,b)
    assert len(new.capacities)>1
    assert list(new.tuples())==list(reference.tuples())


@pytest.mark.parametrize('t,z',[(-3,(1,0,0,0)),(-1,(0,1,0,0)),(1,(1,1,0,0)),(3,(0,0,1,0))])
def test_point_caches_do_not_cross_evaluation_context(t,z):
    n,l,d,r,o=setup(t=t,z=z);cache=d.packet_kernel(r)
    for x in (0,2):
        for exponent in (0,1,3):assert cache.mode_coefficient(x,0,exponent)==o.mode(x,0,exponent)


def test_independent_layout_derives_copy_bits_and_rejects_mutation(monkeypatch):
    import copy
    l=DRIVER['fixture_layout']();record=DRIVER['layout_record'](l)
    assert DRIVER['verify_layout_record'](record)
    bad=copy.deepcopy(record);bad['packets'][4]['slots']=((0,0),(1,1))
    with pytest.raises(DRIVER['ReplayError']):DRIVER['verify_layout_record'](bad)
    bad=copy.deepcopy(record);bad['rows']=[[0,[0,1]]]
    with pytest.raises(DRIVER['ReplayError']):DRIVER['verify_layout_record'](bad)
