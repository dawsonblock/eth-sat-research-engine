"""Lagrange/Newton interpolation with only UNIT denominators.

For residue-distinct x_i in R=(Z/2^pZ)[U]/f, Vandermonde determinants
are units. Newton differences recover the UNIQUE degree<n polynomial
from n evaluations. This is an exact finite R-algebra statement, not the
manuscript's full tapered Hermite recovery.
"""
from __future__ import annotations
from dataclasses import dataclass
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.residue_points import validate_residue_points, distinct_residue_points


def evaluate_polynomial(ring: ExtensionRing, coefficients, point):
    z=ring.zero
    for coeff in reversed(tuple(coefficients)):
        z=ring.add(ring.mul(z,point),coeff)
    return z


def _polynomial_multiply_by_linear(ring, coeffs, root):
    out=[ring.zero for _ in range(len(coeffs)+1)]
    for i,c in enumerate(coeffs):
        out[i]=ring.sub(out[i],ring.mul(root,c))
        out[i+1]=ring.add(out[i+1],c)
    return out


def interpolate_newton(ring: ExtensionRing, points, values, *, max_points=256):
    xs=validate_residue_points(ring,points,max_points=max_points)
    ys=tuple(values)
    if not xs or len(xs)!=len(ys):
        raise ValueError('need equally many nonempty points and values')
    for v in ys:
        if len(v)!=ring.e or any(type(c) is not int or c<0 or c>=ring.modulus for c in v):
            raise ValueError('noncanonical interpolation value')
    n=len(xs)
    differences=list(ys)
    for j in range(1,n):
        for i in range(n-1,j-1,-1):
            denom=ring.sub(xs[i],xs[i-j])
            if not ring.is_unit(denom):
                raise ZeroDivisionError('interpolation denominator is not a unit')
            differences[i]=ring.mul(ring.sub(differences[i],differences[i-1]),ring.inverse(denom))
    coeffs=[ring.zero for _ in range(n)]
    basis=[ring.one]
    for k in range(n):
        for i,b in enumerate(basis):
            coeffs[i]=ring.add(coeffs[i],ring.mul(differences[k],b))
        if k+1<n:
            basis=_polynomial_multiply_by_linear(ring,basis,xs[k])
    result=tuple(coeffs)
    for x,y in zip(xs,ys):
        if evaluate_polynomial(ring,result,x)!=y:
            raise ArithmeticError('interpolation replay mismatch')
    return result


@dataclass(frozen=True)
class TaylorRecovery:
    coefficients: tuple
    points: tuple
    values: tuple
    precision: int
    extension_degree: int
    shifted_center: int
    shifted_scale: int
    claim: str='FINITE_EXTENSION_RING_POLYNOMIAL_RECOVERY_ONLY'

    def to_dict(self):
        return {'coefficients':[list(v) for v in self.coefficients],
                'points':[list(v) for v in self.points],
                'values':[list(v) for v in self.values],
                'precision':self.precision,'extension_degree':self.extension_degree,
                'shifted_center':self.shifted_center,
                'shifted_scale':self.shifted_scale,'claim':self.claim}


def recover_shifted_polynomial(ring: ExtensionRing, evaluate_at,
                               *, degree: int, center: int, scale: int,
                               max_points=256, truncate: int | None=None):
    """Recover polynomial P(z)=F(center+scale*z) from a ring evaluation callback.

    `evaluate_at` must evaluate the chosen polynomial in R at its argument,
    not silently perform rational divisions with even denominators.
    Small bounded reference: degree+1 samples, so no subexponential claim.
    """
    if type(degree) is not int or degree<0 or degree+1>max_points:
        raise ValueError('degree outside reference interpolation budget')
    if type(center) is not int or type(scale) is not int or scale<=0:
        raise ValueError('integral center and positive scale required')
    if truncate is not None and (type(truncate) is not int or not 1<=truncate<=degree+1):
        raise ValueError('invalid truncation')
    pts=distinct_residue_points(ring,degree+1,max_points=max_points)
    values=tuple(evaluate_at(p) for p in pts)
    coeffs=interpolate_newton(ring,pts,values,max_points=max_points)
    return TaylorRecovery(coeffs if truncate is None else coeffs[:truncate],
          pts,values,ring.p,ring.e,center,scale)
