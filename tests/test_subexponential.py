from __future__ import annotations

import unittest

from eth_sat.model import CNF
from eth_sat.references import dpll_count
from eth_sat.reductions import (
    iter_sparsified_leaves,
    reduce_to_three_occurrence_cnf,
    to_3cnf_with_unique_extensions,
)
from eth_sat.subexponential import (
    build_initial_parity_checks,
    count_sparse_formula,
    count_subexponential,
)


class SubexponentialPipelineTests(unittest.TestCase):
    def test_sparse_formula_direct_equations_match_dpll(self) -> None:
        formula = CNF.from_signed_clauses(
            4, ((1, -2), (2, 3), (-3, 4))
        )
        result = count_sparse_formula(formula)
        self.assertEqual(result.count, dpll_count(formula))
        self.assertEqual(result.common_zero_queries, 1)
        self.assertEqual(result.parity_checks, 0)

    def test_tanner_initial_checks_are_bounded_and_deterministic(self) -> None:
        formula = CNF.from_signed_clauses(
            2, ((1, 2), (-1, 2), (1, -2))
        )
        first = build_initial_parity_checks(formula)
        second = build_initial_parity_checks(formula)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 3 * formula.num_variables)
        self.assertTrue(all(len(row) <= len(formula.clauses) for row in first))

    def test_greedy_parity_compression_counts_overfull_clause_family(self) -> None:
        formula = CNF.from_signed_clauses(
            2, ((1, 2), (-1, 2), (1, -2))
        )
        result = count_sparse_formula(formula)
        self.assertEqual(result.count, 1)
        self.assertEqual(result.count, dpll_count(formula))
        self.assertEqual(result.parity_checks, 3 * formula.num_variables)
        self.assertGreater(result.common_zero_queries, 0)

    def test_sparsification_leaves_partition_assignments(self) -> None:
        formula = CNF.from_signed_clauses(
            4, ((1, 2), (1, 3), (1, 4), (-1, 2), (-1, 3))
        )
        leaves = tuple(iter_sparsified_leaves(formula, k=2, sigma=1))
        self.assertGreaterEqual(len(leaves), 1)
        self.assertEqual(sum(dpll_count(leaf) for leaf in leaves), dpll_count(formula))

    def test_count_preserving_three_cnf_and_occurrence_copying(self) -> None:
        formula = CNF.from_signed_clauses(5, ((1, 2, 3, 4, 5), (-1, -2, 3, 4)))
        three_cnf = to_3cnf_with_unique_extensions(formula)
        bounded = reduce_to_three_occurrence_cnf(formula)
        self.assertEqual(dpll_count(three_cnf), dpll_count(formula))
        self.assertEqual(dpll_count(bounded), dpll_count(formula))
        self.assertTrue(all(len(clause) <= 3 for clause in bounded.clauses))
        occurrences = [0] * bounded.num_variables
        for clause in bounded.clauses:
            for literal in clause:
                occurrences[literal.variable - 1] += 1
        self.assertLessEqual(max(occurrences, default=0), 3)

    def test_general_entrypoint_uses_exact_finite_size_fallback(self) -> None:
        formula = CNF.from_signed_clauses(3, ((1, -2), (2, 3)))
        result = count_subexponential(formula)
        self.assertTrue(result.used_finite_size_fallback)
        self.assertEqual(result.count, dpll_count(formula))

    def test_forced_sparsification_runs_the_full_pipeline_on_tiny_input(self) -> None:
        formula = CNF.from_signed_clauses(
            2, ((1, 2), (-1, 2), (1, -2))
        )
        result = count_subexponential(formula, sparsification_sigma=1)
        self.assertEqual(result.count, dpll_count(formula))
        self.assertFalse(result.used_finite_size_fallback)
        self.assertGreaterEqual(result.leaves_processed, 1)

    def test_all_unit_formula_uses_valid_sparsification_width(self) -> None:
        formula = CNF.from_signed_clauses(3, ((1,), (-2,), (3,)))
        result = count_subexponential(formula, sparsification_sigma=1)
        self.assertEqual(result.max_clause_width, 2)
        self.assertEqual(result.count, dpll_count(formula))

    def test_finite_size_fallback_guard_is_explicit(self) -> None:
        formula = CNF.from_signed_clauses(30, ((1,),))
        with self.assertRaisesRegex(ValueError, "finite-size exact fallback"):
            count_subexponential(formula, max_fallback_variables=24)


if __name__ == "__main__":
    unittest.main()
