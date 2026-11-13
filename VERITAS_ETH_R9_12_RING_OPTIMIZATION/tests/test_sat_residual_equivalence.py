"""Residual equivalence counting scaffold."""
from veritas.core.cnf import CNF
from veritas.research.sat_residual_equivalence import (
    count_by_residual_equivalence,
    xor_system_solution_count,
)


def test_xyz_clause_merge_counts_five():
    # (x ∨ z) ∧ (y ∨ z) with x=1, y=2, z=3
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    report = count_by_residual_equivalence(cnf, branch_order=(1, 2))
    assert report["status"] == "EXACT_COUNT"
    assert report["count"] == 5
    assert report["agreement"] is True
    assert report["distinct_residual_classes"] < report["full_assignment_branches"]
    assert report["distinct_residual_classes"] == 2


def test_residual_merge_matches_exhaustive_on_disconnected():
    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    report = count_by_residual_equivalence(cnf)
    assert report["count"] == report["oracle_exhaustive_count"] == 9


def test_xor_rank_demo_matches_power_of_two():
    assert xor_system_solution_count(96, rank=86, consistent=True) == 1 << 10
