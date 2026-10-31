import unittest
from fractions import Fraction

from eth_sat.spectral import (
    SpectralParameters,
    build_spectral_reference,
    local_eigenbasis,
)
from eth_sat.verifier import row_space_contains
from eth_sat.verifier import matrix_rank


class SpectralReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = build_spectral_reference(2, 3, 2)

    def test_local_swap_eigenbasis_is_orthogonal_and_complete(self):
        basis = local_eigenbasis(3)
        self.assertEqual(len(basis), 9)
        dense = []
        for vector in basis:
            entries = dict(vector.entries)
            dense.append(
                tuple(entries.get((a, b), 0) for a in range(3) for b in range(3))
            )
            swapped = tuple(
                (b, a, coefficient)
                for (a, b), coefficient in vector.entries
            )
            swapped_map = {(a, b): coefficient for a, b, coefficient in swapped}
            self.assertEqual(
                swapped_map,
                {pair: vector.eigenvalue * coefficient for pair, coefficient in vector.entries},
            )
        for i, left in enumerate(dense):
            for right in dense[i + 1 :]:
                self.assertEqual(sum(a * b for a, b in zip(left, right)), 0)

    def test_m0_has_the_expected_spectral_action(self):
        self.assertEqual(self.reference.parameters.interval, (0, 1))
        self.assertTrue(self.reference.verify_eigenbasis())
        for vector in self.reference.eigenbasis:
            if vector.negative_count in self.reference.parameters.interval:
                self.assertEqual(
                    self.reference.f[0]
                    + sum(
                        coefficient * vector.negative_count**degree
                        for degree, coefficient in enumerate(self.reference.f[1:], start=1)
                    ),
                    Fraction((-1) ** vector.negative_count),
                )

    def test_partial_swap_support_is_bounded_by_degree_window(self):
        self.assertTrue(self.reference.verify_partial_swap_support())
        self.assertTrue(
            all(mask.bit_count() <= self.reference.parameters.degree_window - 1
                for mask, _ in self.reference.partial_swap_terms)
        )

    def test_replacement_rows_restore_coordinates_and_respect_degree(self):
        errors = self.reference.verify_replacement_identities()
        self.assertEqual(errors, ())
        for row_index in (0, 17, 63):
            row = self.reference.replacement_row(row_index)
            at_zero = tuple(polynomial[0] for polynomial in row)
            expected = tuple(
                Fraction(int(column == row_index))
                for column in range(self.reference.dimension)
            )
            self.assertEqual(at_zero, expected)
            self.assertTrue(
                all(len(polynomial) <= self.reference.parameters.degree_window
                    for polynomial in row)
            )

    def test_measurement_rows_span_correction_and_local_terms_stay_local(self):
        self.assertEqual(self.reference.verify_measurement_rowspace(), ())
        self.assertEqual(
            matrix_rank(self.reference.measurements, width=self.reference.dimension),
            len(self.reference.measurements),
        )
        for row_index in (0, 17, 42, 63):
            measurement_row, local_row = self.reference.replacement_components(row_index)
            self.assertTrue(
                row_space_contains(self.reference.measurements, measurement_row)
            )
            owner = self.reference.coordinates[row_index]
            for point_index in range(self.reference.parameters.q):
                for column, polynomial in enumerate(local_row):
                    point = Fraction(point_index + 1)
                    value = sum(
                        coefficient * point**degree
                        for degree, coefficient in enumerate(polynomial)
                    )
                    if value:
                        candidate = self.reference.coordinates[column]
                        self.assertEqual(
                            candidate[point_index][0], owner[point_index][1]
                        )

    def test_dense_dimension_guard_and_parameter_validation(self):
        with self.assertRaisesRegex(ValueError, "exceeds dense reference limit"):
            build_spectral_reference(2, 4, 2)
        with self.assertRaisesRegex(ValueError, "exceeds dense reference limit"):
            build_spectral_reference(2, 1_000_000, 1)
        with self.assertRaisesRegex(ValueError, "1 <= R < Q"):
            SpectralParameters(2, 3, 3)
        with self.assertRaisesRegex(ValueError, "interval"):
            SpectralParameters(2, 3, 2, interval_start=3)


if __name__ == "__main__":
    unittest.main()
