import unittest
import random
from fractions import Fraction

from eth_sat.examples import simple
from eth_sat.layout import build_spectral_cnf_layout, verify_spectral_cnf_layout
from eth_sat.model import CNF
from eth_sat.polynomial import taylor_coefficients
from eth_sat.references import dpll_count
from eth_sat.taylor import direct_spectral_sum_polynomial, spectral_taylor_count


class TaylorEvaluationTests(unittest.TestCase):
    def test_taylor_jets_match_direct_polynomial_and_dpll(self):
        layout = build_spectral_cnf_layout(
            simple(), r=2, q=3, degree_window=2
        )
        self.assertEqual(verify_spectral_cnf_layout(layout), ())
        direct = direct_spectral_sum_polynomial(layout)
        result = spectral_taylor_count(layout)
        self.assertEqual(result.count, dpll_count(simple()))
        self.assertEqual(result.count, 4)
        for node, jet in zip(result.nodes, result.jets):
            expected = taylor_coefficients(direct, node, result.jet_order)
            expected += (Fraction(0),) * (result.jet_order - len(expected))
            self.assertEqual(jet, expected)

    def test_duplicate_literals_and_tautologies_are_normalized_safely(self):
        formula = CNF.from_signed_clauses(2, ((1, 1, -1), (2, 2)))
        layout = build_spectral_cnf_layout(
            formula, r=2, q=3, degree_window=2
        )
        self.assertIsNone(layout.factor_literals[0])
        result = spectral_taylor_count(layout)
        self.assertEqual(result.count, 2)
        self.assertEqual(result.count, dpll_count(formula))
        direct = direct_spectral_sum_polynomial(layout)
        self.assertEqual(direct[0], Fraction(2))

    def test_taylor_subset_guard_stops_unbounded_small_engine_work(self):
        formula = CNF.from_signed_clauses(
            5, ((1, 2, 3), (2, 3, 4), (3, 4, 5), (1, 4, 5))
        )
        layout = build_spectral_cnf_layout(
            formula, r=2, q=2, degree_window=1
        )
        with self.assertRaisesRegex(ValueError, "pairs"):
            spectral_taylor_count(layout, max_substitution_pairs=1)

    def test_random_tiny_formulas_match_direct_jets_and_dpll(self):
        rng = random.Random(20261031)
        for case in range(6):
            n = rng.randint(1, 3)
            clauses = [
                tuple(
                    (1 if rng.randrange(2) else -1) * rng.randint(1, n)
                    for _ in range(rng.randint(0, 3))
                )
                for _ in range(rng.randint(0, 5))
            ]
            formula = CNF.from_signed_clauses(n, clauses)
            layout = build_spectral_cnf_layout(
                formula, r=2, q=2, degree_window=1
            )
            direct = direct_spectral_sum_polynomial(layout)
            result = spectral_taylor_count(layout)
            with self.subTest(case=case, clauses=clauses):
                self.assertEqual(result.count, dpll_count(formula))
                for node, jet in zip(result.nodes, result.jets):
                    expected = taylor_coefficients(direct, node, result.jet_order)
                    expected += (Fraction(0),) * (result.jet_order - len(expected))
                    self.assertEqual(jet, expected)

    def test_zero_variable_empty_and_false_formulas(self):
        for clauses, expected in (((), 1), (((),), 0)):
            formula = CNF.from_signed_clauses(0, clauses)
            layout = build_spectral_cnf_layout(
                formula, r=2, q=2, degree_window=1
            )
            result = spectral_taylor_count(layout)
            self.assertEqual(result.count, expected)
            self.assertEqual(result.count, dpll_count(formula))

    def test_layout_checks_dense_dimension_before_schedule_generation(self):
        formula = CNF.from_signed_clauses(1, ((1,),))
        with self.assertRaisesRegex(ValueError, "exceeds dense reference limit"):
            build_spectral_cnf_layout(
                formula, r=2, q=1_000_000, degree_window=1
            )


if __name__ == "__main__":
    unittest.main()
