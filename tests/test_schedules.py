import unittest

from eth_sat.schedules import build_balanced_schedules


class ScheduleTests(unittest.TestCase):
    def test_conditional_expectation_is_deterministic_and_valid(self):
        scopes = ((0, 1), (0, 2), ())
        first = build_balanced_schedules(3, scopes, r=2, q=2)
        second = build_balanced_schedules(3, scopes, r=2, q=2)
        self.assertEqual(first, second)
        self.assertEqual(len(first.variable_schedules), 3)
        self.assertEqual(len(first.factor_schedules), 3)
        self.assertEqual(first.factor_schedules[2], (0, 0))
        self.assertTrue(all(len(schedule) == 2 for schedule in first.variable_schedules))
        self.assertTrue(all(len(schedule) == 2 for schedule in first.factor_schedules))

    def test_reports_actual_group_and_label_bounds(self):
        result = build_balanced_schedules(
            4, ((0,), (1,), (2,), (3,)), r=2, q=1
        )
        self.assertEqual(result.max_group_size, 2)
        self.assertEqual(result.max_label_count, 1)
        self.assertTrue(result.paper_bounds_met)
        self.assertFalse(result.hypotheses_met)

    def test_empty_scopes_keep_isolated_variables_and_fix_empty_factors(self):
        result = build_balanced_schedules(3, ((),), r=2, q=2)
        self.assertEqual(len(result.variable_schedules), 3)
        self.assertEqual(result.factor_schedules, ((0, 0),))
        self.assertEqual(sum(result.group_sizes[0]), 3)

    def test_rejects_invalid_scope_indices(self):
        with self.assertRaisesRegex(ValueError, "invalid variable"):
            build_balanced_schedules(2, ((2,),), r=2, q=1)

    def test_rejects_schedule_search_above_bounded_work_limit(self):
        with self.assertRaisesRegex(ValueError, "work estimate"):
            build_balanced_schedules(1, ((0,),), r=2, q=20)


if __name__ == "__main__":
    unittest.main()
