"""E2 external SAT baseline matrix."""
from veritas.core.cnf import CNF
from veritas.research.sat_external_baselines import run_baseline_matrix
from veritas.research.sat_universal import run_universal_sat


def test_baseline_matrix_reference_only_decision():
    cnf = CNF.from_lists(2, [[1, -2]])
    report = run_baseline_matrix(cnf, task="decision", include_external=False)
    assert report["schema"] == "VERITAS_SAT_BASELINE_MATRIX_V1"
    assert report["runs"][0]["baseline_id"] == "veritas_reference"
    assert report["runs"][0]["status"] == "SAT"


def test_external_baselines_skip_when_missing():
    cnf = CNF.from_lists(2, [[1], [-1]])
    report = run_baseline_matrix(cnf, task="decision", include_external=True)
    external = [r for r in report["runs"] if r["baseline_id"] != "veritas_reference"]
    assert external
    assert all(r.get("status") == "SKIPPED" or r.get("status") in ("SAT", "UNSAT", "UNKNOWN", "TIMEOUT") for r in external)


def test_universal_cli_baseline_matrix_attachment():
    cnf = CNF.from_lists(2, [[1, 2]])
    report = run_universal_sat(
        cnf, "decision", timeout_s=2.0, include_baseline_matrix=True
    )
    matrix = report["baseline_matrix"]
    assert matrix is not None
    assert matrix["task"] == "decision"
