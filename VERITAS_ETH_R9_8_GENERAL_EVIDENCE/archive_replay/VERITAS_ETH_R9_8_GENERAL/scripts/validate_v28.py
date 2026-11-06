"""Seeded independent checks for finite extension interpolation."""
import random
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.extension_lagrange import interpolate_newton,evaluate_polynomial
from veritas.research.eth_interpolation.shifted_cauchy import verify_cauchy_interpolation


def main():
    rng=random.Random(261028)
    trials=0
    for deg in (2,3,4,5):
        for p in (2,5,8,12):
            r=ExtensionRing(p,first_irreducible(deg))
            for n in range(1,min(1<<deg,10)+1):
                xs=distinct_residue_points(r,n)
                for _ in range(12):
                    c=tuple(r.elem([rng.randrange(r.modulus) for _ in range(deg)]) for _ in range(n))
                    yy=tuple(evaluate_polynomial(r,c,x) for x in xs)
                    assert interpolate_newton(r,xs,yy)==c
                    trials+=1
    cauchy=0
    for L in (1,2,4):
        for t in range(-L,L):
            r=ExtensionRing(12,first_irreducible(max(1,(2*L-1).bit_length())))
            report=verify_cauchy_interpolation(L,t,r)
            cauchy+=report['matrix_entries_verified']
    print(f'PASS: {trials} seeded full-polynomial recovery checks; {cauchy} shifted Cauchy entries')

if __name__=='__main__':main()
