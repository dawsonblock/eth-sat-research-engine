#!/usr/bin/env python3
"""R9.6 measurement harness: packet coefficients and bounded #SAT.

Two independent sections, reported separately because their work units are not
comparable:

``packet_coefficients``
    Compares the R9.6 first-order product rule and truncated sparse DP against
    the deliberately naive Cartesian reference (which has the shape of the R9.5
    evaluator).  Wall time, CPU time, peak RSS, work units and the exact result
    are recorded.  Work-unit *definitions* differ between the two evaluators, so
    the ratio of work units is not a speedup claim; only wall time on identical
    inputs is comparable.

``sharp_sat``
    A reproducible scaling series of #SAT instances whose exact counts are
    independently confirmed by brute-force enumeration where the variable count
    permits it.  It reports correctness, refusals, nodes, wall and CPU time.

Nothing here claims subexponential runtime, polynomial space, or competitive
solver performance.  Every measured quantity is bounded and every refusal is
reported as a refusal.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from veritas.core.cnf import CNF
from veritas.research.tapered_v4.packet_coefficients import (
    row_factors, sparse_dp, unpruned_reference)
from veritas.research.tapered_v4.source_recipes import (
    Arithmetic, EntryBudget, EntryLimits, compile_entry, evaluate_compiled)
from veritas.research.tapered_v4.source_state import (
    SourceAdmissionError, SourceTensorReference)
from veritas.research.tapered_v4.source_recipes import SCHEMA as ENTRY_SCHEMA
from veritas.solvers.reference import ResourceLimit, exhaustive_count, solve
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing


def _peak_rss_bytes():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return int(usage.ru_maxrss * 1024) if sys.platform != "darwin" else int(usage.ru_maxrss)


def _cpu_seconds():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def first_order_recipe(rows_count, *, polynomial=7, jet_length=1, precision=3):
    e = polynomial.bit_length() - 1
    one = [[1] + [0] * (e - 1) for _ in range(jet_length)]
    data = [list(range(rows_count)), [], [[] for _ in range(rows_count)],
            [[1, [one for _ in range(rows_count)]]], []]
    payload = {"schema": ENTRY_SCHEMA, "kind": "packet", "arity": rows_count,
               "creation_precision": precision, "polynomial": polynomial,
               "jet_length": jet_length, "data": data}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    return SourceTensorReference(rows_count, precision, polynomial, jet_length,
                                 ENTRY_SCHEMA + ":packet", raw)


def packet_benchmark(rows_counts, repeats=5):
    rows = []
    for rows_count in rows_counts:
        reference = first_order_recipe(rows_count)
        bits = (0,) * rows_count
        # R9.6 production path.
        fast_times, fast_work = [], []
        for _ in range(repeats):
            start = time.perf_counter()
            budget = EntryBudget(EntryLimits())
            compiled = compile_entry(reference, budget)
            value = evaluate_compiled(compiled, bits, 3, budget)
            fast_times.append(time.perf_counter() - start)
            fast_work.append(budget.used)
        # Naive Cartesian path with the same ring arithmetic.
        slow_times, slow_work, slow_value, slow_status = [], [], None, "OK"
        for _ in range(repeats):
            start = time.perf_counter()
            budget = EntryBudget(EntryLimits())
            try:
                compiled = compile_entry(reference, budget)
                ring = JetRing(ExtensionRing(3, 7), 1)
                ar = Arithmetic(ring, budget)
                factors = row_factors(*compiled.data[:3], compiled.data[3], bits,
                                      ring, ar, budget,
                                      selected=[(1, compiled.data[3][0][1])])
                slow_value = unpruned_reference(factors, (1,), ring, ar, budget)
            except SourceAdmissionError:
                slow_status = "INCONCLUSIVE_RESOURCE_LIMIT"
            slow_times.append(time.perf_counter() - start)
            slow_work.append(budget.used)
        rows.append({
            "rows": rows_count,
            "result": [list(row) for row in value],
            "naive_result": None if slow_value is None else [list(row) for row in slow_value],
            "results_agree": slow_value is None or slow_value == value,
            "r96_wall_seconds_median": sorted(fast_times)[repeats // 2],
            "naive_wall_seconds_median": sorted(slow_times)[repeats // 2],
            "r96_work_units_median": sorted(fast_work)[repeats // 2],
            "naive_work_units_median": sorted(slow_work)[repeats // 2],
            "r96_status": "EXACT",
            "naive_status": slow_status,
            "work_unit_definition_note": ("work units count ring operations with "
                                          "different multiplicities in the two "
                                          "paths; only wall time is comparable"),
        })
    return {"algorithm": "first_order_vs_unpruned_cartesian", "rows": rows,
            "all_results_agree": all(row["results_agree"] for row in rows)}


def _random_3cnf(rng, n, m):
    clauses = []
    while len(clauses) < m:
        variables = rng.sample(range(1, n + 1), 3)
        clauses.append(tuple(v if rng.random() < 0.5 else -v for v in variables))
    return CNF(n, tuple(clauses))


def _bounded_density_3cnf(rng, n, occurrences=4):
    slots = []
    for variable in range(1, n + 1):
        for _ in range(occurrences):
            slots.append(variable)
    rng.shuffle(slots)
    clauses = []
    for index in range(0, len(slots) - 2, 3):
        triple = slots[index:index + 3]
        if len(set(triple)) != 3:
            continue
        clauses.append(tuple(v if rng.random() < 0.5 else -v for v in triple))
    return CNF(n, tuple(clauses))


def _unsatisfiable_pair(rng, n):
    clauses = [(1,), (-1,)]
    while len(clauses) < n:
        a, b = rng.sample(range(2, max(3, n)), 2)
        clauses.append((a, -b))
    return CNF(max(3, n), tuple(clauses))


def sharp_sat_benchmark():
    rng = random.Random(20261105)
    families = []
    for label, builder, sizes in (
            ("random_3cnf_ratio_4_2", lambda n: _random_3cnf(rng, n, int(round(4.2 * n))),
             (8, 10, 12, 14, 16, 20, 24, 28)),
            ("bounded_density_occurrence_4", lambda n: _bounded_density_3cnf(rng, n),
             (9, 12, 15, 18, 21, 24, 27, 30)),
            ("unsatisfiable_units", lambda n: _unsatisfiable_pair(rng, n),
             (6, 9, 12, 15, 18)),
            ("sparse_ratio_1_0", lambda n: _random_3cnf(rng, n, n),
             (10, 14, 18, 22, 26))):
        cases = []
        for n in sizes:
            cnf = builder(n)
            truth = exhaustive_count(cnf, max_vars=18) if cnf.n <= 18 else None
            start_wall = time.perf_counter()
            start_cpu = _cpu_seconds()
            try:
                result = solve(cnf, count=True, timeout_s=20.0, max_nodes=2_000_000)
                status = result.status
                count = result.count
                nodes = result.nodes
            except ResourceLimit as exc:
                status, count, nodes = "INCONCLUSIVE_RESOURCE_LIMIT", None, None
            wall = time.perf_counter() - start_wall
            cpu = _cpu_seconds() - start_cpu
            cases.append({
                "variables": cnf.n, "clauses": len(cnf.clauses),
                "status": status, "count": count, "nodes": nodes,
                "brute_force_count": truth,
                "correct": (None if truth is None or count is None else count == truth),
                "wall_seconds": wall, "cpu_seconds": cpu,
            })
        families.append({"family": label, "cases": cases})
    # Fail-closed probe: the same hard instance under an inadequate node cap.
    hard = _bounded_density_3cnf(rng, 30)
    try:
        probe = solve(hard, count=True, timeout_s=5.0, max_nodes=100)
        probe_status = probe.status
        probe_count = probe.count
    except ResourceLimit:
        probe_status, probe_count = "INCONCLUSIVE_RESOURCE_LIMIT", None
    return {
        "refusal_probe": {"variables": hard.n, "max_nodes": 100,
                          "status": probe_status, "count": probe_count,
                          "returns_a_value": probe_count is not None},
        "families": families,
        "all_checked_cases_correct": all(case["correct"] is not False
                                         for family in families
                                         for case in family["cases"]),
        "refusals": sum(1 for family in families for case in family["cases"]
                        if case["status"].startswith("INCONCLUSIVE")),
        "cases": sum(len(family["cases"]) for family in families),
        "note": ("counts are exact integers; brute force is the independent "
                 "ground truth where the variable cap allows it"),
    }


def parent_child_benchmark():
    """Record the finite parent-to-all-children coverage numbers."""
    from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
    from veritas.research.eth_arithmetic.gf2 import first_irreducible
    from veritas.research.eth_recursive_contraction_v39.described_network import (
        CreatedDenseTensor, DescribedNetwork, DescribedVertex)
    from veritas.research.tapered_v4.parent_child import (
        ParentChildLimits, build_certificate, verify_certificate)
    polynomial = first_irreducible(2)
    ring = JetRing(ExtensionRing(4, polynomial), 1)
    tensor = lambda arity, values: CreatedDenseTensor(arity, tuple(
        CreationJetEntry.capture(ring, ring.elem(value)) for value in values))
    parent = DescribedNetwork(2, (
        DescribedVertex("row", "r", (0, 1),
                        tensor(2, ([[1, 1]], [[3, 0]], [[2, 1]], [[1, 1]]))),
        DescribedVertex("column", "c0", (0,), tensor(1, ([[2, 1]], [[1, 0]]))),
        DescribedVertex("column", "c1", (1,), tensor(1, ([[1, 1]], [[4, 1]]))),
    ))
    limits = ParentChildLimits(max_edges=4, max_points=8, max_tuples=512,
                               max_work=2_000_000)
    start = time.perf_counter()
    document = build_certificate(parent, precision=4, jet_length=1, a=1, u=1,
                                 radix=4, extension_degree=2, limits=limits)
    build_seconds = time.perf_counter() - start
    start = time.perf_counter()
    verdict = verify_certificate(document, parent=parent, limits=limits)
    verify_seconds = time.perf_counter() - start
    return {
        "parent_edges": parent.edges,
        "points_checked": verdict["points_checked"],
        "points_required": verdict["points_required"],
        "classification": verdict["classification"],
        "identity_verified": verdict["valid"],
        "admissible_tuples_per_point": [entry["cardinality"]
                                        for entry in document["modes"]["domains"]],
        "build_seconds": build_seconds,
        "verify_seconds": verify_seconds,
        "theorem_mode_enabled": verdict["theorem_mode_enabled"],
        "scope": verdict["scope"],
    }


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(
        Path(os.environ["VERITAS_EVIDENCE_DIR"]) / "r96_benchmarks.json"
        if os.environ.get("VERITAS_EVIDENCE_DIR") else
        ROOT / "validation" / "r96_benchmarks.json"))
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args(argv)
    started = time.perf_counter()
    report = {
        "schema": "VERITAS_R96_BENCHMARK_V1",
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "packet_coefficients": packet_benchmark((4, 8, 12, 16), args.repeats),
        "sharp_sat": sharp_sat_benchmark(),
        "parent_child_identity": parent_child_benchmark(),
        "peak_rss_bytes": _peak_rss_bytes(),
        "elapsed_seconds": None,
        "claims": {
            "subexponential_runtime_proven": False,
            "polynomial_space_proven": False,
            "competitive_solver_performance_claimed": False,
            "complete_bit_complexity_accounted": False,
        },
        "limitations": [
            "Peak RSS is the process high-water mark for the whole harness.",
            "Work units exclude interpolation, big-integer bit costs, "
            "verification and allocator overhead.",
            "Wall times on one machine are not a portability claim.",
        ],
    }
    report["elapsed_seconds"] = time.perf_counter() - started
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"output": str(target),
                      "packet_agree": report["packet_coefficients"]["all_results_agree"],
                      "sat_correct": report["sharp_sat"]["all_checked_cases_correct"],
                      "cases": report["sharp_sat"]["cases"],
                      "refusals": report["sharp_sat"]["refusals"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
