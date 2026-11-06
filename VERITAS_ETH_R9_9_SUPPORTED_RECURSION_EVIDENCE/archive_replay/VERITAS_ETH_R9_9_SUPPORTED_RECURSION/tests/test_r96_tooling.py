from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_boundary_contract_rejects_true_substitute(tmp_path):
    lean = os.environ.get("LEAN_BIN") or shutil.which("lean")
    if not lean:
        pytest.skip("Lean unavailable for compile fault")
    source = (ROOT / "proofs/FiniteBoundaryReduction.lean").read_text()
    start = source.index("theorem boundary_mod ")
    end = source.index("#print axioms factor_left", start)
    (tmp_path / "FiniteBoundaryReduction.lean").write_text(
        source[:start] + "theorem boundary_mod : True := True.intro\n\n" + source[end:]
    )
    shutil.copy(ROOT / "proofs/FiniteBoundaryContract.lean", tmp_path)
    env = {**os.environ, "LEAN_PATH": str(tmp_path)}
    subprocess.run(
        [lean, "-o", "FiniteBoundaryReduction.olean", "FiniteBoundaryReduction.lean"],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        timeout=60,
    )
    bad = subprocess.run(
        [lean, "FiniteBoundaryContract.lean"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert bad.returncode != 0 and "boundary_mod" in bad.stdout


def test_dimacs_certificate_cli_and_corruption(tmp_path):
    path = tmp_path / "input.cnf"
    path.write_text("p cnf 3 2\n1 2 0\n-1 2 0\n")
    cert = tmp_path / "record.json"
    base = [
        sys.executable,
        "-m",
        "veritas.research.finite_reductions",
        str(path),
        "--leaf-edges",
        "1",
    ]
    out = subprocess.run(
        [*base, "--write", str(cert)], capture_output=True, text=True, check=True
    )
    assert json.loads(out.stdout)["model_count"] == 4
    cmd = [*base, "--replay", str(cert)]
    assert json.loads(subprocess.check_output(cmd, text=True))["valid"] is True
    altered = json.loads(cert.read_text())
    altered["tree"]["terms"].pop()
    cert.write_text(json.dumps(altered))
    out = subprocess.run(cmd, capture_output=True, text=True)
    assert out.returncode and json.loads(out.stdout)["valid"] is False
