"""Independent bounded checks of Appendix D.4.3 equations (76) and (77)."""
from fractions import Fraction
import random
import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract
from veritas.research.cauchy_deformation import (
    cauchy_kernel, shifted_integral_kernel, _poly_eval, _polynomial_shift,
    exact_cauchy_deformation, shifted_cauchy_jet_mod, verify_cauchy_small,
    coefficient_valuations)


def mod2power(v: Fraction, p: int) -> int:
    v = Fraction(v)
    assert v.denominator & 1
    return v.numerator * pow(v.denominator, -1, 1 << p) % (1 << p)


@pytest.mark.parametrize('L',[1,2,4,8])
def test_source_cauchy_kernel_zeros_and_grid_sparsity(L):
    W = cauchy_kernel(L)
    for i in range(L):
        for j in range(L):
            assert len(W[i][j]) == 2*L
            assert _poly_eval(W[i][j],0) == (i == j)
            for t in range(-L,L):
                if j-i != t:
                    assert _poly_eval(W[i][j],t) == 0
                else:
                    assert _poly_eval(W[i][j],t) != 0
    for t in range(-L,L):
        jet = shifted_integral_kernel(L,t)
        for i in range(L):
            for j in range(L):
                assert all(c.denominator & 1 for c in jet[i][j])
                assert jet[i][j][0] == _poly_eval(W[i][j],t)


def test_kernel_odd_denominator_not_integer_regression():
    # The coefficient 1/9 is valid in Z_2! Never require ordinary integrality.
    w=shifted_integral_kernel(4,0)
    assert any(c.denominator!=1 for row in w for poly in row for c in poly)
    assert all(c.denominator%2==1 for row in w for poly in row for c in poly)


@pytest.mark.parametrize('clauses',[[],[[]],[[1]],[[1],[-1]],[[1,2],[-1]],
                                    [[1,2],[-1,-2]], [[1],[-2],[3]],
                                    [[1,2,3]], [[1,1],[-1]]])
def test_full_cauchy_count_and_grid(clauses):
    n=max([3]+[abs(v) for c in clauses for v in c])
    net=from_cnf(CNF.from_lists(n,clauses),max_degree=6)
    for L in (1,2,4):
        poly,_=exact_cauchy_deformation(net,packet_size=L,max_edges=6,timeout_s=5)
        checks=verify_cauchy_small(net,poly,L)
        assert poly[0]==brute_contract(net)
        assert len(poly)==net.edges*(2*L-1)+1
        assert len(checks['grid_nodes_checked'])==2*L


@pytest.mark.parametrize('L,t,p,order',[(1,0,2,3),(2,-2,5,4),(2,1,8,5),
                                        (4,-4,3,7),(4,3,12,3),(4,0,24,10)])
def test_truncated_modular_jet_matches_full_polynomial(L,t,p,order):
    net=from_cnf(CNF.from_lists(3,[[1,2],[-1,3]]))
    poly,_=exact_cauchy_deformation(net,packet_size=L,max_edges=5)
    jet,_=shifted_cauchy_jet_mod(net,packet_size=L,node=t,precision_bits=p,jet_order=order)
    full=_polynomial_shift(poly,t,2*L,order)
    assert jet==tuple(mod2power(full[k] if k<len(full) else Fraction(0),p) for k in range(order))
    assert len(coefficient_valuations(jet,p))==order


def test_randomized_small_formulas():
    rng=random.Random(20261029)
    for z in range(25):
        n=rng.randrange(1,6)
        m=rng.randrange(0,5)
        clauses=[]
        for _ in range(m):
            k=rng.randrange(0,3)
            clauses.append([rng.choice([-1,1])*rng.randrange(1,n+1) for _ in range(k)])
        if sum(map(len,clauses))>5:
            continue
        cnf=CNF.from_lists(n,clauses)
        net=from_cnf(cnf,max_degree=6)
        poly,_=exact_cauchy_deformation(net,packet_size=2,max_edges=5)
        assert poly[0]==sum(cnf.evaluate({i+1:bool(mask & (1 << i)) for i in range(n)}) for mask in range(1 << n))
        verify_cauchy_small(net,poly,2)
        for node in (-2,1):
            jet,_=shifted_cauchy_jet_mod(net,packet_size=2,node=node,precision_bits=7,jet_order=4)
            oracle=_polynomial_shift(poly,node,4,4)
            assert jet == tuple(mod2power(oracle[i] if i<len(oracle) else Fraction(0),7) for i in range(4))


def test_reject_invalid_grids_and_budget():
    for L in (0,3,16,True):
        with pytest.raises(ValueError):cauchy_kernel(L)
    with pytest.raises(ValueError):shifted_integral_kernel(2,2)
    net=from_cnf(CNF.from_lists(4,[[1,2],[3,4]]))
    with pytest.raises(ValueError):exact_cauchy_deformation(net,max_edges=3)
    with pytest.raises(ValueError):shifted_cauchy_jet_mod(net,precision_bits=0)
    with pytest.raises(ValueError):shifted_cauchy_jet_mod(net,jet_order=0)


def test_jet_tampering_is_detectable():
    net=from_cnf(CNF.from_lists(2,[[1],[2]]))
    poly,_=exact_cauchy_deformation(net,packet_size=2)
    tampered=list(poly)
    tampered[0]+=1
    with pytest.raises(AssertionError):verify_cauchy_small(net,tampered,2)
