import unittest

from eth_sat.model import CNF, Literal


class ModelTests(unittest.TestCase):
    def test_literal_polarity(self):
        self.assertTrue(Literal(1).value(1))
        self.assertFalse(Literal(1).value(0))
        self.assertTrue(Literal(1, True).value(0))
        self.assertFalse(Literal(1, True).value(1))

    def test_satisfaction_and_declared_variables(self):
        formula = CNF.from_signed_clauses(3, ((1, -2),))
        self.assertTrue(formula.is_satisfied((1, 0, 0)))
        self.assertFalse(formula.is_satisfied((0, 1, 1)))
        with self.assertRaises(ValueError):
            formula.is_satisfied((1, 0))
        with self.assertRaises(ValueError):
            CNF.from_signed_clauses(1, ((2,),))

    def test_dimacs_round_trip_and_empty_clause(self):
        formula = CNF.from_signed_clauses(3, ((), (1, -2)))
        parsed = CNF.from_dimacs(formula.to_dimacs())
        self.assertEqual(parsed, formula)
        self.assertEqual(parsed.clauses[0], ())

    def test_dimacs_rejects_bad_clause_count_and_missing_zero(self):
        with self.assertRaisesRegex(ValueError, "declares"):
            CNF.from_dimacs("p cnf 1 2\n1 0\n")
        with self.assertRaisesRegex(ValueError, "missing its terminating zero"):
            CNF.from_dimacs("p cnf 1 1\n1\n")


if __name__ == "__main__":
    unittest.main()
