import unittest
from fractions import Fraction

from eth_sat.polynomial import (
    add,
    evaluate,
    hermite_interpolate,
    multiply,
    taylor_coefficients,
)


class PolynomialTests(unittest.TestCase):
    def test_exact_polynomial_arithmetic(self):
        p = (Fraction(1), Fraction(2))
        q = (Fraction(-1), Fraction(1))
        self.assertEqual(add(p, q), (Fraction(0), Fraction(3)))
        self.assertEqual(multiply(p, q), (Fraction(-1), Fraction(-1), Fraction(2)))
        self.assertEqual(evaluate(multiply(p, q), 2), 5)

    def test_taylor_coefficients_are_coefficients_not_derivatives(self):
        p = (Fraction(1), Fraction(2), Fraction(3))
        self.assertEqual(
            taylor_coefficients(p, 2, 3),
            (Fraction(17), Fraction(14), Fraction(3)),
        )

    def test_hermite_interpolation_from_distinct_nodes(self):
        original = (Fraction(2), Fraction(-3), Fraction(1))
        jets = (
            taylor_coefficients(original, 0, 2),
            taylor_coefficients(original, 1, 2),
        )
        self.assertEqual(hermite_interpolate((0, 1), jets), original)

    def test_hermite_interpolation_with_redundant_jet_data(self):
        original = (Fraction(4), Fraction(0), Fraction(2))
        jets = (taylor_coefficients(original, -1, 3), taylor_coefficients(original, 2, 3))
        self.assertEqual(hermite_interpolate((-1, 2), jets), original)

    def test_hermite_rejects_duplicate_nodes(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            hermite_interpolate((1, 1), ((2,), (3,)))


if __name__ == "__main__":
    unittest.main()
