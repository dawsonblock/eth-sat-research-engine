"""Integer formulas from eq:tensor-parameters and lem:tapered-hermite.

There is no finite-experiment a<=3 restriction and no substituted leaf size.
"""
from dataclasses import dataclass
from math import isqrt


def natural(n, name, minimum=0):
    if type(n) is not int or n < minimum:
        raise ValueError(name+' must be an integer at least '+str(minimum))
    return n


def ceil_root(n, k):
    natural(n, 'radicand'); natural(k, 'root degree', 1)
    if not n:
        return 0
    # Integer Newton iteration from an upper bound, then exact correction.
    x = 1 << ((n.bit_length()+k-1)//k)
    while True:
        y = ((k-1)*x+n//(x**(k-1)))//k
        if y >= x:
            break
        x = y
    while x**k > n:
        x -= 1
    return x if x**k == n else x+1


@dataclass(frozen=True)
class Schedule:
    s: int
    size_constant: int = 1

    def __post_init__(self):
        natural(self.s, 's', 2); natural(self.size_constant, 'C', 1)

    @property
    def lam(self):
        return (self.s-1).bit_length()

    @property
    def extension_degree(self):
        return 4*self.lam

    @property
    def leaf_wires(self):
        d = isqrt(self.lam)
        return (self.s+d-1)//d

    @property
    def delta(self):
        if self.s==(1 << self.lam) and (9*self.lam)%10==0:
            return 1 << (9*self.lam//10)
        return ceil_root(self.s**9, 10)

    def at(self, depth):
        natural(depth, 'depth')
        u = 0 if depth>=self.lam.bit_length() else self.lam//(131072 << depth)
        # Floors eventually vanish; avoid work proportional to an irrelevant
        # enormous supplied depth.
        a = 2*sum(self.lam//(131072 << j)
                  for j in range(min(depth+1, self.lam.bit_length())))
        return a, u

    def active_preconditions(self, wires, depth):
        a, u = self.at(depth)
        if wires <= self.leaf_wires:
            return False
        if not 1 <= u <= a or u > wires:
            return False
        L, D, delta = 1 << a, 1 << (12*a), self.delta
        return wires >= 2*D*D*delta and wires >= L*D and 2*L <= delta

    def admits_recursive_regime(self):
        """Check sufficient conditions for every possible active descendant.

        The root uses direct summation when the manuscript's sufficiently-large
        regime is unavailable. Testing H+1 covers every M>H; the depth bound
        follows from M<=C*s/8**d. This is not a scaled replacement schedule.
        """
        largest = self.size_constant*self.s
        depth = 0
        while largest > self.leaf_wires:
            if not self.active_preconditions(self.leaf_wires+1, depth):
                return False
            a,_=self.at(depth)
            if largest*((2 << a)-1)+1 > 1 << self.extension_degree:
                return False
            largest //= 8
            depth += 1
        return True


@dataclass(frozen=True)
class Node:
    t: int
    valuation: int
    multiplicity: int
    precision: int


def hermite_nodes(M, a, u, p):
    for value, name in ((M,'M'),(a,'a'),(u,'u'),(p,'p')):
        natural(value, name, 1)
    if u > min(M, a):
        raise ValueError('requires 1<=u<=min(M,a)')
    L, h = 1 << a, (3*M+u-1)//u
    for t in range(-L, L):
        if t:
            i = (abs(t)&-abs(t)).bit_length()-1
            if i < u:
                yield Node(t, i, h*(u-i), p+8*h*(L >> i)+8*M*(a+1))
