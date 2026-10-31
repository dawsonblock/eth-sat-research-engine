import unittest
from fractions import Fraction

from eth_sat.algebraic import algebraic_count, grouped_count, replacement_row
from eth_sat.examples import simple
from eth_sat.model import CNF, Literal
from eth_sat.polynomial import evaluate
from eth_sat.references import exhaustive_count


class AlgebraicTests(unittest.TestCase):
    def test_replacement_row_is_original_coordinate_at_zero(self):
        row = replacement_row(3, 0, 0, Literal(2))
        self.assertEqual(tuple(evaluate(entry, 0) for entry in row), (0, 1, 0))

    def test_algebraic_interpolation_example_count(self):
        result = algebraic_count(simple(), node_count=3)
        self.assertEqual(result.count, 4)
        self.assertGreaterEqual(len(result.interpolation_nodes) * result.jet_order, result.transformed_degree + 1)

    def test_tautology_and_empty_clause(self):
        tautology = CNF.from_signed_clauses(1, ((1, -1),))
        contradiction = CNF.from_signed_clauses(1, ((),))
        self.assertEqual(algebraic_count(tautology).count, 2)
        self.assertEqual(algebraic_count(contradiction).count, 0)

    def test_grouped_factor_counter_matches_truth_table(self):
        formula = simple()
        self.assertEqual(grouped_count(formula, group_size=1), exhaustive_count(formula))


if __name__ == "__main__":
    unittest.main()
