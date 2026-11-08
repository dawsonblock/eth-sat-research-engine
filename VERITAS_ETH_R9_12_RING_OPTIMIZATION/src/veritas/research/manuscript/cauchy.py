"""eq:tensor-cauchy evaluated after exact cancellation of powers of two."""
from dataclasses import dataclass
from math import factorial


@dataclass(frozen=True)
class Point:
    L: int
    t: int
    zeta: tuple[int, ...]
    precision: int
    f: int
    ell: int

    def __post_init__(self):
        if type(self.L) is not int or self.L<2 or self.L&(self.L-1):raise ValueError('power-of-two packet width required')
        if type(self.t) is not int or not -self.L<=self.t<self.L or not self.t:raise ValueError('nonzero Cauchy node required')
        if len(self.zeta)!=self.f.bit_length()-1 or any(type(c) is not int or not 0<=c<(1 << self.precision) for c in self.zeta):
            raise ValueError('canonical interpolation coordinates required')

    @property
    def coordinate(self):return (abs(self.t)&-abs(self.t)).bit_length()-1


class Kernel:
    def __init__(self,point,ring):
        if (point.precision,point.f,point.ell)!=(ring.p,ring.f,ring.ell):raise ValueError('point ring mismatch')
        self.point,self.ring=point,ring
        L=point.L
        ring.budget.bits(2*L*L.bit_length(),'Cauchy denominator')
        derivative=(-1 if (L-1)&1 else 1)*factorial(L)*factorial(L-1)
        self.denominator_twos=(abs(derivative)&-abs(derivative)).bit_length()-1
        self.odd_inverse=pow(derivative//(1 << self.denominator_twos),-1,1 << ring.p)
        ring.budget.tick(2*L)

    def value(self,x,y):
        q,r=self.point,self.ring
        if not 0<=x<q.L or not 0<=y<q.L:raise ValueError('invalid packet slot')
        out=r.one_scalar;twos=0;alpha=2*q.L
        for root in range(-q.L,q.L):
            if root==y-x:continue
            if root==q.t:
                twos+=alpha.bit_length()-1;factor=q.zeta
            else:
                d=q.t-root;v=(abs(d)&-abs(d)).bit_length()-1;twos+=v
                factor=r.scalar_add(r.scalar(d//(1 << v)),r.scalar_mul(r.scalar(alpha >> v),q.zeta))
            out=r.scalar_mul(out,factor)
        remaining=twos-self.denominator_twos
        if remaining<0:raise ArithmeticError('Cauchy integrality failed')
        return r.scalar_mul(out,r.scalar(self.odd_inverse*pow(2,remaining,1 << r.p)))

    def mode_coefficient(self,x,y0,b):
        q,r=self.point,self.ring;i=q.coordinate;d=q.t-y0+x
        if not d:raise ValueError('zero crossing denominator')
        v=(abs(d)&-abs(d)).bit_length()-1
        if v>i:raise ValueError('row does not cross the specified tile')
        unit=r.scalar_add(r.scalar(d//(1 << v)),r.scalar_mul(r.scalar((2*q.L) >> v),q.zeta))
        ratio=r.scalar_mul(r.scalar(1 << (i+1-v)),r.inverse(unit))
        value=r.scalar_mul(self.value(x,y0),r.scalar_pow(ratio,b))
        if r.valuation(value)<min(r.p,b+1):raise ArithmeticError('mode valuation bound failed')
        return value
