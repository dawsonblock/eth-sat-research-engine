import random
import unittest

from eth_sat.bivariate import BivariateTruncatedPolynomial
from eth_sat.common_zeros import (
    common_zero_count,
    count_sparse_polynomial_zeros,
    exhaustive_common_zero_count,
    parity_indicator_components,
)
from eth_sat.model import CNF
from eth_sat.references import dpll_count
from eth_sat.sparse import F2Polynomial, SparsePolynomialSystem
from eth_sat.truncated import TruncatedPolynomial


class SparseCommonZeroTests(unittest.TestCase):
    def test_f2_polynomial_uses_boolean_squarefree_arithmetic(self):
        x0 = F2Polynomial(2, ((0,),))
        x1 = F2Polynomial(2, ((1,),))
        self.assertEqual((x0 * x0), x0)
        self.assertEqual((x0 + x0), F2Polynomial.zero(2))
        self.assertEqual((x0 * x1).monomials, ((0, 1),))
        self.assertEqual(F2Polynomial(2, ((), (0,))).evaluate((1, 0)), 0)

    def test_cnf_violation_system_has_the_same_satisfying_assignments(self):
        rng = random.Random(710031)
        for _ in range(8):
            n = rng.randint(1, 4)
            clauses = [
                tuple(
                    (1 if rng.randrange(2) else -1) * rng.randint(1, n)
                    for _ in range(rng.randint(0, 3))
                )
                for _ in range(rng.randint(0, 5))
            ]
            formula = CNF.from_signed_clauses(n, clauses)
            system = SparsePolynomialSystem.from_cnf(formula)
            count = sum(
                system.evaluate(tuple((mask >> i) & 1 for i in range(n)))
                for mask in range(1 << n)
            )
            self.assertEqual(count, dpll_count(formula))

    def test_integer_parity_indicator_decomposition(self):
        for ell in range(1, 7):
            components = parity_indicator_components(ell)
            self.assertEqual(len(components), ell)
            for value in range(16):
                polynomial_value = sum(
                    (a + b * value) * (value * value - value) ** degree
                    for degree, (a, b) in enumerate(components)
                )
                expected = int(value % 2 == 0)
                self.assertEqual((polynomial_value - expected) % (1 << ell), 0)

    def test_bivariate_truncation_and_final_v_sum(self):
        z = TruncatedPolynomial.from_coefficients((1, 1, 0), 3)
        v0 = BivariateTruncatedPolynomial.from_z_polynomial(z, 2)
        v1 = BivariateTruncatedPolynomial.from_z_polynomial(z, 2, v_degree=1)
        product = v1 * v1
        self.assertFalse(product)
        value = v0 + v1
        self.assertEqual(value.sum_over_v(), z * 2)

    def test_common_zero_counter_matches_exhaustive_small_systems(self):
        systems = (
            SparsePolynomialSystem.from_monomials(2, (((0,), (1,)),)),
            SparsePolynomialSystem.from_monomials(2, (((0, 1), (0,), (1,)),)),
            SparsePolynomialSystem.from_monomials(2, (((0,),), ((1,),))),
            SparsePolynomialSystem.from_monomials(3, (((0, 1), (2,)), ((0,), (1,))))
        )
        for system in systems:
            result = common_zero_count(system)
            self.assertEqual(result.count, exhaustive_common_zero_count(system))
            self.assertEqual(result.residue, result.count)

    def test_sparse_system_outer_counter_uses_exact_small_fallback(self):
        system = SparsePolynomialSystem.from_monomials(
            4, (((0, 1), (2,)), ((1,), (3,)))
        )
        result = count_sparse_polynomial_zeros(system)
        self.assertTrue(result.used_exhaustive_fallback)
        self.assertEqual(result.count, exhaustive_common_zero_count(system))

    def test_empty_and_constant_inconsistent_systems(self):
        self.assertEqual(
            count_sparse_polynomial_zeros(SparsePolynomialSystem(3, ())).count,
            8,
        )
        impossible = SparsePolynomialSystem.from_monomials(3, ((((),),)))
        self.assertEqual(count_sparse_polynomial_zeros(impossible).count, 0)


if __name__ == "__main__":
    unittest.main()
