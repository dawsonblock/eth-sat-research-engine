"""Freshness tests for aggregated Lean proof evidence.

These tests validate source binding and failure behavior; they do not run or
prove the Lean theorems.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_r91.py"
spec = importlib.util.spec_from_file_location("veritas_validate_r91", SCRIPT)
aggregate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aggregate)
gate = sys.modules.get("validate_conditional_expectation_lean")


def _write_valid_fixture(root: Path):
    paper = root / "paper/quantitative-contraction.tex"
    paper.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "paper/quantitative-contraction.tex", paper)
    shutil.copyfile(ROOT / "lean-toolchain", root / "lean-toolchain")
    validator = root / "scripts/validate_conditional_expectation_lean.py"
    validator.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "scripts/validate_conditional_expectation_lean.py", validator)

    results = []
    for relative in aggregate.PROOF_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"-- fixture proof source: {relative}\n", encoding="utf-8")
        entry = {
            "file": relative,
            "sha256": aggregate.sha256(path),
            "return_code": 0,
            "sorryAx_absent": True,
        }
        required = aggregate.CENTRAL_THEOREMS_BY_FILE.get(relative, ())
        if required:
            entry["output"] = "\n".join(f"'{name}' does not depend on any axioms" for name in required)
            entry["axiom_lines"] = []
            entry["central_theorems_present"] = True
            entry["central_theorems_qualified"] = True
            entry["central_theorems_printed"] = {name: True for name in required}
            entry["axiom_audit"] = {
                "passed": True,
                "reports": {name: [] for name in required},
                "missing": [], "malformed": [], "duplicates": [],
                "unexpected_axioms": [],
            }
        results.append(entry)

    toolchain = (root / "lean-toolchain").read_text(encoding="utf-8").strip()
    evidence = {
        "status": "PASS",
        "manuscript_source": "paper/quantitative-contraction.tex",
        "manuscript_sha256": aggregate.PINNED_CONTRACTION_SHA256,
        "manuscript_pin_matches": True,
        "lean_toolchain": toolchain,
        "lean_version_output": "Lean (version 4.35.0, test fixture)",
        "pinned_lean_version_matches": True,
        "allowed_lean_axioms": sorted(aggregate.ALLOWED_LEAN_AXIOMS),
        "theorem_mode_enabled": False,
        "validator_sha256": aggregate.sha256(validator),
        "proof_manifest_sha256": aggregate.proof_manifest_sha256(root),
        "results": results,
    }
    return evidence


def test_current_hash_bound_evidence_is_fresh_but_not_authenticated(tmp_path):
    evidence = _write_valid_fixture(tmp_path)
    checked = aggregate.check_lean_evidence_freshness(evidence, tmp_path)
    assert checked["fresh"]
    assert checked["freshness_is_authentication"] is False


def test_modified_proof_source_invalidates_old_pass(tmp_path):
    evidence = _write_valid_fixture(tmp_path)
    changed = tmp_path / evidence["results"][4]["file"]
    changed.write_text(changed.read_text() + "-- modified\n", encoding="utf-8")
    checked = aggregate.check_lean_evidence_freshness(evidence, tmp_path)
    assert not checked["fresh"]
    assert any("proof source changed" in reason for reason in checked["reasons"])
    assert aggregate.lean_flag(evidence, checked, "lean_packet_slot_bijection_proven") is False


def test_deleted_module_invalidates_old_pass(tmp_path):
    evidence = _write_valid_fixture(tmp_path)
    victim = tmp_path / evidence["results"][0]["file"]
    victim.unlink()
    checked = aggregate.check_lean_evidence_freshness(evidence, tmp_path)
    assert not checked["fresh"]
    assert any("missing or symlinked" in reason for reason in checked["reasons"])


def test_missing_duplicate_and_reordered_results_fail_closed(tmp_path):
    evidence = _write_valid_fixture(tmp_path)
    for mutate in (
        lambda report: report["results"].pop(),
        lambda report: report["results"].__setitem__(1, report["results"][0]),
        lambda report: report["results"].reverse(),
    ):
        altered = json.loads(json.dumps(evidence))
        mutate(altered)
        checked = aggregate.check_lean_evidence_freshness(altered, tmp_path)
        assert not checked["fresh"]
        assert any("inventory" in reason or "duplicated" in reason
                   for reason in checked["reasons"])


def test_stale_paper_toolchain_and_validator_are_rejected(tmp_path):
    evidence = _write_valid_fixture(tmp_path)
    cases = []
    paper = tmp_path / "paper/quantitative-contraction.tex"
    paper.write_text(paper.read_text() + "% changed\n", encoding="utf-8")
    cases.append(aggregate.check_lean_evidence_freshness(evidence, tmp_path))
    paper.write_text((ROOT / "paper/quantitative-contraction.tex").read_text(), encoding="utf-8")
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v0.0.0\n", encoding="utf-8")
    cases.append(aggregate.check_lean_evidence_freshness(evidence, tmp_path))
    shutil.copyfile(ROOT / "lean-toolchain", tmp_path / "lean-toolchain")
    validator = tmp_path / "scripts/validate_conditional_expectation_lean.py"
    validator.write_text(validator.read_text() + "# changed\n", encoding="utf-8")
    cases.append(aggregate.check_lean_evidence_freshness(evidence, tmp_path))
    assert all(not case["fresh"] for case in cases)


def test_incomplete_axiom_audit_or_missing_manifest_fails(tmp_path):
    evidence = _write_valid_fixture(tmp_path)
    central = next(entry for entry in evidence["results"] if "axiom_audit" in entry)
    central["axiom_audit"]["unexpected_axioms"] = ["injected_assumption"]
    assert not aggregate.check_lean_evidence_freshness(evidence, tmp_path)["fresh"]
    evidence = _write_valid_fixture(tmp_path)
    evidence.pop("proof_manifest_sha256")
    assert not aggregate.check_lean_evidence_freshness(evidence, tmp_path)["fresh"]
