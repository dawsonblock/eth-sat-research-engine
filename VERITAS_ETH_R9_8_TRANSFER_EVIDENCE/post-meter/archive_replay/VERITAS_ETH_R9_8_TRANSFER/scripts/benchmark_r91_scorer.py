#!/usr/bin/env python3
"""Reproducible scorer benchmark: Python reference, C++ direct, C++ batch.

All three backends are run on identical inputs and every score is compared
exactly.  Wall-clock time, CPU time, peak RSS, candidate counts and work units
are recorded.  Nothing here is a complexity proof; see
``docs/R91_COMPLEXITY.md`` for the analysis and its assumptions.

Usage::

    python scripts/benchmark_r91_scorer.py --output validation/r91_benchmarks.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time

try:
    import resource
except ImportError:  # Windows
    resource = None

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from veritas.research.eth_packing_v26 import cpp_backend  # noqa: E402
from veritas.research.eth_packing_v26.streaming import (  # noqa: E402
    _candidate_score,
    _ordered_vertices,
    _pybind_tables,
    _side_code,
    estimated_streaming_work,
)


class Counter:
    def __init__(self, limit=None):
        self.limit = limit
        self.used = 0

    def tick(self, amount=1):
        self.used += amount


def peak_rss_bytes():
    if resource is None:
        return None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    value = int(usage.ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def make_instance(edges, r, a, seed):
    rng = random.Random(seed)
    partial = {}
    for side, ident in _ordered_vertices(edges):
        if rng.random() < 0.5:
            for d in range(a):
                partial[(side, ident, d)] = rng.randrange(r)
    return partial


def python_step(edges, partial, r, a):
    counter = Counter()
    scores = []
    for side, ident in _ordered_vertices(edges):
        for label in __import__("itertools").product(range(r), repeat=a):
            counter.tick()
            scores.append(_candidate_score(edges, partial, r=r, a=a, D=r ** (2 * a),
                                           vertex=(side, ident), label=label,
                                           work=counter))
    return scores, counter.used


def cpp_direct_step(edges, partial, r, a, name, handle):
    counter = Counter()
    scores = []
    for side, ident in _ordered_vertices(edges):
        for label in __import__("itertools").product(range(r), repeat=a):
            counter.tick()
            if name == "cpp-pybind":
                text, charged = handle.candidate_score(
                    r, a, [edge[0] for edge in edges], [edge[1] for edge in edges],
                    *_pybind_tables(edges, partial, r, a), _side_code((side, ident)),
                    ident, list(label), cpp_backend.UINT64_MAX)
                score = int(text)
            else:
                score, charged = cpp_backend.candidate_score_cpp(
                    edges, partial, r=r, a=a, D=r ** (2 * a), vertex=(side, ident),
                    label=label, max_work=None, function=handle[1])
            counter.tick(charged)
            scores.append(score)
    return scores, counter.used


def cpp_batch_step(edges, partial, r, a, name, handle):
    counter = Counter()
    scores = []
    for side, ident in _ordered_vertices(edges):
        if name == "cpp-pybind":
            batch, _parent, charged = cpp_backend.vertex_scores_pybind(
                edges, partial, r=r, a=a, vertex=(side, ident), module=handle)
        else:
            batch, _parent, charged = cpp_backend.vertex_scores_ctypes(
                edges, partial, r=r, a=a, vertex=(side, ident), handle=handle)
        counter.tick(charged)
        scores.extend(batch)
    return scores, counter.used


def timed(function, repeats):
    samples = []
    cpu = []
    result = None
    for _ in range(repeats):
        start_wall = time.perf_counter()
        start_cpu = time.process_time()
        result = function()
        samples.append(time.perf_counter() - start_wall)
        cpu.append(time.process_time() - start_cpu)
    return result, {
        "wall_seconds_median": statistics.median(samples),
        "wall_seconds_min": min(samples),
        "cpu_seconds_median": statistics.median(cpu),
        "repeats": repeats,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/r91_benchmarks.json")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261103)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")

    try:
        backend_name, handle = cpp_backend.resolve_score_backend("cpp")
    except cpp_backend.CppBackendUnavailable as exc:
        print(f"native backend unavailable: {exc}", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    instances = []
    for label, rows, cols, m, r, a in (
        ("tiny-r2-a1", 3, 3, 6, 2, 1),
        ("small-r2-a1", 6, 6, 24, 2, 1),
        ("small-r3-a1", 5, 5, 24, 3, 1),
        ("medium-r2-a2", 6, 6, 40, 2, 2),
        ("medium-r3-a2", 5, 5, 36, 3, 2),
    ):
        edges = [(rng.randrange(rows), rng.randrange(cols)) for _ in range(m)]
        instances.append((label, edges, r, a))

    records = []
    for label, edges, r, a in instances:
        partial = make_instance(edges, r, a, args.seed)
        reference, ref_meta = timed(lambda: python_step(edges, partial, r, a), args.repeats)
        direct, direct_meta = timed(
            lambda: cpp_direct_step(edges, partial, r, a, backend_name, handle), args.repeats)
        batch, batch_meta = timed(
            lambda: cpp_batch_step(edges, partial, r, a, backend_name, handle), args.repeats)
        ref_scores, ref_work = reference
        direct_scores, direct_work = direct
        batch_scores, batch_work = batch
        scores_match = ref_scores == direct_scores == batch_scores
        record = {
            "instance": label,
            "edges": len(edges),
            "vertices": len(_ordered_vertices(edges)),
            "r": r,
            "a": a,
            "candidates": len(_ordered_vertices(edges)) * (r ** a),
            "pair_count": len(edges) * (len(edges) - 1) // 2,
            "estimated_reference_work": estimated_streaming_work(edges, r=r, a=a),
            "scores_equal": scores_match,
            "direct_work_matches_reference": ref_work == direct_work,
            "score_digest": sum(ref_scores),
            "python_reference": {**ref_meta, "work_units": ref_work,
                                 "work_metric_version": "d3-direct-pair-score-work-v1"},
            "cpp_direct": {**direct_meta, "work_units": direct_work,
                            "work_metric_version": "d3-direct-pair-score-work-v1"},
            "cpp_batch": {**batch_meta, "work_units": batch_work,
                          "work_metric_version": cpp_backend.CPP_BATCH_WORK_METRIC_VERSION},
            "speedup_direct_over_python": (
                ref_meta["wall_seconds_median"] / direct_meta["wall_seconds_median"]
                if scores_match and direct_meta["wall_seconds_median"] else None),
            "speedup_batch_over_python": (
                ref_meta["wall_seconds_median"] / batch_meta["wall_seconds_median"]
                if scores_match and batch_meta["wall_seconds_median"] else None),
            "speedup_batch_over_direct": (
                direct_meta["wall_seconds_median"] / batch_meta["wall_seconds_median"]
                if scores_match and batch_meta["wall_seconds_median"] else None),
        }
        records.append(record)
        print(f"{label}: equal={record['scores_equal']} "
              f"python={ref_meta['wall_seconds_median']:.4f}s "
              f"direct={direct_meta['wall_seconds_median']:.4f}s "
              f"batch={batch_meta['wall_seconds_median']:.4f}s", file=sys.stderr)

    payload = {
        "schema": "VERITAS_ETH_R91_SCORER_BENCHMARK_V1",
        "claim": "MEASURED_WALL_CLOCK_ON_IDENTICAL_INPUTS",
        "qualification": (
            "Timings are machine-specific observations, not asymptotic claims. "
            "The asymptotic analysis is separate and conditional."
        ),
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "processor": platform.processor(),
            "native_backend": backend_name,
            "native_algorithm_version": getattr(handle, "ALGORITHM_VERSION", None)
            if backend_name == "cpp-pybind" else cpp_backend.CPP_BATCH_ALGORITHM_VERSION,
            "cpu_count": os.cpu_count(),
        },
        "peak_rss_bytes": peak_rss_bytes(),
        "peak_rss_is_os_enforced_limit": False,
        "repeats": args.repeats,
        "seed": args.seed,
        "all_scores_exact": all(r["scores_equal"] for r in records),
        "all_direct_work_metrics_match": all(
            r["direct_work_matches_reference"] for r in records),
        "records": records,
        "limitations": [
            "No memory limit is enforced; peak RSS is the process maximum.",
            "Wall-clock includes Python call overhead for the native backends.",
            "Instances are small enough to run the pure-Python reference.",
        ],
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}", file=sys.stderr)
    return 0 if (payload["all_scores_exact"] and
                 payload["all_direct_work_metrics_match"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
