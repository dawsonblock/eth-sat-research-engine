import unittest
from fractions import Fraction

from eth_sat.measurements import (
    Factor,
    LinearMeasurements,
    SharedMeasurementProblem,
    cnf_shared_measurement_count,
    shared_measurement_count,
    shared_measurement_sum,
)
from eth_sat.model import CNF
from eth_sat.verifier import (
    row_space_contains,
    row_space_coordinates,
    verify_measurement_bounds,
    verify_replacement_rowspaces,
)
from eth_sat.truncated import TruncatedPolynomial


class MeasurementTests(unittest.TestCase):
    def test_rational_row_space_membership(self):
        self.assertTrue(row_space_contains(((1, 1),), (Fraction(1, 2), Fraction(1, 2))))
        self.assertFalse(row_space_contains(((1, 1),), (1, 0)))
        self.assertTrue(row_space_contains((), (0, 0)))

    def test_exact_row_space_coordinates(self):
        matrix = ((1, 0, 1), (0, 1, 1))
        coefficients = row_space_coordinates(matrix, (Fraction(1, 2), 2, Fraction(5, 2)))
        self.assertEqual(coefficients, (Fraction(1, 2), Fraction(2)))
        self.assertIsNone(row_space_coordinates(matrix, (1, 1, 3)))
        self.assertEqual(row_space_coordinates((), (0, 0)), ())

    def test_replacement_rowspace_verifier_reports_kernel_dependency(self):
        issues = verify_replacement_rowspaces(
            groups=((0,), (1,)),
            measurement_matrices=((), ()),
            factor_owners=(0,),
            replacement_rows=(((1, 1),),),
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].group, 1)

    def test_measurement_budget_checks_l1_and_row_count(self):
        errors = verify_measurement_bounds((((1, -2),), ((3,),)), max_row_l1=2, max_total_rows=1)
        self.assertEqual(len(errors), 3)
        self.assertEqual(verify_measurement_bounds((((1, -1),),), 2, 1), ())

    def test_shared_factorization_and_cnf_adapter(self):
        problem = SharedMeasurementProblem(
            num_variables=2,
            groups=((0,), (1,)),
            measurements=(LinearMeasurements(((1,),), 1), LinearMeasurements(((1,),), 1)),
            factors=(Factor(0, lambda local, summaries: int(local[0] == summaries[1][0])),),
        )
        self.assertEqual(shared_measurement_count(problem), Fraction(2))
        formula = CNF.from_signed_clauses(3, ((1, 2), (-1, 3)))
        self.assertEqual(cnf_shared_measurement_count(formula, group_size=1), 4)

    def test_shared_sum_supports_truncated_polynomials_and_fixed_bits(self):
        problem = SharedMeasurementProblem(
            num_variables=2,
            groups=((0,), (1,)),
            measurements=(LinearMeasurements(((1,),), 1), LinearMeasurements(((1,),), 1)),
            factors=(
                Factor(
                    0,
                    lambda local, summaries: TruncatedPolynomial.constant(
                        int(local[0] == summaries[1][0]), 3
                    ),
                ),
            ),
        )
        self.assertEqual(
            shared_measurement_sum(problem),
            TruncatedPolynomial.constant(2, 3),
        )
        self.assertEqual(
            shared_measurement_sum(problem, fixed_ones=(0,)),
            TruncatedPolynomial.constant(1, 3),
        )
        with self.assertRaisesRegex(ValueError, "outside"):
            shared_measurement_sum(problem, fixed_ones=(2,))


if __name__ == "__main__":
    unittest.main()
