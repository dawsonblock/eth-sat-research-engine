"""Validate the nonconstant full-grid driver through its external CLI."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.parent_child_r98.model import canonical
from veritas.research.tapered_v4.provenance import source_binding


def run(output):
    if output.resolve().is_relative_to(ROOT):
        raise ValueError("evidence must be outside the source checkout")
    output.parent.mkdir(parents=True, exist_ok=True)
    execution = output.parent / "general-matching22.json"
    binding = source_binding()
    command = [sys.executable, "-m", "veritas.research.parent_child_r98.general_cli",
               str(ROOT / "examples/r98_general_matching22.json"), "--output", str(execution)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=900,
                            env=dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1"))
    report = {"status": "FAILED_OR_INCONCLUSIVE", "source": binding,
              "command": command, "exit_code": result.returncode,
              "source_qualified": False, "theorem_mode_enabled": False}
    try:
        if result.returncode:
            raise ValueError(result.stdout[-2000:] + result.stderr[-1000:])
        # Reports include elapsed-time floats; immutable recipe decoding is stricter.
        data = json.loads(execution.read_bytes())
        assert data["status"] == "PASS_FINITE_SCALED_GENERAL_SHRINKING_RECURSION"
        assert data["result"] == [[31**22, 0, 0, 0, 0, 0, 0]]
        assert data["edge_layers"] == {"0": [22], "1": [0, 2]}
        assert data["ledger"]["actual_calls"] == 8577
        assert data["ledger"]["point_evaluations"] == 134
        assert data["ledger"]["nonshrinking_children"] == 0
        assert len({point["term_sha256"] for point in data["transitions"]}) > 1
        assert all(len(point["child_edges"]) == 64 and sum(point["child_edges"]) == 44
                   and all(64 * n <= 132 for n in point["child_edges"])
                   for point in data["transitions"])
        assert not data["source_qualified"] and not data["theorem_mode_enabled"]
        assert source_binding() == binding
        report.update(status=data["status"], exact_result=data["result"],
                      expected_result="31^22", independent_basis="PRODUCT_OF_UNARY_DOT_PRODUCTS",
                      deformation_polynomial="(24+7*W_xx(T))^22; degree 66",
                      edge_layers=data["edge_layers"], actual_calls=8577,
                      point_evaluations=134, execution=str(execution),
                      bit_time_bound_status="COMPLEXITY_NOT_ESTABLISHED",
                      peak_space_bound_status="COMPLEXITY_NOT_ESTABLISHED")
    except (AssertionError, ValueError, KeyError, OSError) as exc:
        report["reason"] = str(exc)
    output.write_bytes(canonical(report))
    print(json.dumps({"status": report["status"], "output": str(output), "reason": report.get("reason")}))
    return int(not report["status"].startswith("PASS_"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
