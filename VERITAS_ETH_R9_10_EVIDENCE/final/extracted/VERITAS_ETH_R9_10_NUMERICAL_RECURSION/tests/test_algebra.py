from fractions import Fraction
import itertools
import random
from veritas.research.algebra import (clause_indicator, parity_indicator, two_adic_valuation,
    omit_if_zero_mod, mobius_coefficients, eval_multilinear, hermite_coefficients, polynomial_derivative_eval)


def test_parity_full_small():
    for p in range(1, 10):
        for y in range(-40,41):
            assert parity_indicator(p,y) == (1 if y % 2 == 0 else 0)


def test_two_adic():
    assert two_adic_valuation(0) is None
    assert two_adic_valuation(-24) == 3
    assert two_adic_valuation(17) == 0
    assert omit_if_zero_mod(64, 6) == 0
    assert omit_if_zero_mod(63, 6) == 63


def test_mobius_reconstruct():
    rng = random.Random(19)
    for n in range(0,7):
        values = [rng.randint(-4,7) for _ in range(1<<n)]
        coeffs = mobius_coefficients(values)
        for mask in range(1<<n):
            bits = tuple(bool(mask & (1<<i)) for i in range(n))
            assert eval_multilinear(coeffs, bits) == values[mask]


def test_hermite():
    # f(x) = 3-2x+4x^2+x^3 ; f'(x)=-2+8x+3x^2
    coeffs = hermite_coefficients([(0,[3,-2]),(2,[23,26])])
    assert coeffs == [3,-2,4,1]
    assert polynomial_derivative_eval(coeffs,2,1) == 26
    assert hermite_coefficients([(1,[5])]) == [Fraction(5)]


def test_clause_indicators():
    for x, y in itertools.product([False,True],repeat=2):
        expected = int(x or not y)
        assert clause_indicator((1,-2), {1:x,2:y}) == expected
