#!/usr/bin/env python3
"""Run bounded Python/C++ differentials and independent certificate replay."""
from __future__ import annotations

import argparse
import itertools
import json
import os
import platform
import random
import sys
from unittest.mock import patch
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from veritas.research.eth_packing_v26 import cpp_backend  # noqa: E402
from veritas.research.eth_packing_v26.streaming import (  # noqa: E402
    _Work,
    _candidate_score,
    _pybind_tables,
    _side_code,
    construct_streaming_d3_packing,
)
from veritas.research.eth_packing_v26.streaming_check import (  # noqa: E402
    verify_streaming_d3_certificate,
)


def native_candidate_score(name, handle, edges, partial, *, r, a, vertex, label):
    if name == "cpp-pybind":
        rows, row_values, columns, column_values = _pybind_tables(
            edges, partial, r, a)
        word = list(label) if label else [0] * a
        text, work = handle.candidate_score(
            r, a, [edge[0] for edge in edges], [edge[1] for edge in edges],
            rows, row_values, columns, column_values, _side_code(vertex),
            vertex[1], word, cpp_backend.UINT64_MAX)
        return int(text), work
    return cpp_backend.candidate_score_cpp(
        edges, partial, r=r, a=a, D=r ** (2 * a), vertex=vertex,
        label=label, function=handle[1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(Path(os.environ["VERITAS_EVIDENCE_DIR"]) / "r9_1_differential.json")
                        if os.environ.get("VERITAS_EVIDENCE_DIR") else "validation/r9_1_differential.json")
    args = parser.parse_args()
    started = monotonic()
    record = {
        "schema": "VERITAS_ETH_R9_1_CPP_DIFFERENTIAL_V2",
        "status": "NOT_RUN",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpp_requested": True,
        "fixtures": [],
        "candidate_score_cases": 0,
        "independent_certificate_replays": 0,
        "python_lean_refinement_proven": False,
        "cpp_lean_refinement_proven": False,
        "universal_packing_proven": False,
        "theorem_mode_enabled": False,
    }
    try:
        selected, native = cpp_backend.resolve_score_backend("cpp")
        if selected not in cpp_backend.NATIVE_BACKEND_NAMES or native is None:
            raise RuntimeError("explicit C++ backend resolution did not select native code")
        backends = [(selected, native)]
        try:
            library_path = cpp_backend._find_library()
            library, function, batch = cpp_backend._load_library(str(library_path.resolve()))
            function._veritas_library = library
            batch._veritas_library = library
            if selected != "cpp-ctypes":
                backends.append(("cpp-ctypes", (library, function, batch)))
        except cpp_backend.CppBackendUnavailable:
            pass
        record["preferred_backend"] = selected
        record["backends_tested"] = [name for name, _ in backends]
        record["algorithm_version"] = cpp_backend.CPP_BATCH_ALGORITHM_VERSION

        rng = random.Random(9101)
        random_edges = [(rng.randrange(5), rng.randrange(5)) for _ in range(10)]
        fixtures = [
            ("required_trace", [(0, 0), (1, 1), (0, 1)], 2, 1),
            ("parallel_edges", [(0, 0), (0, 0), (1, 1)], 2, 1),
            ("permuted_edges", [(0, 1), (1, 1), (0, 0)], 2, 1),
            ("empty", [], 2, 1),
            ("single_edge", [(4, 4)], 3, 2),
            ("seed_9101", random_edges, 3, 1),
        ]
        all_ok = True
        for name, edges, radix, dimension in fixtures:
            python_run = construct_streaming_d3_packing(
                edges, r=radix, a=dimension, max_work=2_000_000,
                max_candidate_evaluations=100_000, score_backend="python")
            for backend_name, handle in backends:
                if backend_name == "cpp-ctypes":
                    with patch.object(cpp_backend, "_load_pybind_module",
                                      side_effect=cpp_backend.CppBackendUnavailable(
                                          "ctypes transport selected by validator")):
                        cpp_run = construct_streaming_d3_packing(
                            edges, r=radix, a=dimension, max_work=2_000_000,
                            max_candidate_evaluations=100_000, score_backend="cpp")
                else:
                    cpp_run = construct_streaming_d3_packing(
                        edges, r=radix, a=dimension, max_work=2_000_000,
                        max_candidate_evaluations=100_000, score_backend="cpp")
                fields = ("steps", "row_labels", "column_labels", "edges",
                          "initial_expected_square_scaled", "final_square_scaled",
                          "H_pad", "preconditions")
                equal = all(python_run.certificate[key] == cpp_run.certificate[key]
                            for key in fields)
                checked = verify_streaming_d3_certificate(
                    cpp_run.certificate, max_work=2_000_000,
                    max_candidate_evaluations=100_000)
                replay_ok = checked.get("valid") is True
                record["independent_certificate_replays"] += int(replay_ok)
                all_ok &= equal and replay_ok
                record["fixtures"].append({
                    "name": name,
                    "native_transport": backend_name,
                    "edge_count": len(edges),
                    "radix": radix,
                    "dimension": dimension,
                    "python_cpp_exact_result_equal": equal,
                    "independent_rational_replay_valid": replay_ok,
                    "selected_backend": cpp_run.certificate["score_backend"],
                    "python_work_metric": "d3-direct-pair-score-work-v1",
                    "cpp_work_metric": cpp_backend.CPP_BATCH_WORK_METRIC_VERSION,
                    "python_work_units": python_run.work_units,
                    "cpp_work_units": cpp_run.work_units,
                    "cpp_work_independently_recomputed": checked.get(
                        "independently_recomputed_construction_work_units"),
                    "expected_square_scaled": cpp_run.certificate["final_square_scaled"],
                })

        matrix_edges = [(0, 0), (1, 1), (0, 1)]
        vertices = [("R", 0), ("R", 1), ("C", 0), ("C", 1)]
        for backend_name, handle in backends:
            for states in itertools.product((None, 0, 1), repeat=4):
                partial = {(side, vertex, 0): value
                           for (side, vertex), value in zip(vertices, states)
                           if value is not None}
                for current in vertices:
                    for candidate in ((0,), (1,)):
                        py_work = _Work(None)
                        python_score = _candidate_score(
                            matrix_edges, partial, r=2, a=1, D=4,
                            vertex=current, label=candidate, work=py_work)
                        cpp_score, cpp_work = native_candidate_score(
                            backend_name, handle, matrix_edges, partial, r=2, a=1,
                            vertex=current, label=candidate)
                        record["candidate_score_cases"] += 1
                        if (cpp_score, cpp_work) != (python_score, py_work.used):
                            all_ok = False

        huge = 64 ** 128
        record["large_integer_exact_by_backend"] = {}
        for backend_name, handle in backends:
            large_score, large_work = native_candidate_score(
                backend_name, handle, [(0, 0)], {}, r=64, a=64,
                vertex=("", -1), label=())
            exact = large_score == huge and type(large_score) is int
            record["large_integer_exact_by_backend"][backend_name] = {
                "exact": exact, "work_units": large_work}
            all_ok &= exact
        record["large_integer_exact"] = all(
            item["exact"] for item in record["large_integer_exact_by_backend"].values())
        record["status"] = "PASS_FINITE_CPP_DIFFERENTIAL" if all_ok else "FAIL"
    except Exception as exc:  # retain an honest evidence file on every failure
        record["status"] = "FAIL"
        record["error"] = f"{type(exc).__name__}: {exc}"

    record["elapsed_seconds"] = round(monotonic() - started, 6)
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps(record, sort_keys=True, indent=2))
    return 0 if record["status"] == "PASS_FINITE_CPP_DIFFERENTIAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
