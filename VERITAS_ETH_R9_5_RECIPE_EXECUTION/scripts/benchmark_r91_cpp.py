#!/usr/bin/env python3
"""Measure bounded Python and C++ D3 packing executions in isolated workers.

The output separates elapsed/CPU time, per-process peak RSS, and the algorithm's
legacy scalar work metric. It is a finite benchmark, not a bit-complexity bound.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

try:
    import resource
except ImportError:  # Windows has no stdlib resource module.
    resource = None


def _rss_record():
    try:
        if resource is None:
            raise AttributeError("resource module is unavailable")
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError, ValueError):
        return {"peak_rss": None, "peak_rss_unit": None}
    # macOS reports bytes; Linux and the other supported Unix runners report KiB.
    unit = "bytes" if sys.platform == "darwin" else "KiB"
    return {"peak_rss": value, "peak_rss_unit": unit}


def _edges(seed: int, count: int):
    rng = random.Random(seed)
    side_size = max(5, count // 3)
    return [(rng.randrange(side_size), rng.randrange(side_size))
            for _ in range(count)]


def _worker(backend: str, seed: int, edge_count: int):
    sys.path.insert(0, str(ROOT / "src"))
    from veritas.research.eth_packing_v26.streaming import construct_streaming_d3_packing

    edges = _edges(seed, edge_count)
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    result = construct_streaming_d3_packing(
        edges, r=2, a=1, max_work=5_000_000,
        max_candidate_evaluations=100_000, score_backend=backend)
    wall = time.perf_counter() - wall_start
    cpu = time.process_time() - cpu_start
    cert = result.certificate
    return {
        "backend": backend,
        "seed": seed,
        "edge_count": edge_count,
        "vertex_count": len(cert["row_labels"]) + len(cert["column_labels"]),
        "candidate_evaluations": len(cert["steps"]) * (cert["r"] ** cert["a"]),
        "work_units": result.work_units,
        "estimated_work_units": result.estimated_work_units,
        "final_scaled_score": cert["final_square_scaled"],
        "wall_seconds": wall,
        "cpu_seconds": cpu,
        **_rss_record(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/r9_1_benchmarks.json")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--worker", choices=("python", "cpp"))
    parser.add_argument("--seed", type=int, default=9102)
    parser.add_argument("--edges", type=int, default=36)
    args = parser.parse_args()
    if args.repeats < 1 or args.edges < 1:
        parser.error("--repeats and --edges must be positive")

    if args.worker:
        try:
            print(json.dumps(_worker(args.worker, args.seed, args.edges), sort_keys=True))
            return 0
        except Exception as exc:
            print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}))
            return 2

    record = {
        "schema": "VERITAS_ETH_R9_1_BENCHMARKS_V1",
        "status": "NOT_RUN",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "compiler": os.environ.get("VERITAS_D3_CPP_COMPILER", "not recorded"),
        "method": "one fresh subprocess per backend/repeat; ru_maxrss is per child process",
        "fixtures": [],
        "metric_limitations": [
            "work_units are the existing scalar operation metric, not bit operations",
            "no asymptotic complexity or theorem qualification is inferred",
        ],
        "python_lean_refinement_proven": False,
        "cpp_lean_refinement_proven": False,
        "theorem_mode_enabled": False,
    }
    ok = True
    for edge_count in sorted({max(8, args.edges // 2), args.edges}):
        runs = {"python": [], "cpp": []}
        for backend in runs:
            for _ in range(args.repeats):
                command = [sys.executable, str(Path(__file__).resolve()),
                           "--worker", backend, "--seed", str(args.seed),
                           "--edges", str(edge_count)]
                completed = subprocess.run(command, cwd=ROOT, text=True,
                                           capture_output=True, check=False)
                try:
                    measurement = json.loads(completed.stdout.strip().splitlines()[-1])
                except (ValueError, IndexError):
                    measurement = {"status": "FAIL", "stderr": completed.stderr,
                                   "stdout": completed.stdout,
                                   "return_code": completed.returncode}
                if completed.returncode != 0 or measurement.get("status") == "FAIL":
                    ok = False
                runs[backend].append(measurement)
        valid = all(len(items) == args.repeats and all(
            item.get("backend") == backend for item in items
        ) for backend, items in runs.items())
        equivalent = valid and all(
            item["final_scaled_score"] == runs["python"][0]["final_scaled_score"] and
            item["work_units"] == runs["python"][0]["work_units"]
            for items in runs.values() for item in items
        )
        ok &= equivalent
        record["fixtures"].append({
            "seed": args.seed,
            "edge_count": edge_count,
            "repeats_per_backend": args.repeats,
            "exact_outputs_and_work_equal": equivalent,
            "runs": runs,
        })
    record["status"] = "PASS_FINITE_BENCHMARK" if ok else "FAIL"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps(record, sort_keys=True, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
