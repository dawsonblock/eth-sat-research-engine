from dataclasses import FrozenInstanceError
from fractions import Fraction
from itertools import product
import random

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork, from_cnf, brute_contract, eliminate
from veritas.research.math_exact import Ring, Element, Polynomial, exhaustive_count
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry, fraction_to_ring
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing


def independent_product(a, b, p, f, ell):
    """Convolve integer monomials, then reduce f and V^ell independently."""
    d = f.bit_length() - 1
    terms = [[0] * (2*d-1) for _ in range(ell)]
    for v, row in enumerate(a):
        for w, row2 in enumerate(b):
            if v+w < ell:
                for i, x in enumerate(row):
                    for j, y in enumerate(row2): terms[v+w][i+j] += x*y
    for row in terms:
        for degree in range(2*d-2, d-1, -1):
            for i in range(d):
                if f & (1 << i): row[degree-d+i] -= row[degree]
        del row[d:]
    return tuple(tuple(x % (1 << p) for x in row) for row in terms)


def test_count_all_small_clause_pairs_and_boundaries():
    literals = (-2, -1, 1, 2)
    clauses = [()] + [(x,) for x in literals] + list(product(literals, repeat=2))
    for selected in [()] + [(x,) for x in clauses] + list(product(clauses, repeat=2)):
        formula = CNF(2, selected)
        network = from_cnf(formula)
        expected = exhaustive_count(formula)
        assert brute_contract(network) == expected
        assert eliminate(network) == expected
    assert exhaustive_count(CNF(0, ())) == 1
    assert exhaustive_count(CNF(0, ((),))) == 0
    assert exhaustive_count(CNF(4, ((1,), (2, -2)))) == 8
    with pytest.raises(ValueError): exhaustive_count(CNF(3, ()), max_variables=2)


def test_tensor_and_cnf_are_deeply_immutable():
    ports, table = [0], [0, 1]
    f = Factor(ports, table, 'a')
    factors = [f, Factor([0], [1, 1], 'b')]
    n = TensorNetwork(1, factors)
    ports.clear(); table.clear(); factors.clear()
    assert n.factors[0].ports == (0,) and n.factors[0].table == (0, 1)
    source = [[1], [-1]]
    cnf = CNF(1, source); source[0].clear()
    assert cnf.clauses == ((1,), (-1,))
    with pytest.raises(FrozenInstanceError): f.ports = ()
    with pytest.raises(ValueError): TensorNetwork(-1, ())


def test_ring_random_differential_and_inverses():
    rng = random.Random(4317)
    for p, f, ell in product((1, 2, 5), (2, 3, 7, 11), (1, 2, 3)):
        ring = Ring(p, f, ell)
        degree = f.bit_length()-1
        for _ in range(20):
            a = ring.element([[rng.randrange(-20, 20) for _ in range(degree)] for _ in range(ell)])
            b = ring.element([[rng.randrange(-20, 20) for _ in range(degree)] for _ in range(ell)])
            assert (a*b).coefficients == independent_product(a.coefficients, b.coefficients, p, f, ell)
            assert a*(b+ring.one) == a*b+a
            if any(x & 1 for x in a.coefficients[0]):
                assert a*a.inverse() == ring.one
            else:
                with pytest.raises(ZeroDivisionError): a.inverse()


def test_precision_and_polynomial_contract():
    r = Ring(6, 7, 2)
    a = r.element(((17, 2), (4, 8)))
    assert a.creation_precision == 6 and a.valuation() == 0
    low = a.reduce_precision(3)
    assert low.creation_precision == 6 and low.coefficients == ((1, 2), (4, 0))
    with pytest.raises(ValueError): low.reduce_precision(4)
    with pytest.raises(ValueError): a + low
    with pytest.raises(ValueError): Element(r, ((0,),), 6)
    with pytest.raises(ValueError): r.element(((1.2,),))
    for args in ((0, 7, 1), (6, 5, 1), (6, 7, 0), (6, 7, 65)):
        with pytest.raises(ValueError): Ring(*args)
    x = Polynomial(r, (a, r.one))
    y = Polynomial(r, (r.one, a, r.one))
    assert (x*y).evaluate(a) == x.evaluate(a)*y.evaluate(a)
    assert r.zero.valuation() == 6
    with pytest.raises(ZeroDivisionError): r.integer(2).inverse()


def test_cauchy_cancellation_and_shift_integrality():
    # Independent product at integer points, including removable roots.
    for L in (1, 2, 4):
        entries = cauchy_matrix_polynomials(L)
        denom = 1
        for z in range(-L, L):
            if z: denom *= -z
        ring = ExtensionRing(7, 7)
        for x in range(L):
            for y in range(L):
                poly = entries[x][y]
                for t in range(-L, L):
                    numerator = 1
                    for z in range(-L, L):
                        if z != y-x: numerator *= t-z
                    assert sum(c*t**i for i, c in enumerate(poly)) == Fraction(numerator, denom)
                    shifted = shift_cauchy_entry(L, t, ring, x, y)
                    for s in (-1, 0, 1):
                        value = sum(c*(t+2*L*s)**i for i, c in enumerate(poly))
                        modular = sum(c[0]*s**i for i, c in enumerate(shifted)) % ring.modulus
                        assert modular == fraction_to_ring(ring, value)[0]
        with pytest.raises(ValueError): fraction_to_ring(ring, Fraction(1, 2))


def test_scope_report_cannot_be_promoted_by_mutating_result():
    from veritas.research.math_exact.status import execution_status
    a = execution_status()
    a['components']['theorem_recursion'] = 'PROVEN'
    b = execution_status()
    assert b['components']['theorem_recursion'] == 'NOT_IMPLEMENTED'
    assert b['components']['legacy_function_inventory'] == 'INCOMPLETE'
    assert b['universal_theorem_proven'] is False


def test_small_ring_units_against_exhaustive_independent_products():
    # All 256 elements of (Z/4)[U,V]/(U²+U+1,V²).
    ring = Ring(2, 7, 2)
    rows = list(product(range(4), repeat=2))
    values = [ring.element((a, b)) for a, b in product(rows, repeat=2)]
    one = ring.one.coefficients
    for value in values:
        witnesses = [candidate for candidate in values
                     if independent_product(value.coefficients, candidate.coefficients, 2, 7, 2) == one]
        if witnesses:
            assert len(witnesses) == 1
            assert value.inverse().coefficients == witnesses[0].coefficients
        else:
            with pytest.raises(ZeroDivisionError): value.inverse()
