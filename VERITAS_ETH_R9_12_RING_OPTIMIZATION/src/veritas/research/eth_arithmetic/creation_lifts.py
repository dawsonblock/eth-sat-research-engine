"""Immutable creation-time representatives for recursive tensor entries.

A lift Z/2^p -> Z/2^P by least residues is NOT a ring homomorphism.
Never recompute an old entry in a larger ring; retain its creation-precision
residue, then embed its integer coordinate representatives.
"""
from __future__ import annotations
from dataclasses import dataclass
from .extension_ring import ExtensionRing
from .jets import JetRing

@dataclass(frozen=True)
class CreationEntry:
    creation_precision: int
    defining_polynomial: int
    coefficients: tuple[int, ...]

    @classmethod
    def capture(cls, ring: ExtensionRing, value):
        if len(value)!=ring.e or any(type(x) is not int or x<0 or x>=ring.modulus for x in value):
            raise ValueError('entry is not canonical at creation precision')
        return cls(ring.p,ring.f,tuple(value))

    def __post_init__(self):
        r=ExtensionRing(self.creation_precision,self.defining_polynomial)
        if type(self.coefficients) is not tuple or len(self.coefficients)!=r.e or any(type(x) is not int or x<0 or x>=r.modulus for x in self.coefficients):
            raise ValueError('creation entry is not in canonical normal form')

    def evaluate(self, ring: ExtensionRing):
        if ring.f!=self.defining_polynomial or ring.p<self.creation_precision:
            raise ValueError('incompatible extension ring or decreased precision')
        return ring.elem(self.coefficients)

    def to_dict(self):
        return {'creation_precision':self.creation_precision,
                'defining_polynomial':self.defining_polynomial,
                'coefficients':list(self.coefficients)}


@dataclass(frozen=True)
class CreationJetEntry:
    """Immutable coordinate representatives of a truncated-ring entry."""
    creation_precision: int
    defining_polynomial: int
    coefficients: tuple[tuple[int, ...], ...]

    @classmethod
    def capture(cls, ring: JetRing, value):
        if not isinstance(ring, JetRing):
            raise TypeError('JetRing required')
        if (len(value) != ring.length or any(len(c) != ring.base.e for c in value) or
                any(type(x) is not int or x < 0 or x >= ring.base.modulus
                    for c in value for x in c)):
            raise ValueError('jet entry is not canonical at creation precision')
        return cls(ring.base.p, ring.base.f, tuple(tuple(c) for c in value))

    def __post_init__(self):
        base = ExtensionRing(self.creation_precision, self.defining_polynomial)
        if (type(self.coefficients) is not tuple or not 1 <= len(self.coefficients) <= 64 or
                any(type(c) is not tuple or len(c) != base.e for c in self.coefficients) or
                any(type(x) is not int or x < 0 or x >= base.modulus
                    for c in self.coefficients for x in c)):
            raise ValueError('creation jet is not in canonical immutable normal form')

    def evaluate(self, ring: JetRing):
        if (not isinstance(ring, JetRing) or ring.base.f != self.defining_polynomial or
                ring.base.p < self.creation_precision or ring.length != len(self.coefficients)):
            raise ValueError('incompatible jet ring or decreased precision')
        return ring.elem(self.coefficients)
