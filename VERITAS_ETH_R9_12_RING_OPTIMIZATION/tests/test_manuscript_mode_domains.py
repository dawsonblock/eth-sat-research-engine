"""Second finite topology and the target-group crossing-denominator invariant."""
from fractions import Fraction
from itertools import product
from math import comb,factorial

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.manuscript.cauchy import Point,Kernel
from veritas.research.manuscript.children import point_contraction
from veritas.research.manuscript.experimental import ScaledExperiment
from veritas.research.manuscript.model import DenseTensor,Vertex,Network,direct
from veritas.research.manuscript.modes import Domain
from veritas.research.manuscript.resources import Budget,Limits
from veritas.research.manuscript.ring import Ring


def _budget():return Budget(Limits(max_work=200_000_000,max_seconds=120))


@pytest.mark.parametrize('a',[1,2,3,4])
def test_target_group_bits_force_valid_crossing_denominators(a):
    L=1<<a;budget=_budget()
    for t in range(-L,L):
        if not t:continue
        i=(abs(t)&-abs(t)).bit_length()-1
        point=Point(L,t,(0,1),5,7,1);ring=Ring(5,7,1,budget);kernel=Kernel(point,ring)
        for x in range(L):
            for y0 in range(1<<(i+1)):
                # In an active packet the row's label is pair[bit_i(x)],
                # while a mode's target is pair[bit_i(y0)]. A targeted mode
                # therefore has equal bits. Other modes are not evaluated
                # against that row. Full beta enumeration does not alter this.
                if (x>>i)&1 != (y0>>i)&1:continue
                d=t-y0+x
                assert d!=0
                assert (abs(d)&-abs(d)).bit_length()-1<=i
                kernel.mode_coefficient(x,y0,0)
                kernel.mode_coefficient(x,y0,2)


def _network():
    return Network(2,(
        Vertex('row',0,(0,1),DenseTensor(2,3,((1,2),(3,1),(2,4),(5,6)))),
        Vertex('column',0,(0,),DenseTensor(1,3,((2,1),(1,3)))),
        Vertex('column',1,(1,),DenseTensor(1,3,((3,2),(2,1))))))


def _rational_kernel(L,t,x,y,z,ring):
    coefficients=[Fraction(1)]
    for root in range(-L,L):
        if root==y-x:continue
        nxt=[Fraction(0)]*(len(coefficients)+1)
        for j,c in enumerate(coefficients):nxt[j]-=root*c;nxt[j+1]+=c
        coefficients=nxt
    denominator=(-1)**(L-1)*factorial(L)*factorial(L-1)
    shifted=[sum(c*comb(j,k)*t**(j-k)*(2*L)**k for j,c in enumerate(coefficients) if j>=k)/denominator
             for k in range(len(coefficients))]
    value=ring.zero
    for c in reversed(shifted):
        assert c.denominator&1
        scalar=c.numerator*pow(c.denominator,-1,ring.modulus)%ring.modulus
        value=ring.add(ring.mul(value,z),ring.elem([scalar]))
    return value


def _half_edge_oracle(network,layout,point):
    ring=ExtensionRing(point.precision,point.f);ell=point.ell
    addresses={edge:(pid,slot) for pid,packet in enumerate(layout.packets) for slot,edge in packet.slots}
    weights={}
    for x in range(network.wires):
        for y in range(network.wires):
            px,sx=addresses[x];py,sy=addresses[y]
            weights[x,y]=(_rational_kernel(layout.L,point.t,sx,sy,point.zeta,ring) if px==py else ring.zero)
    def add(a,b):return tuple(ring.add(x,y) for x,y in zip(a,b))
    def mul(a,b):
        out=[]
        for k in range(ell):
            value=ring.zero
            for j in range(k+1):value=ring.add(value,ring.mul(a[j],b[k-j]))
            out.append(value)
        return tuple(out)
    total=(ring.zero,)*ell
    for ys in product((0,1),repeat=network.wires):
        for xs in product((0,1),repeat=network.wires):
            term=(ring.one,)+(ring.zero,)*(ell-1)
            for v in network.vertices:
                bits=ys if v.side=='row' else xs
                row=v.tensor.values[sum(bits[edge]<<j for j,edge in enumerate(v.ports))]
                term=mul(term,tuple(ring.elem([value]) for value in row))
            for edge,bit in enumerate(ys):
                linear=ring.zero
                for col,x in enumerate(xs):
                    if x:linear=ring.add(linear,weights[edge,col])
                factor=linear if bit else ring.sub(ring.one,linear)
                term=tuple(ring.mul(c,factor) for c in term)
            total=add(total,term)
    return total


@pytest.mark.parametrize('t',[-3,-2,-1,1,2,3])
def test_two_wire_two_occupied_packets_full_point_identity(t):
    network=_network();budget=_budget();layout=ScaledExperiment(a=2,u=2).layout(network,budget)
    assert sum(bool(packet.slots) for packet in layout.packets)==2
    point=Point(4,t,(0,1),3,7,2);ring=Ring(3,7,2,budget)
    domain=Domain(layout,point,budget)
    actual=point_contraction(network,layout,domain,ring,
        lambda child,p:direct(child,Ring(p,7,2,budget)),require_bounds=False)
    assert actual==_half_edge_oracle(network,layout,point)
