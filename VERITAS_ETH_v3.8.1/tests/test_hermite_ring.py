"""Independent modular Hermite recovery checks."""
import random
from fractions import Fraction
import pytest
from veritas.research.hermite_ring import (
    hermite_plan, reconstruct_mod, jets_from_polynomial, modular_fraction)
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.cauchy_deformation import (
    exact_cauchy_deformation, shifted_cauchy_jet_mod)


def test_reconstruction_random_polynomials():
    rng = random.Random(2026103009)
    for degree in range(0,15):
        # No node at zero: this is a genuine reconstruction and not F(0) lookup.
        points=[(-2, 6),(-1,6),(1,6)]
        plan=hermite_plan(points,alpha=4,degree_bound=degree)
        assert len(plan.samples_used)==degree+1
        for _ in range(5):
            coeff=[rng.randrange(-10_000,10_000) for _ in range(degree+1)]
            p=9
            data_bits=p+plan.guard_bits
            assert data_bits<=256
            jets=jets_from_polynomial(coeff,plan,data_precision_bits=data_bits)
            assert reconstruct_mod(plan,jets,precision_bits=p,data_precision_bits=data_bits) == coeff[0]%(1<<p)
            if plan.guard_bits:
                with pytest.raises(ValueError,match='insufficient'):
                    reconstruct_mod(plan,jets,precision_bits=p,data_precision_bits=data_bits-1)


def test_odd_denominator_fraction_and_exact_residue():
    plan=hermite_plan([(-2,3),(1,3)],alpha=4,degree_bound=4)
    coeff=[Fraction(1,3),Fraction(-7,5),3,Fraction(7,9),2]
    bits=16+plan.guard_bits
    jets=jets_from_polynomial(coeff,plan,data_precision_bits=bits)
    assert reconstruct_mod(plan,jets,precision_bits=16,data_precision_bits=bits) == modular_fraction(coeff[0],16)


def test_hermite_rejects_malformed_specifications():
    with pytest.raises(ValueError,match='insufficient'):
        hermite_plan([(1,2)],alpha=4,degree_bound=3)
    with pytest.raises(ValueError,match='distinct'):
        hermite_plan([(1,2),(1,2)],alpha=4,degree_bound=3)
    with pytest.raises(ValueError):
        modular_fraction(Fraction(1,2),8)
    with pytest.raises(ValueError):
        hermite_plan([(1,2)],alpha=0,degree_bound=1)
    plan=hermite_plan([(1,2)],alpha=2,degree_bound=1)
    with pytest.raises(ValueError):
        jets_from_polynomial([1,2,3],plan,data_precision_bits=8)
    with pytest.raises(ValueError):
        reconstruct_mod(plan,((1,),),precision_bits=8,data_precision_bits=12)


@pytest.mark.parametrize('clauses',[[[1]],[[1,2]],[[1],[-1]],[[1,2],[-2]]])
def test_independent_cauchy_jets_reconstruct_count(clauses):
    n=max(abs(k) for c in clauses for k in c)
    network=from_cnf(CNF.from_lists(n,clauses))
    degree=network.edges*3
    plan=hermite_plan([(-2,degree+1)],alpha=4,degree_bound=degree)
    p=10
    bits=p+plan.guard_bits
    assert bits<=256
    jet,_=shifted_cauchy_jet_mod(network,packet_size=2,node=-2,
                                 precision_bits=bits,jet_order=degree+1)
    poly,_=exact_cauchy_deformation(network,packet_size=2)
    assert reconstruct_mod(plan,(jet,),precision_bits=p,data_precision_bits=bits)==int(poly[0])%(1<<p)
