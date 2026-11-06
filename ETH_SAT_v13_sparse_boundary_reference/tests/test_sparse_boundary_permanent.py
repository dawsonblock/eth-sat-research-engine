from fractions import Fraction
import unittest
from math import nan

from ETH_SAT_v13_sparse_boundary_reference import (
    PermanentResourceLimit,
    brute_force_permanent_polynomial,
    self_test,
    sparse_boundary_permanent_coefficients,
)


class SparseBoundaryPermanentTests(unittest.TestCase):
    def test_full_seeded_validation(self):
        result = self_test()
        self.assertEqual(result['randomized_differential']['cases'], 330)
        self.assertEqual(result['bundled_example']['coefficients'], ['1', '0', '61', '144'])
        self.assertEqual(result['large_cycle_case']['permanent_at_one'], '441')

    def test_fractional_entries_and_single_block(self):
        matrix = ((Fraction(1, 2), 1), (3, Fraction(-2, 3)))
        labels = (0, 1)
        result = sparse_boundary_permanent_coefficients(matrix, labels)
        self.assertEqual(result.coefficients,
                         (Fraction(-1, 3), Fraction(0), Fraction(3)))
        self.assertEqual(result.permanent_at_one, Fraction(8, 3))
        self.assertEqual(result.coefficients,
                         brute_force_permanent_polynomial(matrix, labels))

    def test_empty_permanent(self):
        result = sparse_boundary_permanent_coefficients((), ())
        self.assertEqual(result.coefficients, (Fraction(1),))
        self.assertEqual(result.permanent_at_one, Fraction(1))

    def test_nonreflexive_hashable_labels_are_normalized_once(self):
        label = nan
        matrix = ((1, 2), (3, 4))
        result = sparse_boundary_permanent_coefficients(matrix, (label, label))
        self.assertEqual(result.cross_entries, 0)
        self.assertEqual(result.coefficients, (Fraction(10),))
        self.assertEqual(result.coefficients,
                         brute_force_permanent_polynomial(matrix, (label, label)))

    def test_nonexact_and_malformed_inputs_rejected(self):
        with self.assertRaises(TypeError):
            sparse_boundary_permanent_coefficients(((1.0,),), (0,))
        with self.assertRaises(ValueError):
            sparse_boundary_permanent_coefficients(((1, 2),), (0,))
        with self.assertRaises(ValueError):
            sparse_boundary_permanent_coefficients(((1,),), ())

    def test_resource_caps_fail_closed(self):
        matrix = ((1, 2), (3, 1))
        with self.assertRaises(PermanentResourceLimit):
            sparse_boundary_permanent_coefficients(
                matrix, (0, 1), max_cross_entries=1)
        with self.assertRaises(PermanentResourceLimit):
            sparse_boundary_permanent_coefficients(
                matrix, (0, 1), max_arithmetic_operations=1)
        with self.assertRaises(PermanentResourceLimit):
            sparse_boundary_permanent_coefficients(
                matrix, (0, 1), max_dp_state_visits=10)
        with self.assertRaises(PermanentResourceLimit):
            sparse_boundary_permanent_coefficients(
                matrix, (0, 1), max_dp_transition_scans=1)
        with self.assertRaises(PermanentResourceLimit):
            sparse_boundary_permanent_coefficients(
                ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0, 1, 2),
                max_dimension=2)


if __name__ == '__main__':
    unittest.main()
