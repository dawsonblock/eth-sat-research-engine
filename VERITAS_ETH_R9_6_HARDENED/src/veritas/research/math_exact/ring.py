"""Typed finite quotient arithmetic with explicit creation precision.

The extension polynomial is the monic binary lift of an irreducible F2
polynomial, represented by its coefficient bits. Operations require equal
rings. Reduction is explicit; a canonical representative is never a lift.
"""
from __future__ import annotations
from dataclasses import dataclass
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing


@dataclass(frozen=True, slots=True)
class Ring:
    precision: int
    polynomial: int
    length: int

    def __post_init__(self):
        # Cap degree before the irreducibility algorithm or polynomial allocation.
        if type(self.polynomial) is not int or not 1 <= self.polynomial.bit_length() - 1 <= 32:
            raise ValueError('extension degree must be 1..32')
        self._backend()

    def _backend(self):
        return JetRing(ExtensionRing(self.precision, self.polynomial), self.length)

    def element(self, coefficients=()):
        rows = tuple(tuple(row) for row in coefficients)
        if any(type(x) is not int for row in rows for x in row):
            raise ValueError('coefficients must be integers')
        return Element(self, self._backend().elem(rows), self.precision)

    def integer(self, value):
        if type(value) is not int:
            raise ValueError('integer required')
        return self.element(((value,),))

    @property
    def zero(self):
        return self.integer(0)

    @property
    def one(self):
        return self.integer(1)


@dataclass(frozen=True, slots=True)
class Element:
    ring: Ring
    coefficients: tuple[tuple[int, ...], ...]
    creation_precision: int

    def __post_init__(self):
        if not isinstance(self.ring, Ring):
            raise TypeError('Ring required')
        if type(self.creation_precision) is not int or not self.ring.precision <= self.creation_precision <= 1024:
            raise ValueError('invalid creation precision')
        rows = tuple(tuple(row) for row in self.coefficients)
        b = self.ring._backend()
        if len(rows) != b.length or any(len(row) != b.base.e for row in rows):
            raise ValueError('incorrect quotient coefficient dimensions')
        if any(type(x) is not int or not 0 <= x < b.base.modulus for row in rows for x in row):
            raise ValueError('coefficients must be canonical residues')
        object.__setattr__(self, 'coefficients', rows)

    def _binary(self, other, operation):
        if not isinstance(other, Element) or self.ring != other.ring:
            raise ValueError('operands must have the same ring and precision')
        data = getattr(self.ring._backend(), operation)(self.coefficients, other.coefficients)
        return Element(self.ring, data, self.ring.precision)

    def __add__(self, other): return self._binary(other, 'add')
    def __sub__(self, other): return self._binary(other, 'sub')
    def __mul__(self, other): return self._binary(other, 'mul')
    def __neg__(self):
        return Element(self.ring, self.ring._backend().neg(self.coefficients), self.ring.precision)

    def inverse(self):
        return Element(self.ring, self.ring._backend().inverse(self.coefficients), self.ring.precision)

    def valuation(self):
        """Minimum coefficient valuation, capped at the known precision."""
        b = self.ring._backend().base
        return min(b.valuation(row) for row in self.coefficients)

    def reduce_precision(self, precision):
        if type(precision) is not int or not 1 <= precision <= self.ring.precision:
            raise ValueError('precision reduction cannot increase precision')
        target = Ring(precision, self.ring.polynomial, self.ring.length)
        modulus = 1 << precision
        rows = tuple(tuple(x % modulus for x in row) for row in self.coefficients)
        return Element(target, rows, self.creation_precision)


@dataclass(frozen=True, slots=True)
class Polynomial:
    """Ordinary polynomial over Ring; coefficients ordered low degree first."""
    ring: Ring
    coefficients: tuple[Element, ...]

    def __post_init__(self):
        if not isinstance(self.ring, Ring): raise TypeError('Ring required')
        coeffs = tuple(self.coefficients)
        if any(not isinstance(x, Element) or x.ring != self.ring for x in coeffs):
            raise ValueError('polynomial coefficients must belong to its ring')
        object.__setattr__(self, 'coefficients', coeffs)

    def __add__(self, other):
        if not isinstance(other, Polynomial) or self.ring != other.ring:
            raise ValueError('polynomial rings must match')
        z = self.ring.zero
        return Polynomial(self.ring, tuple((self.coefficients[i] if i < len(self.coefficients) else z) +
            (other.coefficients[i] if i < len(other.coefficients) else z)
            for i in range(max(len(self.coefficients), len(other.coefficients)))) )

    def __mul__(self, other):
        if not isinstance(other, Polynomial) or self.ring != other.ring:
            raise ValueError('polynomial rings must match')
        if not self.coefficients or not other.coefficients: return Polynomial(self.ring, ())
        out = [self.ring.zero for _ in range(len(self.coefficients)+len(other.coefficients)-1)]
        for i, a in enumerate(self.coefficients):
            for j, b in enumerate(other.coefficients): out[i+j] = out[i+j] + a*b
        return Polynomial(self.ring, tuple(out))

    def evaluate(self, value):
        if not isinstance(value, Element) or value.ring != self.ring:
            raise ValueError('evaluation point must belong to polynomial ring')
        result = self.ring.zero
        for coefficient in reversed(self.coefficients): result = result*value + coefficient
        return result
