"""Truncated V-jets over the finite 2-adic extension ring."""
from __future__ import annotations
from dataclasses import dataclass
from .extension_ring import ExtensionRing


@dataclass(frozen=True)
class JetRing:
    base: ExtensionRing
    length: int

    def __post_init__(self):
        if type(self.length) is not int or not 1<=self.length<=64:
            raise ValueError("jet length 1..64 required")

    @property
    def zero(self):
        return (self.base.zero,)*self.length

    @property
    def one(self):
        return (self.base.one,)+(self.base.zero,)*(self.length-1)

    def elem(self,coefficients):
        items=list(coefficients)
        if len(items)>self.length:
            raise ValueError("jet too long")
        return tuple(self.base.elem(x) for x in items)+(self.base.zero,)*(self.length-len(items))

    def add(self,a,b):
        return tuple(self.base.add(x,y) for x,y in zip(a,b))

    def neg(self,a):
        return tuple(self.base.neg(x) for x in a)

    def sub(self,a,b):
        return self.add(a,self.neg(b))

    def mul(self,a,b):
        out=[self.base.zero for _ in range(self.length)]
        for i,x in enumerate(a):
            for j in range(self.length-i):
                out[i+j]=self.base.add(out[i+j],self.base.mul(x,b[j]))
        return tuple(out)

    def inverse(self,a):
        if not self.base.is_unit(a[0]):
            raise ZeroDivisionError("jet constant term is not a unit")
        b=[self.base.inverse(a[0])]
        for n in range(1,self.length):
            s=self.base.zero
            for i in range(1,n+1):
                s=self.base.add(s,self.base.mul(a[i],b[n-i]))
            b.append(self.base.neg(self.base.mul(b[0],s)))
        result=tuple(b)
        if self.mul(a,result)!=self.one:
            raise ArithmeticError("jet inverse verification failed")
        return result
