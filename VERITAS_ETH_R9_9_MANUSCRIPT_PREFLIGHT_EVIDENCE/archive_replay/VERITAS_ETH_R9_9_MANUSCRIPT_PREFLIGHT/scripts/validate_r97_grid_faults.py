"""Attack a saved complete grid through the public replay command."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grid", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    saved = json.loads(args.grid.read_text())
    script = Path(__file__).with_name("validate_r97_paper.py")
    attacks = {}
    for name in ("missing_point", "missing_term", "same_length_point_substitution",
                 "wrong_recovery", "missing_group", "changed_precision", "source_pin", "truncated_json"):
        obj = deepcopy(saved)
        point = obj["points"][0]
        if name == "missing_point":
            obj["points"].pop()
        elif name == "missing_term":
            point["child_sum"]["terms"].pop()
        elif name == "same_length_point_substitution":
            obj["points"][1] = obj["points"][0]
        elif name == "wrong_recovery":
            obj["result"][0] += 1
        elif name == "missing_group":
            point["child_sum"]["terms"][0]["groups"].pop()
        elif name == "changed_precision":
            point["used"]["child_precision"] -= 1
        elif name == "source_pin":
            point["paper_source_sha256"] = "0" * 64
        attacks[name] = json.dumps(obj) if name != "truncated_json" else json.dumps(obj)[:100]
    records = []
    with tempfile.TemporaryDirectory() as temp:
        for name, content in attacks.items():
            path = Path(temp) / "bad.json"
            path.write_text(content)
            start = time.monotonic()
            proc = subprocess.run([sys.executable, "-O", str(script), "--verify", str(path)],
                                  text=True, capture_output=True, timeout=90)
            try:
                report = json.loads(proc.stdout)
            except ValueError:
                report = {"status": "INVALID_VALIDATOR_OUTPUT"}
            records.append({"attack": name, "exit_code": proc.returncode,
                            "wall_seconds": time.monotonic() - start,
                            "response": report,
                            "rejected_without_result": proc.returncode == 1 and
                            report.get("status") == "INCONCLUSIVE_OR_INVALID_GRID" and "result" not in report})
    good = all(row["rejected_without_result"] for row in records)
    out = {"status": "PASS_NEGATIVE_GRID_CHECKS" if good else "FAIL", "executed": len(records),
           "python_optimized": True, "cases": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"status": out["status"], "executed": len(records)}))
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())
