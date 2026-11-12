"""Reduction-first universal SAT entry (E1)."""
import json

from veritas.core.cnf import CNF
import pytest
from veritas.research.sat_universal import INTERACTION_96_CERT, run_universal_sat
from veritas.solvers.reference import exhaustive_count


def test_fixed_density_reduction_valid_on_tiny_3cnf():
    cnf = CNF.from_lists(3, [[1, 2, -3], [1, -2, 3]])
    report = run_universal_sat(cnf, "decision", timeout_s=2.0, adaptive_timeout_s=2.0)
    assert report["schema"] == "VERITAS_SAT_UNIVERSAL_RUN_V1"
    assert not report["universal_speedup_claimed"]
    assert not report["theorem_backed"]
    chk = report["reduction"]["structural_check"]
    assert chk["valid"] is True
    assert report["cross_checks"]["schema"] == "VERITAS_SAT_CROSS_CHECKS_V1"
    assert report["jet_fast_path"]["status"] == "REFUSED"
    assert report["result"]["status"] == "SAT"
    assert report["cross_checks"]["agreement"] is True
    assert report["cross_checks"]["phase_c_vs_direct"]["agreement"] is True


def test_jet_refused_even_with_interaction_cert_until_parent_map():
    cnf = CNF.from_lists(2, [[1, 2]])
    report = run_universal_sat(
        cnf, "decision", interaction_cert=INTERACTION_96_CERT, timeout_s=2.0
    )
    jet = report["jet_fast_path"]
    assert jet["status"] == "REFUSED"
    assert jet["reason"] == "parent_digest_mismatch"


def test_count_lane_matches_exhaustive_on_small_formula():
    cnf = CNF.from_lists(3, [[1, 2], [-1, 3]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=10.0, timeout_s=4.0)
    assert report["result"]["status"] in ("EXACT_COUNT", "COUNT_RESIDUE")
    assert int(report["result"]["count"]) == exhaustive_count(cnf)
    assert report["cross_checks"]["agreement"] is True
    assert report["cross_checks"]["phase_c_vs_direct"]["agreement"] is True
    assert report["cross_checks"]["phase_c_vs_direct"]["phase_c_count"] == exhaustive_count(
        cnf
    )
    led = report["decomposition_work"]
    assert led["schema"] == "VERITAS_SAT_WORK_AGGREGATE_V1"
    assert len(led["steps"]) >= 3


def test_non_3cnf_refused():
    cnf = CNF.from_lists(4, [[1, 2, 3, 4]])
    with pytest.raises(ValueError, match="3-CNF"):
        run_universal_sat(cnf, "decision")


def test_jet_diagnostic_fixture_runs_fast_solver():
    cnf = CNF.from_lists(2, [[1, 2]])
    report = run_universal_sat(
        cnf,
        "decision",
        interaction_cert=INTERACTION_96_CERT,
        jet_diagnostic_fixture=True,
        timeout_s=2.0,
    )
    jet = report["jet_fast_path"]
    assert jet["status"] == "DIAGNOSTIC_FAST_JET_RAN"
    assert jet["reconstruction_equals_oracle"] is True
    assert jet["digest_gate"] == "fixture_override"


def test_decomposition_ledger_serializes():
    cnf = CNF.from_lists(1, [[1]])
    report = run_universal_sat(cnf, "decision", timeout_s=1.0)
    json.dumps(report["decomposition_work"])
