"""Exact arithmetic in (Z/2^pZ)[U]/(f(U)), with monic integer f.

The polynomial f is defined by its binary coefficients (0 or 1).
The mod-2 reduction is irreducible; therefore a class is a unit exactly
when its mod-2 representative is nonzero. This is a finite local ring,
not a field when p>1.
"""
from __future__ import annotations
from dataclasses import dataclass
from .gf2 import is_irreducible, degree, pow_mod


@dataclass(frozen=True)
class ExtensionRing:
    p: int
    f: int

    def __post_init__(self):
        if type(self.p) is not int or not 1<=self.p<=1024:
            raise ValueError("precision must be 1..1024 bits")
        if type(self.f) is not int or not is_irreducible(self.f):
            raise ValueError("mod-2 polynomial must be irreducible")

    @property
    def e(self):
        return degree(self.f)

    @property
    def modulus(self):
        return 1 << self.p

    @property
    def zero(self):
        return (0,)*self.e

    @property
    def one(self):
        return (1,)+(0,)*(self.e-1)

    def elem(self, coefficients):
        raw=list(coefficients)
        if len(raw)>self.e:
            raise ValueError("pass at most e reduced coefficients")
        return tuple(int(v)%self.modulus for v in raw) + (0,)*(self.e-len(raw))

    def add(self,a,b):
        return tuple((x+y)%self.modulus for x,y in zip(a,b))

    def neg(self,a):
        return tuple((-x)%self.modulus for x in a)

    def sub(self,a,b):
        return self.add(a,self.neg(b))

    def mul(self,a,b):
        e=self.e
        terms=[0]*(2*e-1)
        q=self.modulus
        for i,x in enumerate(a):
            for j,y in enumerate(b):
                terms[i+j]=(terms[i+j]+x*y)%q
        for k in range(2*e-2,e-1,-1):
            v=terms[k]
            if v:
                # U^e == -sum_{i<e} f_i U^i
                for i in range(e):
                    if self.f >> i & 1:
                        terms[k-e+i]=(terms[k-e+i]-v)%q
        return tuple(terms[:e])

    def pow(self,a,n):
        if n<0:
            raise ValueError("negative exponent")
        z=self.one
        while n:
            if n&1:z=self.mul(z,a)
            a=self.mul(a,a)
            n >>= 1
        return z

    def is_unit(self,a):
        return any(v&1 for v in a)

    def valuation(self,a):
        if not any(a):
            return self.p
        return min((v & -v).bit_length()-1 if v else self.p for v in a)

    def inverse(self,a):
        if not self.is_unit(a):
            raise ZeroDivisionError("nonunit element")
        parity=sum((v&1)<<i for i,v in enumerate(a))
        inv_bits=pow_mod(parity,(1<<self.e)-2,self.f)
        y=self.elem([(inv_bits>>i)&1 for i in range(self.e)])
        two=self.elem([2])
        # Hensel/Newton iteration in the finite ring, doubling p-adic precision.
        k=1
        while k<self.p:
            y=self.mul(y,self.sub(two,self.mul(a,y)))
            k*=2
        if self.mul(a,y)!=self.one:
            raise ArithmeticError("Hensel inverse verification failed")
        return y

    def reduce_precision(self,a,p):
        if not 1<=p<=self.p:
            raise ValueError('invalid precision reduction')
        return tuple(x % (1<<p) for x in a)

    def lift(self,a,p_new):
        # Canonical integer representative map is not a ring homomorphism.
        if not p_new>=self.p:
            raise ValueError("lift must not decrease precision")
        return ExtensionRing(p_new,self.f).elem(a)
