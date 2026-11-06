"""External validation of finite group counts, descendants and refusal budgets."""

import argparse
from hashlib import sha256
import json
from math import comb
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.bounded_integer_encoding import decode_integer_object
from veritas.research.parent_child_r98.model import canonical
from veritas.research.tapered_v4.provenance import source_binding


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(output):
    if output.resolve().is_relative_to(ROOT):
        raise ValueError("group evidence must be outside the source checkout")
    output.parent.mkdir(parents=True, exist_ok=True)
    binding = source_binding()
    report = {"schema": "VERITAS_R98_CONFIGURABLE_GROUP_VALIDATION_V1",
              "status": "INCOMPLETE", "source": binding, "cases": [],
              "source_group_count": 64, "source_qualified": False,
              "theorem_mode_enabled": False, "scaled_experiment": True,
              "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
              "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED"}
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")

    def execute(name, groups, *, general=False, input_path=None, extra=()):
        execution = output.parent / (name + ".json")
        module = "general_cli" if general else "shrinking_cli"
        input_path = input_path or ROOT / "examples/r98_shrinking_cycle484.json"
        command = [sys.executable, "-m", "veritas.research.parent_child_r98." + module,
                   str(input_path), "--groups", str(groups), "--output", str(execution), *extra]
        done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                              text=True, timeout=900)
        (output.parent / (name + ".log")).write_text(done.stdout + done.stderr)
        data = json.loads(execution.read_bytes(), object_hook=decode_integer_object)
        require(not data["source_qualified"] and not data["theorem_mode_enabled"],
                "group experiment escalated source qualification")
        case = {"name": name, "groups": groups, "command": command,
                "exit_code": done.returncode, "status": data["status"],
                "execution": execution.name,
                "sha256": sha256(execution.read_bytes()).hexdigest(),
                "actual_calls": data["ledger"]["actual_calls"]}
        report["cases"].append(case)
        return data, case

    try:
        data, case = execute("cycle484-groups512", 512, extra=("--max-calls", "1025"))
        require(case["exit_code"] == 0, "512-group cycle refused")
        require(data["result"] == [[1 << 484, 0]], "512-group exact result differs")
        require(data["edge_layers"] == {"0": [484], "1": [0, 4]}, "512-group actual edge layers")
        require(data["ledger"]["actual_calls"] == 1025, "512-group actual calls")
        require(data["group_preflight"]["required_calls"] == 1025, "512-group preflight calls")
        require(data["maximal_precision_used"] == 31488, "512-group precision")
        require(data["ledger"]["point_evaluations"] == 2, "complete constant points")
        for point in data["transitions"]:
            require(point["child_count"] == len(point["child_edges"]) == 512, "child omitted")
            require(sum(point["child_edges"]) == 968, "half-edge coverage differs")
            require(all(512 * n <= 6 * 484 for n in point["child_edges"]), "actual shrink differs")
            require((point["cross_group_pairs"], point["retained_modes"], point["complete_tuple_count"])
                    == (242, 0, 1), "constant-point mode accounting")
        case.update(exact_result=data["result"], edge_layers=data["edge_layers"],
                    max_precision=data["maximal_precision_used"])

        for groups in (128, 256, 1024):
            data, case = execute("cycle484-refused-groups" + str(groups), groups)
            require(case["exit_code"] == 1 and "result" not in data, "invalid descendants returned a result")
            require(data["status"] == "INCONCLUSIVE_DESCENDANT_PACKING", "wrong descendant refusal")
            require(data["ledger"]["actual_calls"] == 0, "descendant refusal occurred after production calls")
            case["preflight"] = data["group_preflight"]

        data, case = execute("cycle484-insufficient-calls", 512, extra=("--max-calls", "1024"))
        require(case["exit_code"] == 1 and data["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
                and "result" not in data and data["ledger"]["actual_calls"] == 0,
                "insufficient total call budget accepted")

        data, case = execute("cycle484-general-groups512", 512, general=True)
        require(case["exit_code"] == 1 and "result" not in data and case["actual_calls"] == 0,
                "general tuple overflow was not refused")
        require(data["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", "wrong general refusal")
        require(data["group_preflight"]["nonzero_point_tuples"] == comb(31488 + 242 - 1, 242),
                "complete general tuple count differs")
        case["preflight"] = data["group_preflight"]

        data, case = execute("matching22-general-groups65", 65, general=True,
                             input_path=ROOT / "examples/r98_general_matching22.json")
        require(case["exit_code"] == 0 and data["result"] == [[31**22, 0, 0, 0, 0, 0, 0]],
                "65-group nonconstant matching result")
        require(case["actual_calls"] == data["group_preflight"]["required_calls"] == 8711,
                "65-group complete call count")
        require(data["ledger"]["point_evaluations"] == 134, "65-group full grid missing")
        case.update(exact_result=data["result"], edge_layers=data["edge_layers"])

        # An admitted case at the upper group limit, with near-limit precision.
        large_input = output.parent / "cycle1000-input.json"
        large_input.write_bytes(canonical({
            "root_s": 1024, "precision": 1024, "extension_degree": 2, "edges": 1000,
            "vertices": [
                {"side": "row", "ports": [2*i, 2*i+1], "table": [1]*4}
                for i in range(500)
            ] + [
                {"side": "column", "ports": [2*i+1, 2*((i+1) % 500)], "table": [1]*4}
                for i in range(500)
            ],
        }))
        data, case = execute("cycle1000-groups1024", 1024, input_path=large_input)
        require(case["exit_code"] == 0 and data["result"] == [[1 << 1000, 0]],
                "upper-group-limit exact contraction differs")
        require(data["edge_layers"] == {"0": [1000], "1": [0, 4]}, "upper-group-limit shrink")
        require(case["actual_calls"] == data["group_preflight"]["required_calls"] == 2049,
                "upper-group-limit actual calls")
        require(data["maximal_precision_used"] == 65024, "upper-group-limit precision")
        case.update(exact_result=data["result"], edge_layers=data["edge_layers"], max_precision=65024)
        require(source_binding() == binding, "source changed during group validation")
        report["status"] = "PASS_FINITE_CONFIGURABLE_GROUP_RECURSION"
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        report.update(status="FAILED_OR_INCONCLUSIVE", reason=str(exc))
    output.write_bytes(canonical(report))
    print(json.dumps({"status": report["status"], "cases": len(report["cases"]),
                      "reason": report.get("reason"), "output": str(output)}))
    return int(not report["status"].startswith("PASS_"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
