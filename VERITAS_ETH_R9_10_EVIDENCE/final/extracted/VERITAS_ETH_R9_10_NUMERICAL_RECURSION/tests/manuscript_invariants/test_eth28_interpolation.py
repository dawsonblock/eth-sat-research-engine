"""Independent small-instance checks for new v2.8 finite ring tools."""
from fractions import Fraction
from itertools import product
from random import Random
import pytest

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.residue_points import (
    distinct_residue_points, validate_residue_points, lift_binary)
from veritas.research.eth_arithmetic.creation_lifts import CreationEntry
from veritas.research.eth_interpolation.extension_lagrange import (
    interpolate_newton,evaluate_polynomial,recover_shifted_polynomial)
from veritas.research.eth_interpolation.shifted_cauchy import (
    cauchy_jet_grid, fraction_to_ring, shift_cauchy_entry,
    shifted_fraction_coefficients, verify_cauchy_interpolation)
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials,evaluate
from veritas.research.eth_packing.parameters import manuscript_parameters


def test_floor_boundary_and_depth():
    D=131072
    for lam in [1,D-1,D,D+1,2*D-1,2*D,2*D+1,4*D]:
        for depth in [0,1,2]:
            p=manuscript_parameters(1<<lam,depth)
            assert p.log2_s_ceil==lam
            assert p.u==lam//(D<<depth)
            assert p.a==2*sum(lam//(D<<j) for j in range(depth+1))
            assert not p.eligible
            assert p.source_status=='UNPINNED_PUBLIC_MAIN_REFERENCE'
    assert manuscript_parameters(1000).u==0
    with pytest.raises(ValueError):manuscript_parameters(1)


@pytest.mark.parametrize('precision',[1,2,7,12])
@pytest.mark.parametrize('degree',[2,3,4,5])
def test_interpolation_exact_independent_polynomial(precision,degree):
    rng=Random(12000+precision*100+degree)
    r=ExtensionRing(precision,first_irreducible(degree))
    n=min(1<<degree,9)
    pts=distinct_residue_points(r,n)
    for _ in range(16):
        original=tuple(r.elem([rng.randrange(r.modulus) for _ in range(degree)]) for _ in range(n))
        vals=tuple(evaluate_polynomial(r,original,x) for x in pts)
        recovered=interpolate_newton(r,pts,vals)
        assert recovered==original
        for x in (r.zero,r.one,r.elem([2,3])):
            assert evaluate_polynomial(r,recovered,x)==evaluate_polynomial(r,original,x)


def test_rejection_of_duplicate_residues_and_nonunits():
    r=ExtensionRing(7,first_irreducible(3))
    pts=distinct_residue_points(r,3)
    clone=r.add(pts[1],r.elem([2,0,0]))
    with pytest.raises(ValueError,match='duplicate residue'):
        interpolate_newton(r,[pts[0],pts[1],clone],[r.one]*3)
    with pytest.raises(ValueError):distinct_residue_points(r,9)
    with pytest.raises(ValueError):validate_residue_points(r,[(r.modulus,) + (0,)*(r.e-1)])
    with pytest.raises(ValueError):interpolate_newton(r,[],[])
    with pytest.raises(ValueError):fraction_to_ring(r,Fraction(1,2))
    assert fraction_to_ring(r,Fraction(-3,5))==r.elem([-3*pow(5,-1,r.modulus)])


def test_creation_time_canonical_lifts_nonhomomorphic():
    small=ExtensionRing(2,first_irreducible(2))
    big=ExtensionRing(5,small.f)
    three=small.elem([3])
    old_sum=CreationEntry.capture(small,small.add(three,three)).evaluate(big)
    fresh_sum=big.add(CreationEntry.capture(small,three).evaluate(big),
                      CreationEntry.capture(small,three).evaluate(big))
    assert old_sum!=fresh_sum  # canonical lift does NOT commute with +
    assert old_sum==big.elem([2]) and fresh_sum==big.elem([6])
    with pytest.raises(ValueError):CreationEntry.capture(small,three).evaluate(ExtensionRing(1,small.f))
    with pytest.raises(ValueError):CreationEntry.capture(small,(5,0))


@pytest.mark.parametrize('L',[1,2,4])
@pytest.mark.parametrize('precision',[1,5,12])
def test_exact_shifted_cauchy_fraction_oracle(L,precision):
    r=ExtensionRing(precision,first_irreducible(max(1,(2*L-1).bit_length())))
    original=cauchy_matrix_polynomials(L)
    alpha=1<<(L.bit_length())
    for t in range(-L,L):
        grid=cauchy_jet_grid(L,t,r)
        for x,y in product(range(L),repeat=2):
            expected=shifted_fraction_coefficients(original[x][y],t,alpha)
            assert grid[x][y]==tuple(fraction_to_ring(r,f) for f in expected)
            # Evaluate the shifted rational polynomial at ordinary integers.
            for z in [0,1,2,-1]:
                fz=evaluate(original[x][y],t+alpha*z)
                got=evaluate_polynomial(r,grid[x][y],r.elem([z]))[0]
                assert got==fraction_to_ring(r,fz)[0]
        assert verify_cauchy_interpolation(L,t,r)['matrix_entries_verified']==L*L


def test_recover_full_then_truncate_and_check_replay():
    r=ExtensionRing(9,first_irreducible(4))
    coeffs=tuple(r.elem([i+1, 3*i,2]) for i in range(6))
    fn=lambda z:evaluate_polynomial(r,coeffs,z)
    full=recover_shifted_polynomial(r,fn,degree=5,center=1,scale=8)
    assert full.coefficients==coeffs
    small=recover_shifted_polynomial(r,fn,degree=5,center=1,scale=8,truncate=3)
    assert small.coefficients==coeffs[:3]
    assert len(small.points)==6 and small.claim.startswith('FINITE_')
    with pytest.raises(ValueError):recover_shifted_polynomial(r,fn,degree=16,center=0,scale=4)
    with pytest.raises(ValueError):recover_shifted_polynomial(r,fn,degree=2,center=0,scale=0)


def test_cauchy_rejects_invalid_resources():
    r=ExtensionRing(6,first_irreducible(2))
    with pytest.raises(ValueError):verify_cauchy_interpolation(4,1,r)
    with pytest.raises(ValueError):shift_cauchy_entry(3,1,r,0,0)
    with pytest.raises(ValueError):shift_cauchy_entry(2,2,r,0,1)
