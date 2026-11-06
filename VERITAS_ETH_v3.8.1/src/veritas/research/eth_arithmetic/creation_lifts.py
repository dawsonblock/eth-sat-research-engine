"""Immutable creation-time representatives for recursive tensor entries.

A lift Z/2^p -> Z/2^P by least residues is NOT a ring homomorphism.
Never recompute an old entry in a larger ring; retain its creation-precision
residue, then embed its integer coordinate representatives.
"""
from __future__ import annotations
from dataclasses import dataclass
from .extension_ring import ExtensionRing

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
        if len(self.coefficients)!=r.e or any(type(x) is not int or x<0 or x>=r.modulus for x in self.coefficients):
            raise ValueError('creation entry is not in canonical normal form')

    def evaluate(self, ring: ExtensionRing):
        if ring.f!=self.defining_polynomial or ring.p<self.creation_precision:
            raise ValueError('incompatible extension ring or decreased precision')
        return ring.elem(self.coefficients)

    def to_dict(self):
        return {'creation_precision':self.creation_precision,
                'defining_polynomial':self.defining_polynomial,
                'coefficients':list(self.coefficients)}
