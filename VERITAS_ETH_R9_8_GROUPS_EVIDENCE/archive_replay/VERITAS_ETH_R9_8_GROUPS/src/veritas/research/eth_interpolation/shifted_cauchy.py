"""Exact shift T=t+2^(a+1)z of the manuscript's Cauchy kernel.

Work in Q[z] until the factor C'(0) has been cancelled exactly.
Only then map 2-adically integral rational coefficients into the ring.
Never invert an even integer modulo 2^p. Small bounded packet reference.
"""
from __future__ import annotations
from fractions import Fraction
from math import comb
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from .extension_lagrange import interpolate_newton,evaluate_polynomial
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points


def shifted_fraction_coefficients(coefficients, t: int, scale: int):
    if type(t) is not int or type(scale) is not int or scale<=0:
        raise ValueError('integer center and positive scale required')
    out=[Fraction(0) for _ in coefficients]
    for k,ck in enumerate(coefficients):
        for j in range(k+1):
            out[j]+=Fraction(ck)*comb(k,j)*pow(t,k-j)*pow(scale,j)
    return tuple(out)


def fraction_to_ring(ring: ExtensionRing, x):
    x=Fraction(x)
    if x.denominator%2==0:
        raise ValueError('nonintegral 2-adic rational; forbidden even denominator')
    reduced=(x.numerator*pow(x.denominator,-1,ring.modulus))%ring.modulus
    return ring.elem([reduced])


def shift_cauchy_entry(L: int, t: int, ring: ExtensionRing, x: int, y: int):
    if type(L) is not int or L<1 or L>8 or L&(L-1):
        raise ValueError('supported power-of-two packets: 1, 2, 4, 8')
    if type(t) is not int or t not in range(-L,L):
        raise ValueError('t outside interpolation nodes')
    if type(x) is not int or type(y) is not int or x not in range(L) or y not in range(L):
        raise ValueError('invalid Cauchy matrix indices')
    a=L.bit_length()-1
    scale=1<<(a+1)
    raw=cauchy_matrix_polynomials(L)[x][y]
    shifted=shifted_fraction_coefficients(raw,t,scale)
    return tuple(fraction_to_ring(ring,c) for c in shifted)


def cauchy_jet_grid(L: int, t: int, ring: ExtensionRing):
    return tuple(tuple(shift_cauchy_entry(L,t,ring,x,y)
                       for y in range(L)) for x in range(L))


def verify_cauchy_interpolation(L: int,t:int,ring:ExtensionRing,*,max_points=64):
    """Independent evaluation and Newton reconstruction for all W_xy jets.

    Samples are evaluated by Horner on the original *shifted* coefficients;
    interpolation implementation independently reconstructs monomial form.
    This verifies the finite arithmetic pathway, not recursion or Hermite.
    """
    if 2*L>max_points:
        raise ValueError('interpolation sample budget exceeded')
    if (1<<ring.e)<2*L:
        raise ValueError('extension degree lacks distinct residue points')
    points=distinct_residue_points(ring,2*L,max_points=max_points)
    grid=cauchy_jet_grid(L,t,ring)
    number=0
    for row in grid:
        for original in row:
            # W has degree 2L-1, so 2L samples uniquely determine it.
            values=tuple(evaluate_polynomial(ring,original,z) for z in points)
            reconstructed=interpolate_newton(ring,points,values,max_points=max_points)
            if tuple(original)!=reconstructed:
                raise AssertionError('Cauchy interpolation coefficient mismatch')
            number+=1
    return {'status':'FINITE_CAUCHY_SHIFTED_JETS_VERIFIED',
            'packet_size':L,'node':t,'precision_bits':ring.p,
            'extension_degree':ring.e,'sample_points':2*L,
            'matrix_entries_verified':number,
            'full_recursive_contraction':False,
            'subexponential_runtime_proven':False}
