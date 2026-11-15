"""E2 CI: pinned external solver when installed (optional locally)."""
import os
import shutil

import pytest

from veritas.core.cnf import CNF
from veritas.research.sat_external_baselines import run_baseline_matrix


PINNED_CADICAL_RELEASE = "rel-2.1.2"


@pytest.mark.skipif(
    shutil.which("cadical") is None,
    reason="cadical not on PATH (built in CI E2 job)",
)
def test_cadical_agrees_with_veritas_reference():
    cnf = CNF.from_lists(12, [[1, 2, 3], [-1, -2, 4], [2, -3, -4], [1, -4, 5]])
    report = run_baseline_matrix(cnf, task="decision", include_external=True)
    ref = next(r for r in report["runs"] if r["baseline_id"] == "veritas_reference")
    cad = next(r for r in report["runs"] if r["baseline_id"] == "cadical")
    assert ref["status"] in ("SAT", "UNSAT")
    assert cad["status"] == ref["status"], cad
    assert cad.get("pinned_release", "").startswith("Rel-2.1")
    agree = next(
        a for a in report["agreements"] if a["baseline_id"] == "cadical"
    )
    assert agree["agrees_with_veritas_reference"]


@pytest.mark.skipif(
    os.environ.get("CI") != "true" or shutil.which("cadical") is None,
    reason="records pinned cadical binary only in CI",
)
@pytest.mark.skipif(
    shutil.which("kissat") is None,
    reason="kissat not on PATH",
)
def test_kissat_agrees_with_veritas_reference():
    cnf = CNF.from_lists(8, [[1, -2], [2, -3], [3, -4], [4, -1]])
    report = run_baseline_matrix(cnf, task="decision", include_external=True)
    ref = next(r for r in report["runs"] if r["baseline_id"] == "veritas_reference")
    kiss = next(r for r in report["runs"] if r["baseline_id"] == "kissat")
    assert ref["status"] in ("SAT", "UNSAT")
    assert kiss["status"] == ref["status"]


@pytest.mark.skipif(
    os.environ.get("CI") != "true" or shutil.which("cadical") is None,
    reason="records pinned cadical binary only in CI",
)
def test_ci_cadical_version_probe():
    report = run_baseline_matrix(
        CNF.from_lists(1, [[1]]),
        task="decision",
        include_external=True,
    )
    cad = next(r for r in report["runs"] if r["baseline_id"] == "cadical")
    assert cad["status"] != "SKIPPED"
    probe = (cad.get("version_probe") or "").lower()
    assert "2.1" in probe or cad.get("exit_code") in (10, 20)
