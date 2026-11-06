"""R9.6 regression tests: release-input integrity and out-of-tree evidence.

Red test (R9.5): ``.github/workflows/test.yml`` ran ``scripts/validate_v08.py``
before ``scripts/verify_manifest.py``.  ``validate_v08.py`` rewrites
``validation/validation_v08.json``, which is a manifest-covered release input,
so an untouched release failed its own manifest check:

    PASS: 820 complete file hashes match release manifest
    (validate_v08.py runs, rewriting validation_v08.json)
    FAIL: checksum mismatch: validation/validation_v08.json

Green test (R9.6): the manifest is verified before any step can write, every
validator honours an out-of-tree destination, and the job re-verifies the same
immutable bytes afterwards.
"""
import json
import os
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
INTEGRITY = SCRIPTS / "release_integrity.py"


def build_tree(tmp_path, files):
    root = tmp_path / "release"
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    lines = [f"{sha256(data).hexdigest()}  {rel}"
             for rel, data in sorted(files.items())]
    (root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    return root


def run(*args, **kwargs):
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, timeout=300, **kwargs)


BASE = {
    "src/pkg/mod.py": b"VALUE = 1\n",
    "paper/quantitative-contraction.tex": b"\\documentclass{article}\n",
    "validation/report.json": b'{"elapsed_s": 1.0}\n',
}


def test_verify_passes_on_an_untouched_tree(tmp_path):
    root = build_tree(tmp_path, BASE)
    result = run(str(INTEGRITY), "verify", "--root", str(root))
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


@pytest.mark.parametrize("mutation", ["modify", "add", "remove", "manifest"])
def test_verify_rejects_every_kind_of_drift(tmp_path, mutation):
    root = build_tree(tmp_path, BASE)
    if mutation == "modify":
        (root / "validation/report.json").write_bytes(b'{"elapsed_s": 2.0}\n')
    elif mutation == "add":
        (root / "validation/extra.json").write_text("{}", encoding="utf8")
    elif mutation == "remove":
        (root / "src/pkg/mod.py").unlink()
    else:
        manifest = root / "SHA256SUMS.txt"
        manifest.write_text(manifest.read_text().replace(
            sha256(BASE["src/pkg/mod.py"]).hexdigest(), "0" * 64), encoding="utf8")
    result = run(str(INTEGRITY), "verify", "--root", str(root))
    assert result.returncode == 1
    assert "FAIL" in result.stdout


def test_manifest_check_is_identical_under_optimized_python(tmp_path):
    root = build_tree(tmp_path, BASE)
    normal = run(str(INTEGRITY), "verify", "--root", str(root))
    optimized = run("-O", str(INTEGRITY), "verify", "--root", str(root))
    assert normal.returncode == optimized.returncode == 0
    assert normal.stdout == optimized.stdout


def test_snapshot_then_compare_detects_validation_time_mutation(tmp_path):
    root = build_tree(tmp_path, BASE)
    snapshot = tmp_path / "snapshot.json"
    assert run(str(INTEGRITY), "snapshot", "--root", str(root),
               "--output", str(snapshot)).returncode == 0
    # Simulate the historical defect: a validator rewrites a release input.
    (root / "validation/report.json").write_bytes(b'{"elapsed_s": 99.0}\n')
    comparison = tmp_path / "comparison.json"
    result = run(str(INTEGRITY), "compare", "--root", str(root),
                 "--snapshot", str(snapshot), "--output", str(comparison))
    assert result.returncode == 1
    record = json.loads(comparison.read_text())
    assert record["release_inputs_stable"] is False
    assert record["modified"] == ["validation/report.json"]


def test_compare_passes_when_only_out_of_tree_evidence_changed(tmp_path):
    root = build_tree(tmp_path, BASE)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    snapshot = tmp_path / "snapshot.json"
    run(str(INTEGRITY), "snapshot", "--root", str(root), "--output", str(snapshot))
    (evidence / "fresh.json").write_text('{"elapsed_s": 5.0}', encoding="utf8")
    result = run(str(INTEGRITY), "compare", "--root", str(root),
                 "--snapshot", str(snapshot))
    assert result.returncode == 0, result.stdout
    assert "PASS" in result.stdout


def test_runtime_evidence_manifest_is_separate_from_release_inputs(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "a.json").write_text("{}", encoding="utf8")
    output = tmp_path / "evidence_manifest.json"
    result = run(str(INTEGRITY), "evidence", "--output", str(output),
                 "--directory", str(evidence))
    assert result.returncode == 0, result.stderr
    record = json.loads(output.read_text())
    assert record["role"] == "RUNTIME_EVIDENCE_NOT_RELEASE_INPUT"
    assert record["trust_class"] == "HASH_MATCH_UNSIGNED"
    assert [Path(name).name for name in record["files"]] == ["a.json"]


def test_evidence_path_prefers_explicit_output(tmp_path, monkeypatch):
    sys.path.insert(0, str(SCRIPTS))
    try:
        import _evidence
    finally:
        sys.path.pop(0)
    target = _evidence.evidence_path("validation/x.json", ["--output",
                                                           str(tmp_path / "y.json")])
    assert target == tmp_path / "y.json"
    monkeypatch.setenv("VERITAS_EVIDENCE_DIR", str(tmp_path / "dir"))
    target = _evidence.evidence_path("validation/x.json", [])
    assert target == tmp_path / "dir" / "x.json"
    monkeypatch.delenv("VERITAS_EVIDENCE_DIR")
    target = _evidence.evidence_path("validation/x.json", [], root=tmp_path)
    assert target == tmp_path / "validation" / "x.json"


def test_evidence_path_rejects_a_missing_output_argument():
    sys.path.insert(0, str(SCRIPTS))
    try:
        import _evidence
    finally:
        sys.path.pop(0)
    with pytest.raises(_evidence.EvidencePathError):
        _evidence.evidence_path("validation/x.json", ["--output"])


def test_validator_writes_out_of_tree_and_leaves_the_tree_intact(tmp_path):
    """End-to-end: a real validator must not write into its working tree."""
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    evidence = tmp_path / "evidence"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["VERITAS_EVIDENCE_DIR"] = str(evidence)
    result = subprocess.run([sys.executable, str(SCRIPTS / "validate_v36.py")],
                            capture_output=True, text=True, env=env,
                            cwd=str(workdir), timeout=600)
    assert result.returncode == 0, result.stderr
    assert (evidence / "v36_validation.json").is_file()
    assert not (workdir / "validation").exists()
    # And without the override it still honours an explicit --output.
    explicit = tmp_path / "explicit.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_v36.py"),
         "--output", str(explicit)],
        capture_output=True, text=True, env=env, cwd=str(workdir), timeout=600)
    assert result.returncode == 0, result.stderr
    assert explicit.is_file()
    assert not (workdir / "validation").exists()


def test_ci_verifies_before_and_after_validation():
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
    test_job = workflow.split("  test:", 1)[1].split("  cpp-backend:", 1)[0]
    pre = test_job.index("release_integrity.py verify")
    install = test_job.index("pip install")
    validator = test_job.index("validate_v08.py")
    post = test_job.index("release_integrity.py compare")
    assert pre < install < validator < post, (
        "the manifest must be verified before anything writes, and the same "
        "immutable bytes must be re-verified after validation")
    assert "VERITAS_EVIDENCE_DIR" in test_job
    assert "python -O scripts/release_integrity.py verify" in test_job


def test_no_validator_writes_a_manifest_covered_report_by_default():
    """Every writing validator must route through the evidence helper."""
    offenders = []
    for script in sorted(SCRIPTS.glob("validate_*.py")):
        text = script.read_text(encoding="utf-8")
        if "validation/" not in text:
            continue
        writes = [line for line in text.splitlines()
                  if ("write_text(" in line or ".write(" in line)
                  and "validation/" in line]
        if writes:
            offenders.append((script.name, writes))
    assert offenders == [], offenders
