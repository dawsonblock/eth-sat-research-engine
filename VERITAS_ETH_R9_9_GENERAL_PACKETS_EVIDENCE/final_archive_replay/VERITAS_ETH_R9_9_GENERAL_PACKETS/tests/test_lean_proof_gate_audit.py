"""Adversarial checks for the local Lean evidence gate, not theorem proofs."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_conditional_expectation_lean.py"
spec = importlib.util.spec_from_file_location("veritas_lean_gate", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_exact_axiom_reports_accept_the_standard_trusted_base():
    output = ("'first' depends on axioms: [propext, Classical.choice, Quot.sound]\n"
              "'second' does not depend on any axioms\n")
    audit = gate.check_axiom_reports(output, ("first", "second"))
    assert audit["passed"]
    assert audit["reports"]["second"] == []


@pytest.mark.parametrize("output,reason", [
    ("'target' depends on axioms: [injected_assumption]", "unexpected_axioms"),
    ("'target' depends on axioms: [sorryAx]", "unexpected_axioms"),
    ("'target_extra' depends on axioms: [propext]", "missing"),
    ("warning: target depends on axioms: [propext]", "malformed"),
    ("'target' depends on axioms: [propext]\n"
     "'target' depends on axioms: [propext]", "duplicates"),
])
def test_axiom_gate_rejects_forged_or_untrusted_reports(output, reason):
    audit = gate.check_axiom_reports(output, ("target",))
    assert not audit["passed"]
    assert audit[reason]


def test_axiom_gate_checks_noncentral_printed_reports_too():
    output = ("'target' depends on axioms: [propext]\n"
              "'another' depends on axioms: [injected_assumption]\n")
    audit = gate.check_axiom_reports(output, ("target",))
    assert not audit["passed"]
    assert audit["unexpected_axioms"] == ["injected_assumption"]


@pytest.mark.parametrize("toolchain,output,expected", [
    ("leanprover/lean4:v4.35.0", "Lean (version 4.35.0, arm64, Release)", True),
    ("leanprover/lean4:v4.35.0", "Lean (version 0.0.0, fake)", False),
    ("leanprover/lean4:v4.35.0", "Lean (version 4.35.0-rc1, fake)", False),
    ("unrecognized-toolchain", "Lean (version 4.35.0, fake)", False),
    ("leanprover/lean4:v4.35.0", "", False),
])
def test_exact_pinned_toolchain_version(toolchain, output, expected):
    assert gate.check_lean_version(toolchain, output) is expected


def test_failed_gate_clears_partial_positive_proof_claims():
    evidence = {"status": "FAIL", "a_proven": True, "b_proven": True}
    gate.clear_failed_qualifications(evidence, ("a_proven", "b_proven"))
    assert evidence == {"status": "FAIL", "a_proven": False, "b_proven": False}


def test_passing_gate_preserves_positive_proof_claims():
    evidence = {"status": "PASS", "a_proven": True}
    gate.clear_failed_qualifications(evidence, ("a_proven",))
    assert evidence["a_proven"] is True


def test_ci_has_an_independent_fail_closed_lean_job_and_failure_artifact():
    workflow = SCRIPT.parents[1] / ".github" / "workflows" / "test.yml"
    source = workflow.read_text(encoding="utf-8")
    lean_job = source.split("  lean-proof:", 1)[1]
    assert "leanprover/lean-action@24581d74d674803a25a81b10b059c5c0cdd344c6" in lean_job
    assert "python scripts/validate_conditional_expectation_lean.py" in lean_job
    assert "if: always()" in lean_job
    assert "actions/upload-artifact@v4" in lean_job
    assert "validation/r9_ci_proof.json" in lean_job
    assert "needs: [test]" not in lean_job
    assert "leanprover/lean-action@v1" not in lean_job


def test_ci_builds_and_tests_the_optional_cpp_backend_separately():
    workflow = SCRIPT.parents[1] / ".github" / "workflows" / "test.yml"
    source = workflow.read_text(encoding="utf-8")
    cpp_job = source.split("  cpp-differential:", 1)[1]
    assert "cmake -S cpp -B build/cpp" in cpp_job
    assert "python scripts/validate_r91_cpp.py" in cpp_job
    assert "tests/test_r91_cpp_backend.py" in cpp_job
    assert "actions/upload-artifact@v4" in cpp_job


def test_missing_compiler_writes_failure_evidence_and_clears_flags(tmp_path, monkeypatch):
    (tmp_path / "paper").mkdir()
    pinned_paper = SCRIPT.parents[1] / "paper" / "quantitative-contraction.tex"
    shutil.copyfile(pinned_paper, tmp_path / "paper" / "quantitative-contraction.tex")
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
    output = tmp_path / "proof.json"
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "PROOF_FILES", ())
    monkeypatch.setattr(gate.sys, "argv", ["proof-gate", "--output", str(output)])
    monkeypatch.setenv("LEAN_BIN", str(tmp_path / "missing-lean"))
    monkeypatch.delenv("ELAN_HOME", raising=False)
    assert gate.main() == 2
    evidence = json.loads(output.read_text())
    assert evidence["status"] == "FAIL"
    assert evidence["lean_version_output"]
    assert evidence["finite_pair_marginal_variance_bound_proven"] is False


def test_missing_module_fails_and_persists_evidence(tmp_path, monkeypatch):
    (tmp_path / "paper").mkdir()
    pinned_paper = SCRIPT.parents[1] / "paper" / "quantitative-contraction.tex"
    shutil.copyfile(pinned_paper, tmp_path / "paper" / "quantitative-contraction.tex")
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
    fake_lean = tmp_path / "lean"
    fake_lean.write_text("#!/bin/sh\nprintf 'Lean (version 4.35.0, test fixture)\\n'\n")
    fake_lean.chmod(fake_lean.stat().st_mode | stat.S_IXUSR)
    output = tmp_path / "proof.json"
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "PROOF_FILES", ("proofs/missing.lean",))
    monkeypatch.setattr(gate.sys, "argv", ["proof-gate", "--output", str(output)])
    monkeypatch.setenv("LEAN_BIN", str(fake_lean))
    monkeypatch.delenv("ELAN_HOME", raising=False)
    assert gate.main() == 2
    evidence = json.loads(output.read_text())
    assert evidence["status"] == "FAIL"
    assert evidence["results"] == [{"file": "proofs/missing.lean", "status": "MISSING"}]
    assert evidence["lean_any_distinct_covering_order_port_bound_proven"] is False


def test_changed_manuscript_pin_fails_closed_and_writes_evidence(tmp_path, monkeypatch):
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "quantitative-contraction.tex").write_text("changed paper")
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "PROOF_FILES", ())
    monkeypatch.setattr(gate.sys, "argv", ["proof-gate", "--output", str(output)])
    monkeypatch.setattr(gate.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout="Lean (version 4.35.0, test fixture)"))
    monkeypatch.setenv("LEAN_BIN", "/tmp/lean")
    monkeypatch.delenv("ELAN_HOME", raising=False)
    assert gate.main() == 2
    evidence = json.loads(output.read_text())
    assert evidence["status"] == "FAIL"
    assert evidence["manuscript_pin_matches"] is False
    assert evidence["pinned_lean_version_matches"] is True
    assert evidence["lean_generated_symbol_port_bound_proven"] is False
