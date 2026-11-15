"""Mathematical regression: residual merge, preprocess, invariants (no theorem claims)."""
from veritas.core.cnf import CNF
from veritas.research.sat_count_invariants import collect_count_invariants
from veritas.research.sat_phase_c_preprocess import apply_phase_c_preprocess
from veritas.research.sat_residual_equivalence import count_by_residual_equivalence
from veritas.research.sat_universal import run_universal_sat
from veritas.solvers.reference import exhaustive_count


def test_residual_unsat_formula_count_zero():
    cnf = CNF.from_lists(2, [[1], [-1]])
    report = count_by_residual_equivalence(cnf)
    assert report["agreement"] is True
    assert report["status"] == "EXACT_COUNT"
    assert report["count"] == 0
    assert report["oracle_exhaustive_count"] == 0


def test_residual_xyz_toy_count_five():
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    report = count_by_residual_equivalence(cnf, branch_order=(1, 2))
    assert report["count"] == 5
    assert report["distinct_residual_classes"] == 2
    assert report["full_assignment_branches"] == 4


def test_residual_empty_branch_order_buckets_root_once():
    cnf = CNF.from_lists(2, [[1, 2]])
    report = count_by_residual_equivalence(cnf, branch_order=())
    assert report["agreement"] is True
    assert report["full_assignment_branches"] == 1
    assert report["count"] == 3


def test_preprocess_count_preserved_random_style():
    for cnf in (
        CNF.from_lists(3, [[1, 2, -3]]),
        CNF.from_lists(4, [[1, 2], [-3, 4]]),
        CNF.from_lists(2, [[1], [-1]]),
    ):
        reduced, detail, _ = apply_phase_c_preprocess(cnf, w_old=8)
        expected = 0 if detail["status"] == "UNSAT" else exhaustive_count(cnf)
        got = 0 if detail["status"] == "UNSAT" else exhaustive_count(reduced)
        assert expected == got, (cnf, detail)


def test_count_invariants_no_false_proved_in_repo():
    cnf = CNF.from_lists(3, [[1, 2, -3], [1, -2, 3], [-1, 2, 3]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=8.0)
    reg = collect_count_invariants(report["reduction"])
    for entry in reg["entries"]:
        assert entry["proved_in_repo"] is False
        assert entry["theorem_backed"] is False
    assert report["universal_speedup_claimed"] is False