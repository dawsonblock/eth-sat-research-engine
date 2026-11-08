from fractions import Fraction
from itertools import product
from math import comb,factorial
from types import MappingProxyType
import random
import pytest

from veritas.research.manuscript.resources import Budget,Limits
from veritas.research.manuscript.parameters import Schedule,hermite_nodes,ceil_root
from veritas.research.manuscript.ring import Ring,choose_polynomial
from veritas.research.manuscript.model import DenseTensor,Vertex,Network,direct
from veritas.research.manuscript.packing import Layout,Packet,construct
from veritas.research.manuscript.cauchy import Point,Kernel
from veritas.research.manuscript.modes import Domain
from veritas.research.manuscript.children import point_contraction,child
from veritas.research.manuscript.recovery import recover
from veritas.research.manuscript.executor import contract
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing


def budget():return Budget(Limits(500_000_000,180,2_000_000,1_000_000))


def shifted_kernel_coefficients(L,t,x,y):
    """Independent rational polynomial multiplication in T, then binomial shift."""
    coefficients=[Fraction(1)]
    for root in range(-L,L):
        if root==y-x:continue
        nxt=[Fraction(0)]*(len(coefficients)+1)
        for j,c in enumerate(coefficients):nxt[j]-=root*c;nxt[j+1]+=c
        coefficients=nxt
    denominator=(-1)**(L-1)*factorial(L)*factorial(L-1)
    return [sum(c*comb(j,k)*t**(j-k)*(2*L)**k for j,c in enumerate(coefficients) if j>=k)/denominator
            for k in range(len(coefficients))]


def rational_evaluate(coefficients,z,ring):
    out=ring.zero
    for c in reversed(coefficients):
        assert c.denominator&1
        value=c.numerator*pow(c.denominator,-1,ring.modulus)%ring.modulus
        out=ring.add(ring.mul(out,z),ring.elem([value]))
    return out


def packet_example(a=3,p=6,ell=2):
    # Two real slots in the same directed class; bit 2 encodes copies and the
    # active group coordinate is bit 1. Positive geometric exponents survive.
    rows=DenseTensor(2,3,((1,2),(3,1),(2,4),(5,6)) if ell==2 else ((1,),(3,),(2,),(5,)))
    cols=DenseTensor(2,3,((2,3),(1,5),(6,1),(4,2)) if ell==2 else ((2,),(1,),(6,),(4,)))
    network=Network(2,(Vertex('row',0,(0,1),rows),Vertex('column',0,(0,1),cols)))
    layout=Layout(a,2,MappingProxyType({0:(0,0,0)}),MappingProxyType({0:(0,1,0)}),
                  (Packet(((0,0),(0,1),(0,0)),0,((0,0),(4,1))),),8,0)
    point=Point(8,2,(0,1),p,7,ell)
    return network,layout,point


def independent_half_edges(network,point):
    old=ExtensionRing(point.precision,point.f)
    L=point.L;slots=(0,4);ell=point.ell
    w={(x,y):rational_evaluate(shifted_kernel_coefficients(L,point.t,x,y),point.zeta,old) for x in slots for y in slots}
    zero=(old.zero,)*ell
    def mul(a,b):return tuple(sum_ext(old,[old.mul(a[j],b[k-j]) for j in range(k+1)]) for k in range(ell))
    total=list(zero)
    for ys in product((0,1),repeat=2):
        for xs in product((0,1),repeat=2):
            tensor=[]
            for v,bits in zip(network.vertices,(ys,xs)):
                tensor.append(tuple(old.elem([c]) for c in v.tensor.values[sum(x<<j for j,x in enumerate(bits))]))
            term=mul(*tensor)
            for x,bit in zip(slots,ys):
                linear=sum_ext(old,[w[x,y] for y,b in zip(slots,xs) if b])
                factor=linear if bit else old.sub(old.one,linear)
                term=tuple(old.mul(c,factor) for c in term)
            total=[old.add(a,b) for a,b in zip(total,term)]
    return tuple(total)


def sum_ext(ring,values):
    out=ring.zero
    for value in values:out=ring.add(out,value)
    return out


def test_source_schedule_and_non_power_size_thresholds():
    for n in range(2,100):
        d=Schedule(n).delta
        assert (d-1)**10<n**9<=d**10
    s=Schedule(1 << 2_000_000)
    assert [s.at(d) for d in range(4)]==[(30,15),(44,7),(50,3),(52,1)]
    assert s.admits_recursive_regime()
    assert s.at(10**8)==(52,0)
    assert not Schedule(100).admits_recursive_regime()


@pytest.mark.parametrize('p',[1,17,257])
def test_extension_and_truncation_against_separate_arithmetic(p):
    b=budget();ring=Ring(p,11,3,b);old=ExtensionRing(p,11);rng=random.Random(p)
    for _ in range(8):
        a=tuple(rng.randrange(1 << p) for _ in range(3));c=tuple(rng.randrange(1 << p) for _ in range(3))
        assert ring.scalar_mul(a,c)==old.mul(a,c)
        if any(x&1 for x in a):assert ring.inverse(a)==old.inverse(a)
        x=(a,c,a);y=(c,a,c)
        assert ring.mul(x,y)==tuple(sum_ext(old,[old.mul(x[j],y[k-j]) for j in range(k+1)]) for k in range(3))


def test_full_mode_domain_and_packet_identity_including_empty_sources():
    network,layout,point=packet_example();b=budget();r=Ring(point.precision,point.f,point.ell,b)
    domain=Domain(layout,point,b)
    tuples=list(domain.tuples())
    assert len(tuples)==domain.count()==len(set(tuples))
    assert tuples==sorted(tuples)
    assert any(max(beta)>1 for beta in tuples)
    assert any(domain.mode(j).exponent>0 and n for beta in tuples for j,n in enumerate(beta))
    result=point_contraction(network,layout,domain,r,lambda graph,p:direct(graph,Ring(p,point.f,point.ell,b)),require_bounds=False)
    assert result==independent_half_edges(network,point)


def test_packet_entries_keep_creation_representatives_when_precision_increases():
    network,layout,point=packet_example();b=budget();domain=Domain(layout,point,b)
    beta=[0]*domain.size;beta[0]=1
    graph=child(network,layout,domain,tuple(beta),0,require_bounds=False)
    recipe=next(v.tensor for v in graph.vertices if v.side=='column')
    old=Ring(point.precision,point.f,point.ell,b);higher=Ring(point.precision+7,point.f,point.ell,b)
    for bits in product((0,1),repeat=recipe.arity):
        assert recipe.entry(bits,old)==recipe.entry(bits,higher)


@pytest.mark.parametrize('a,u,M',[(1,1,1),(3,2,2),(4,1,1)])
def test_full_hermite_recovery_with_nonunit_node_differences(a,u,M):
    b=budget();degree=M*((2 << a)-1);e=(degree+1).bit_length();f=choose_polynomial(e,b)
    target=Ring(7,f,2,b);L=1 << a
    def evaluate(node,z,ring):
        old=ExtensionRing(node.precision,f,max_precision_bits=65536)
        value=rational_evaluate(shifted_kernel_coefficients(L,node.t,0,0),z,old)
        return value,old.add(old.mul(old.elem([3]),value),old.elem([2]))
    result=recover(M,a,u,target,evaluate)
    assert result==(target.scalar(1),target.scalar(5))
    assert len({n.precision for n in hermite_nodes(M,a,u,7)})==u


def test_whole_label_packing_retains_padded_empty_packets():
    tensor=DenseTensor(1,3,((1,),(2,)))
    net=Network(3,tuple(Vertex(side,j,(j,),tensor) for side in ('row','column') for j in range(3)))
    b=budget();packing=construct(net,1,1,b,r=2,require_bounds=False)
    assert len(packing.packets)==(2**2)*packing.padded_height//2
    real=[edge for packet in packing.packets for _,edge in packet.slots]
    assert sorted(real)==list(range(3))
    assert any(not p.slots for p in packing.packets)


def test_connected_source_executor_uses_exact_leaf_rule_and_fails_closed():
    t=DenseTensor(2,3,((1,2),(3,1),(2,4),(5,6)))
    net=Network(4,(Vertex('row',0,(0,1),t),Vertex('row',1,(2,3),t),
        Vertex('column',0,(1,2),t),Vertex('column',1,(3,0),t)))
    result=contract(net,s=2,precision=3,ell=2,size_constant=2)
    assert result['status']=='PASS_MANUSCRIPT_CONSTRUCTION_EXECUTION'
    assert result['route']=='SOURCE_DIRECT_RANGE' and result['parameters']['leaf_threshold']==2
    # Integer polynomial oracle, independently summing the original four bits.
    expected=[0,0]
    for bits in product((0,1),repeat=4):
        term=[1,0]
        for v in net.vertices:
            value=v.tensor.values[sum(bits[e]<<j for j,e in enumerate(v.ports))]
            term=[term[0]*value[0],term[0]*value[1]+term[1]*value[0]]
        expected=[(x+y)%8 for x,y in zip(expected,term)]
    assert [row[0] for row in result['result']]==expected
    refused=contract(net,s=2,precision=3,ell=2,size_constant=2,limits=Limits(max_work=1))
    assert refused['status']=='INCONCLUSIVE_RESOURCE_LIMIT' and 'result' not in refused
