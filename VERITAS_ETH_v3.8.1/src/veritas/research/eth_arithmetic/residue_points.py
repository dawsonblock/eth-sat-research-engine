"""Distinct residue classes for interpolation over unramified 2-adic rings.

Represent GF(2^e) residues by bit vectors in the power basis of f(U).
Pairwise DISTINCT residues imply all pairwise differences are UNITS in R_p.
"""
from __future__ import annotations
from .extension_ring import ExtensionRing


def lift_binary(ring: ExtensionRing, bits: int):
    if type(bits) is not int or bits < 0 or bits >= (1 << ring.e):
        raise ValueError('residue bits must lie in GF(2^e)')
    return ring.elem([(bits >> i) & 1 for i in range(ring.e)])


def residue_key(element):
    return sum((int(x) & 1) << i for i, x in enumerate(element))


def validate_residue_points(ring: ExtensionRing, points, *, max_points=256):
    pts=tuple(points)
    if len(pts)>max_points or len(pts)>(1<<ring.e):
        raise ValueError('too many interpolation points')
    seen=set()
    for p in pts:
        if not isinstance(p, (tuple,list)) or len(p)!=ring.e:
            raise ValueError('point has incorrect extension-ring degree')
        if any(type(c) is not int or c<0 or c>=ring.modulus for c in p):
            raise ValueError('point is not in the specified ring')
        k=residue_key(p)
        if k in seen:
            raise ValueError('duplicate residue: interpolation denominator is a nonunit')
        seen.add(k)
    return pts


def distinct_residue_points(ring: ExtensionRing, count: int, *, max_points=256):
    if type(count) is not int or count<0:
        raise ValueError('count must be nonnegative')
    if count>max_points or count>(1<<ring.e):
        raise ValueError('insufficient distinct residue classes or point budget')
    return validate_residue_points(ring,[lift_binary(ring,i) for i in range(count)],max_points=max_points)
