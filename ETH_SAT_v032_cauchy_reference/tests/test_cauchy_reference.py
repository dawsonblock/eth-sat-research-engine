from fractions import Fraction
import unittest

from ETH_SAT_v032_cauchy_reference import (
    ReferenceLimit,
    deformed_packet_contraction_polynomial,
    expand_crossing_entry_mod,
    local_coordinate_series,
    make_cauchy_packet,
    self_test,
    two_group_mode_contraction,
)
from tapered_hermite import (
    HermiteInputError,
    integer_polynomial_jets,
    make_tapered_schedule,
    recover_tapered_hermite,
    validate_tapered_hermite_reference,
)


class CauchyReferenceTests(unittest.TestCase):
    def test_full_small_reference_validation(self):
        result = self_test()
        self.assertEqual(result['packet_sizes_checked'], list(range(1, 9)))
        self.assertEqual(result['grid_nodes_checked'], 72)
        self.assertEqual(result['rational_kernel_formula_entry_checks'], 408)
        self.assertEqual(result['deformed_contraction_identity']['cases'], 24)
        self.assertEqual(
            result['crossing_mode_expansion']['crossing_entry_expansions_checked'], 7440)
        self.assertEqual(result['two_group_mode_factorization']['cases'], 16)
        self.assertEqual(result['tapered_hermite_recovery']['cases'], 25)
        self.assertTrue(result['tapered_hermite_reconstruction_implemented'])
        self.assertFalse(result['full_recursive_modular_mode_pruning_implemented'])
        self.assertFalse(result['recursive_child_contraction_implemented'])

    def test_packet_grid_support_and_exact_rational_coefficients(self):
        packet = make_cauchy_packet(4)
        self.assertEqual(packet.derivative_at_zero, Fraction(-144))
        for node in packet.grid:
            matrix = packet.evaluate(node)
            self.assertTrue(all(
                matrix[x][y] == 0 for x in range(4) for y in range(4)
                if y - x != node))
        self.assertEqual(packet.evaluate(0), tuple(
            tuple(Fraction(int(x == y)) for y in range(4)) for x in range(4)))
        series = local_coordinate_series(packet, -3)
        self.assertTrue(all(coefficient.denominator % 2 == 1
                            for row in series for poly in row for coefficient in poly))

    def test_single_crossing_geometric_expansion(self):
        packet = make_cauchy_packet(8)
        result = expand_crossing_entry_mod(
            packet, node=-3, row=0, tile_base=0, tile_index=1,
            z=1, precision=8)
        self.assertEqual(result.direct_residue, result.mode_sum_residue)
        self.assertEqual(result.number_of_modes, 7)
        self.assertGreaterEqual(result.minimum_coefficient_valuation, 1)

    def test_exhaustive_packet_reference_fails_closed_at_cap(self):
        packet = make_cauchy_packet(2)
        table = (1, 1, 1, 1)
        with self.assertRaises(ReferenceLimit):
            deformed_packet_contraction_polynomial(
                packet, table, table, max_exhaustive_packet_size=1)

        large_packet = make_cauchy_packet(16)
        with self.assertRaises(ReferenceLimit):
            two_group_mode_contraction(
                large_packet, node=-1, z=0, precision=2,
                row_unary=((1, 1),) * 16, column_unary=((1, 1),) * 16)

    def test_tapered_schedule_matches_precision_and_multiplicity_formulas(self):
        schedule = make_tapered_schedule(8, M=5, u=3, target_precision=7)
        self.assertEqual(schedule.a, 3)
        self.assertEqual(schedule.h, 5)
        self.assertEqual(schedule.degree_bound, 75)
        self.assertGreater(schedule.total_multiplicity, schedule.degree_bound)
        for node in schedule.active_nodes:
            level = abs(node & -node).bit_length() - 1
            self.assertEqual(schedule.multiplicity(node), 5 * (3 - level))
            self.assertEqual(
                schedule.precision(node),
                7 + 8 * 5 * (8 >> level) + 8 * 5 * 4)

    def test_tapered_hermite_exhaustive_degree_three_polynomials(self):
        schedule = make_tapered_schedule(2, M=1, u=1, target_precision=3)

        def visit(prefix):
            if len(prefix) == schedule.degree_bound + 1:
                coefficients = tuple((value,) for value in prefix)
                jets = integer_polynomial_jets(coefficients, schedule)
                self.assertEqual(
                    recover_tapered_hermite(schedule, jets),
                    (prefix[0] % (1 << schedule.target_precision),))
                return
            for value in (-1, 0, 1):
                visit(prefix + (value,))

        visit(())

    def test_tapered_hermite_random_vector_polynomials(self):
        result = validate_tapered_hermite_reference(cases=25)
        self.assertEqual(result['cases'], 25)
        self.assertEqual(result['coefficient_dimensions'], 3)
        self.assertGreater(result['max_local_precision_bits'], 1024)

    def test_tapered_hermite_rejects_bad_schedule_and_jets(self):
        with self.assertRaises(HermiteInputError):
            make_tapered_schedule(6, M=2, u=1, target_precision=3)
        schedule = make_tapered_schedule(2, M=1, u=1, target_precision=2)
        with self.assertRaises(HermiteInputError):
            recover_tapered_hermite(schedule, {})


if __name__ == '__main__':
    unittest.main()
