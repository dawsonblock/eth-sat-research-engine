"""Kernel/compiler fault injection for the R9 Lean proof gate."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_conditional_expectation_lean.py"
spec = importlib.util.spec_from_file_location("veritas_lean_gate_faults", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def _lean_4350():
    candidate = os.environ.get("LEAN_BIN") or shutil.which("lean")
    if not candidate:
        pytest.skip("Lean is installed only in the separate lean-proof CI job")
    try:
        version = subprocess.run(
            [candidate, "--version"], capture_output=True, text=True,
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("Lean executable is not runnable in this test environment")
    if version.returncode != 0 or not gate.check_lean_version(
            "leanprover/lean4:v4.35.0", version.stdout):
        pytest.skip("fault injection requires the pinned Lean 4.35.0 toolchain")
    return str(Path(candidate).resolve())


@pytest.mark.parametrize("module,theorem,end_marker,dependent", [
    ("D3SymbolPorts", "d3_any_order_symbol_port_bound",
     "\n#print axioms d3_any_order_symbol_port_bound", "D3PythonOrder"),
    ("D3PaddedConstruction", "constructed_real_edge_contract",
     "\n#print axioms member_le_max", "D3R93Contracts"),
])
def test_substituting_true_for_substantive_theorem_fails_full_gate(
        tmp_path, monkeypatch, module, theorem, end_marker, dependent):
    lean = _lean_4350()
    source_root = SCRIPT.parents[1]
    proof_root = tmp_path / "proofs"
    shutil.copytree(source_root / "proofs", proof_root)
    (tmp_path / "paper").mkdir()
    shutil.copyfile(source_root / "paper" / "quantitative-contraction.tex",
                    tmp_path / "paper" / "quantitative-contraction.tex")
    shutil.copyfile(source_root / "lean-toolchain", tmp_path / "lean-toolchain")

    path = proof_root / (module + ".lean")
    text = path.read_text(encoding="utf-8")
    start = text.index("theorem " + theorem)
    end = text.index(end_marker, start)
    text = (text[:start] +
            f"theorem {theorem} : True := by trivial\n" +
            text[end:])
    path.write_text(text, encoding="utf-8")

    output = tmp_path / "proof.json"
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate.sys, "argv", ["proof-gate", "--output", str(output)])
    monkeypatch.setenv("LEAN_BIN", lean)
    monkeypatch.delenv("ELAN_HOME", raising=False)
    assert gate.main() == 2
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["status"] == "FAIL"
    assert evidence["lean_any_distinct_covering_order_port_bound_proven"] is False
    assert evidence["lean_python_sorted_order_port_bound_proven"] is False
    assert evidence["lean_central_contract_types_checked"] is False
    assert evidence["lean_r93_contracts_checked"] is False
    assert evidence["lean_global_edge_occurrence_model_bijection_proven"] is False
    assert evidence["lean_computed_padding_model_proven"] is False
    assert any(item["file"] == f"proofs/{dependent}.lean" and
               item.get("return_code") not in (None, 0)
               for item in evidence["results"])

