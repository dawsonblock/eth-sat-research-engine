"""Exact unramified extension arithmetic and arbitrary finite V truncation."""
from dataclasses import dataclass
from veritas.research.eth_arithmetic.gf2 import is_irreducible, pow_mod
from .parameters import natural


def choose_polynomial(degree, budget):
    natural(degree, 'extension degree', 1)
    budget.bits(degree+1, 'defining polynomial')
    for low in range(1, 1 << degree, 2):
        budget.tick(degree*degree)
        f = (1 << degree)|low
        if is_irreducible(f):
            return f
    raise ArithmeticError('irreducible polynomial existence contradicted')


@dataclass(frozen=True)
class Ring:
    p: int
    f: int
    ell: int
    budget: object

    def __post_init__(self):
        natural(self.p,'precision',1); natural(self.ell,'jet length',1)
        natural(self.f,'defining polynomial',2)
        # Derived quantities are pure functions of the frozen fields: compute
        # them once. Plain instance attributes replace the former @property
        # recomputation (millions of bit_length calls per contraction).
        e = self.f.bit_length()-1
        zero_scalar = (0,)*e
        for name, value in (
            ('e', e),
            ('mask', (1 << self.p)-1),
            ('zero_scalar', zero_scalar),
            ('one_scalar', (1,)+(0,)*(e-1)),
            ('zero', (zero_scalar,)*self.ell),
            ('one', ((1,)+(0,)*(e-1),)+(zero_scalar,)*(self.ell-1)),
            ('f_bits', tuple((self.f >> j) & 1 for j in range(e))),
        ):
            object.__setattr__(self, name, value)
        self.budget.bits(self.p, 'coefficient')
        self.budget.items(self.e*self.ell, 'ring element')
        # Irreducibility is authenticated once at root construction; precision
        # changes retain that same immutable defining polynomial.

    def scalar(self, n): return (n & self.mask,)+(0,)*(self.e-1)
    def integer(self, n): return (self.scalar(n),)+(self.zero_scalar,)*(self.ell-1)
    def embed(self, scalar): return (tuple(scalar),)+(self.zero_scalar,)*(self.ell-1)

    def scalar_add(self, a, b):
        self.budget.tick(self.e)
        return tuple((x+y)&self.mask for x,y in zip(a,b))

    def scalar_neg(self, a): return tuple((-x)&self.mask for x in a)
    def scalar_sub(self, a, b):
        self.budget.tick(self.e)
        return tuple((x-y)&self.mask for x,y in zip(a,b))

    def scalar_mul(self, a, b):
        e = self.e
        self.budget.tick(2*e*e)
        out = [0]*(2*e-1)
        for i,x in enumerate(a):
            for j,y in enumerate(b):
                out[i+j] += x*y
        # All arithmetic is mod-2^p-linear, so masking once at the end preserves
        # the residues exactly while skipping per-add mask operations.
        mask = self.mask
        f_bits = self.f_bits
        for k in range(len(out)-1, e-1, -1):
            top = out[k] & mask
            if top:
                for j in range(e):
                    if f_bits[j]:
                        out[k-e+j] -= top
        return tuple(x & mask for x in out[:e])

    def scalar_pow(self, a, n):
        natural(n,'exponent')
        out = self.one_scalar
        while n:
            if n&1: out = self.scalar_mul(out,a)
            n >>= 1
            if n: a = self.scalar_mul(a,a)
        return out

    def inverse(self, a):
        parity = sum((x&1) << i for i,x in enumerate(a))
        if not parity: raise ZeroDivisionError('nonunit extension element')
        self.budget.tick(self.e*self.e)
        bits = pow_mod(parity,(1 << self.e)-2,self.f)
        out = tuple((bits >> i)&1 for i in range(self.e))
        p = 1
        while p < self.p:
            p = min(2*p,self.p)
            r = Ring(p,self.f,self.ell,self.budget)
            out = r.scalar_mul(out,r.scalar_sub(r.scalar(2),r.scalar_mul(a,out)))
        if self.scalar_mul(a,out) != self.one_scalar:
            raise ArithmeticError('unit inverse failed')
        return out

    def valuation(self, a):
        return min(((x&-x).bit_length()-1 if x else self.p for x in a),default=self.p)

    def add(self, a, b): return tuple(self.scalar_add(x,y) for x,y in zip(a,b))
    def neg(self, a): return tuple(self.scalar_neg(x) for x in a)
    def sub(self, a, b): return self.add(a,self.neg(b))
    def scale(self, a, c): return tuple(self.scalar_mul(x,c) for x in a)

    def mul(self, a, b):
        out = [self.zero_scalar]*self.ell
        for i,x in enumerate(a):
            for j in range(min(self.ell-i, len(b))):
                out[i+j] = self.scalar_add(out[i+j],self.scalar_mul(x,b[j]))
        return tuple(out)

    def pow(self, a, n):
        natural(n,'exponent'); out=self.one
        while n:
            if n&1: out=self.mul(out,a)
            n >>= 1
            if n: a=self.mul(a,a)
        return out

    def canonical(self, value):
        if (type(value) is not tuple or len(value)!=self.ell or
            any(type(c) is not tuple or len(c)!=self.e or
                any(type(x) is not int or not 0<=x<=self.mask for x in c) for c in value)):
            raise ValueError('canonical complete coefficient vector required')
        return value

    def residue(self, value):
        if len(value)!=self.ell or any(len(c)!=self.e for c in value):
            raise ValueError('coefficient-ring dimensions differ')
        return tuple(tuple(x&self.mask for x in c) for c in value)
