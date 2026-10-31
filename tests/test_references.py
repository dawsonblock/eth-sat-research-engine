import random
import unittest

from eth_sat.algebraic import algebraic_count, grouped_count
from eth_sat.measurements import cnf_shared_measurement_count
from eth_sat.model import CNF
from eth_sat.references import dpll_count, exhaustive_count


class ReferenceTests(unittest.TestCase):
    def test_dpll_counts_free_variables_and_empty_clause(self):
        self.assertEqual(dpll_count(CNF(4, ())), 16)
        self.assertEqual(dpll_count(CNF.from_signed_clauses(2, ((),))), 0)

    def test_dpll_matches_exhaustive_on_random_formulas(self):
        rng = random.Random(44017)
        for _ in range(25):
            n = rng.randint(1, 5)
            clauses = []
            for _ in range(rng.randint(0, 8)):
                clauses.append(
                    tuple(
                        (1 if rng.randrange(2) else -1) * rng.randint(1, n)
                        for _ in range(rng.randint(0, 3))
                    )
                )
            formula = CNF.from_signed_clauses(n, clauses)
            self.assertEqual(dpll_count(formula), exhaustive_count(formula))

    def test_all_engines_match_on_random_small_formulas(self):
        rng = random.Random(9122026)
        for _ in range(8):
            n = rng.randint(1, 5)
            clauses = [
                tuple(
                    (1 if rng.randrange(2) else -1) * rng.randint(1, n)
                    for _ in range(rng.randint(0, 3))
                )
                for _ in range(rng.randint(0, 7))
            ]
            formula = CNF.from_signed_clauses(n, clauses)
            expected = exhaustive_count(formula)
            self.assertEqual(dpll_count(formula), expected)
            self.assertEqual(algebraic_count(formula, node_count=2).count, expected)
            self.assertEqual(cnf_shared_measurement_count(formula, group_size=2), expected)
            self.assertEqual(grouped_count(formula, group_size=2), expected)


if __name__ == "__main__":
    unittest.main()
