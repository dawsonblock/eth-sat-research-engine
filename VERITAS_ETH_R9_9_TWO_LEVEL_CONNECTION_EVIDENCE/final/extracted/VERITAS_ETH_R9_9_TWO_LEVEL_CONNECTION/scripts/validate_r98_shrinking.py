"""Validate actual 484->44->4 child recursion via the external finite CLI."""

import argparse
import json
import os
import platform
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.tapered_v4.provenance import source_binding


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def run(output):
    if output.resolve().is_relative_to(ROOT):
        raise ValueError("shrinking evidence must be outside the source tree")
    output.parent.mkdir(parents=True, exist_ok=True)
    binding = source_binding()
    record = {
        "schema": "VERITAS_R98_SHRINKING_VALIDATION_V1",
        "status": "INCOMPLETE",
        "paper": source_registry(),
        "source": binding,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "source_eligible": False,
        "scaled_experiment": True,
        "source_qualified": False,
        "theorem_mode_enabled": False,
        "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
        "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
    }
    record["cases"] = []
    try:
        env = dict(
            os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1"
        )
        for name, filename in (
            ("matching", "r98_shrinking_484.json"),
            ("connected_cycle", "r98_shrinking_cycle484.json"),
        ):
            execution_path = output.parent / (
                "r98_shrinking_" + name + "_484_execution.json"
            )
            command = [
                sys.executable,
                "-m",
                "veritas.research.parent_child_r98.shrinking_cli",
                str(ROOT / "examples" / filename),
                "--output",
                str(execution_path),
            ]
            case = {"name": name, "command": command}
            record["cases"].append(case)
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            case["cli_exit_code"] = result.returncode
            if result.returncode:
                raise ValueError(
                    name
                    + " CLI failed: "
                    + result.stdout[-2000:]
                    + result.stderr[-1000:]
                )
            execution = json.loads(execution_path.read_text())
            require(
                execution["status"] == "PASS_FINITE_SCALED_SHRINKING_RECURSION",
                "shrinking execution status",
            )
            require(
                execution["result"] == [[1 << 484, 0]],
                "independent all-one tensor count differs",
            )
            require(
                execution["edge_layers"] == {"0": [484], "1": [0, 44], "2": [0, 4]},
                "actual edge layers differ",
            )
            require(
                execution["ledger"]["maximum_depth"] == 2,
                "actual recursive depth differs",
            )
            require(
                execution["ledger"]["nonshrinking_children"] == 0,
                "nonshrinking transition",
            )
            trace = execution["transitions"]
            require(len(trace) == 90, "complete two-node point trace missing")
            for point in trace:
                require(
                    point["child_count"] == len(point["child_edges"]) == 64,
                    "child omitted",
                )
                M = point["parent_edges"]
                require(
                    all(
                        64 * count <= 6 * M and count < M
                        for count in point["child_edges"]
                    ),
                    "actual child shrink failed",
                )
                require(
                    sum(point["child_edges"]) == 2 * M, "half-edge coverage differs"
                )
                require(point["group_load_bound_met"], "actual per-side load failure")
            require(execution["active_calls"] == 45, "active calls differ")
            require(
                execution["ledger"]["actual_calls"] == 5761,
                "not every child recursively invoked",
            )
            require(
                len(execution["hermite_recoveries"]) == 45,
                "active call recovery omitted",
            )
            require(
                not execution["source_qualified"]
                and not execution["theorem_mode_enabled"],
                "source claim escalation",
            )
            require(
                execution["implementation_source_sha256"] == binding["digest"],
                "execution source mismatch",
            )
            case.update(
                status=execution["status"],
                exact_result=execution["result"],
                expected_result="2^484 modulo 2^512",
                independent_result_basis="ALL_TENSORS_ONE_SO_ONE_PER_BOOLEAN_EDGE_ASSIGNMENT",
                family=execution["family"],
                recursive_depth=2,
                actual_calls=5761,
                active_calls=45,
                edge_layers=execution["edge_layers"],
                child_count_per_tuple=64,
                actual_child_shrink="PASS_EVERY_64_M_CHILD_LE_6_M",
                termination=execution["termination"],
                interpolation=execution["interpolation"],
                execution_file=execution_path.name,
                execution_sha256=sha256(execution_path.read_bytes()).hexdigest(),
            )
        require(source_binding() == binding, "source changed during validation")
        record.update(
            status="PASS_FINITE_SCALED_SHRINKING_RECURSION",
            case_count=2,
            actual_calls=sum(case["actual_calls"] for case in record["cases"]),
            actual_child_shrink="PASS_EVERY_64_M_CHILD_LE_6_M",
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
        RuntimeError,
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        record.update(status="FAILED_OR_INCONCLUSIVE", reason=str(exc))
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": record["status"],
                "output": str(output),
                "actual_calls": record.get("actual_calls"),
            }
        )
    )
    return 0 if record["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    raise SystemExit(run(parser.parse_args().output))
