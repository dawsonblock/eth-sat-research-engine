"""Count-mode micro-benchmark suite with decomposition ledger totals."""
from __future__ import annotations

import time
from typing import Any

from veritas.core.cnf import CNF
from veritas.research.sat_external_baselines import run_baseline_matrix
from veritas.research.sat_micro_generators import (
    adversarial_grid_cases,
    micro_generator_suite,
)
from veritas.research.sat_residual_equivalence import (
    count_by_residual_equivalence,
    probe_branch_orders_benchmark,
)
from veritas.research.sat_universal import run_universal_sat


def residual_compression_row(report: dict[str, Any], *, cnf: CNF) -> dict[str, Any]:
    rc = (report.get("reduction") or {}).get("residual_compression") or {}
    n = cnf.n
    classes = rc.get("distinct_residual_classes")
    ratio = rc.get("compression_ratio_branches_over_classes")
    vs_2n = rc.get("compression_vs_2n")
    if vs_2n is None and classes and n <= 20:
        vs_2n = (1 << n) / classes
    return {
        "distinct_residual_classes": classes,
        "full_assignment_branches": rc.get("full_assignment_branches"),
        "compression_ratio_branches_over_classes": ratio,
        "compression_vs_2n": vs_2n,
        "residual_probe_status": rc.get("status"),
        "agreement_with_exhaustive": rc.get("agreement_with_exhaustive"),
    }


def decomposition_metrics_from_report(
    report: dict[str, Any], *, cnf: CNF | None = None
) -> dict[str, Any]:
    """Extract Phase C proxy ledger fields for benchmarks (not a theorem)."""
    phase_c = (report.get("reduction") or {}).get("phase_c_split") or {}
    metrics = dict(phase_c.get("decomposition_metrics") or {})
    steps = (report.get("decomposition_work") or {}).get("steps") or []
    direct_nodes = None
    for step in steps:
        if step.get("name") == "direct_exact_fallback":
            direct_nodes = step.get("w_new") or step.get("w_transform")
            break
    if metrics and direct_nodes is not None:
        split_new = metrics.get("w_new_proxy_split")
        metrics["w_direct_proxy"] = direct_nodes
        metrics["split_beats_direct_nodes"] = (
            split_new is not None and direct_nodes is not None and split_new < direct_nodes
        )
    preprocess = phase_c.get("preprocess") or {}
    metrics.setdefault("preprocess_status", preprocess.get("status"))
    child_engines = [
        (c.get("child_solve") or {}).get("child_engine_used")
        or (c.get("child_solve") or {}).get("engine")
        for c in (phase_c.get("components") or [])
    ]
    metrics["child_engines"] = child_engines
    metrics["any_count_dag_child"] = any(e == "count_dag_certificate" for e in child_engines)
    metrics["any_residual_equivalence_child"] = any(
        e == "residual_equivalence" for e in child_engines
    )
    tel = phase_c.get("child_engine_telemetry") or {}
    metrics["phase_c_residual_wins"] = tel.get("residual_equivalence_wins")
    metrics["phase_c_direct_lane_fallback_children"] = tel.get(
        "direct_lane_fallback_children"
    )
    if cnf is not None:
        metrics.update(residual_compression_row(report, cnf=cnf))
    return metrics


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = (len(sorted_vals) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def adversarial_grid_compression_summary(
    *,
    n_min: int = 6,
    n_max: int = 10,
    seeds: tuple[int, ...] = (0, 1, 2),
) -> dict[str, Any]:
    """Benchmark-only grid: ``compression_vs_2n`` percentiles (no speedup claim)."""
    rows: list[dict[str, Any]] = []
    vs_2n_values: list[float] = []
    agree = 0
    for name, cnf, family in adversarial_grid_cases(n_min=n_min, n_max=n_max, seeds=seeds):
        rep = count_by_residual_equivalence(cnf)
        vs = rep.get("compression_vs_2n")
        if rep.get("agreement"):
            agree += 1
        row = {
            "case": name,
            "family": family,
            "n": cnf.n,
            "distinct_residual_classes": rep.get("distinct_residual_classes"),
            "compression_vs_2n": vs,
            "agreement": rep.get("agreement"),
        }
        rows.append(row)
        if vs is not None and rep.get("agreement"):
            vs_2n_values.append(float(vs))
    vs_2n_values.sort()
    return {
        "schema": "VERITAS_SAT_ADVERSARIAL_GRID_COMPRESSION_V1",
        "n_min": n_min,
        "n_max": n_max,
        "seeds": list(seeds),
        "case_count": len(rows),
        "agreement_count": agree,
        "cases": rows,
        "compression_vs_2n_percentiles": {
            "p25": _percentile(vs_2n_values, 0.25),
            "p50": _percentile(vs_2n_values, 0.50),
            "p75": _percentile(vs_2n_values, 0.75),
            "max": vs_2n_values[-1] if vs_2n_values else None,
            "min": vs_2n_values[0] if vs_2n_values else None,
        },
        "theorem_backed": False,
        "universal_speedup_claimed": False,
        "qualification": "branch_order_default_prefix_research_only",
    }


def e2_generator_baseline_summary(
    *,
    external_timeout_s: float = 8.0,
    include_external: bool = True,
) -> dict[str, Any]:
    """E2 decision baseline matrix on pinned MICRO generator families."""
    case_rows: list[dict[str, Any]] = []
    external_agree = 0
    external_ran = 0
    for name, cnf, family in micro_generator_suite():
        matrix = run_baseline_matrix(
            cnf,
            task="decision",
            include_external=include_external,
            external_timeout_s=external_timeout_s,
        )
        veritas = next(
            r for r in matrix["runs"] if r["baseline_id"] == "veritas_reference"
        )
        externals = [
            r
            for r in matrix["runs"]
            if r["baseline_id"] not in ("veritas_reference",)
        ]
        for row in externals:
            if row.get("status") in ("SAT", "UNSAT"):
                external_ran += 1
                if row["status"] == veritas.get("status"):
                    external_agree += 1
        case_rows.append(
            {
                "case": name,
                "family": family,
                "formula_sha256": matrix["formula_sha256"],
                "veritas_reference_status": veritas.get("status"),
                "agreements": matrix.get("agreements") or [],
                "runs": matrix["runs"],
            }
        )
    return {
        "schema": "VERITAS_SAT_E2_GENERATOR_BASELINE_SUMMARY_V1",
        "case_count": len(case_rows),
        "cases": case_rows,
        "external_decision_agree_count": external_agree,
        "external_decision_ran_count": external_ran,
        "theorem_backed": False,
        "universal_speedup_claimed": False,
        "qualification": "generator_micro_tier_decision_crosscheck_not_count",
    }


def _suite() -> tuple[tuple[str, CNF], ...]:
    return (
        ("unit_sat", CNF.from_lists(1, [[1]])),
        ("unit_unsat", CNF.from_lists(1, [[1], [-1]])),
        ("two_var_sat", CNF.from_lists(2, [[1, 2]])),
        ("two_var_unsat", CNF.from_lists(2, [[1], [-1]])),
        ("disjoint_4", CNF.from_lists(4, [[1, 2], [3, -4]])),
        ("triangle_3cnf", CNF.from_lists(3, [[1, 2, -3], [1, -2, 3], [-1, 2, 3]])),
        ("xyz_residual_coupled", CNF.from_lists(3, [[1, 3], [2, 3]])),
    )


def run_micro_benchmark_suite(
    *,
    adaptive_timeout_s: float = 12.0,
    timeout_s: float = 4.0,
    include_baseline_matrix: bool = False,
    include_e2_generator_baselines: bool = False,
    e2_external_timeout_s: float = 8.0,
    include_external_e2: bool = True,
    include_generator_cases: bool = True,
    include_branch_order_probe: bool = True,
    include_adversarial_grid: bool = False,
) -> dict[str, Any]:
    """Run universal count mode on pinned tiny 3-CNFs; aggregate ledger work."""
    t0 = time.perf_counter()
    cases: list[dict[str, Any]] = []
    all_agree = True
    entries: list[tuple[str, CNF, str | None]] = [
        (name, cnf, None) for name, cnf in _suite()
    ]
    if include_generator_cases:
        for gname, cnf, family in micro_generator_suite():
            entries.append((gname, cnf, family))

    coupled_highlights: list[dict[str, Any]] = []
    adversarial_highlights: list[dict[str, Any]] = []

    for name, cnf, family in entries:
        report = run_universal_sat(
            cnf,
            "count",
            timeout_s=timeout_s,
            adaptive_timeout_s=adaptive_timeout_s,
            include_baseline_matrix=include_baseline_matrix,
        )
        cross = report.get("cross_checks") or {}
        if cross.get("agreement") is False:
            all_agree = False
        led = report.get("decomposition_work") or {}
        decomp = decomposition_metrics_from_report(report, cnf=cnf)
        branch_probe = None
        if include_branch_order_probe and cnf.n <= 10:
            branch_probe = probe_branch_orders_benchmark(cnf)
        case_row = {
            "case": name,
            "family": family,
            "n": cnf.n,
            "clauses": len(cnf.clauses),
            "formula_sha256": cnf.digest(),
            "count": (report.get("result") or {}).get("count"),
            "phase_c_q": (report.get("reduction") or {})
            .get("phase_c_split", {})
            .get("q"),
            "parent_bridge_status": (report.get("reduction") or {})
            .get("parent_call_bridge", {})
            .get("status"),
            "cross_check_agreement": cross.get("agreement"),
            "w_total_reported": led.get("w_total_reported"),
            "ledger_steps": len((led.get("steps") or [])),
            "ledger_totals": report.get("ledger_totals"),
            "source_finite_status": (report.get("reduction") or {})
            .get("source_finite_count", {})
            .get("status"),
            "decomposition_metrics": decomp,
            "residual_compression": residual_compression_row(report, cnf=cnf),
            "branch_order_probe": branch_probe,
        }
        cases.append(case_row)
        rc_ratio = decomp.get("compression_ratio_branches_over_classes")
        if family == "coupled" and rc_ratio is not None:
            coupled_highlights.append(
                {
                    "case": name,
                    "compression_ratio_branches_over_classes": rc_ratio,
                    "compression_vs_2n": decomp.get("compression_vs_2n"),
                    "distinct_residual_classes": decomp.get("distinct_residual_classes"),
                }
            )
        if family == "adversarial" and rc_ratio is not None:
            adversarial_highlights.append(
                {
                    "case": name,
                    "compression_ratio_branches_over_classes": rc_ratio,
                    "compression_vs_2n": decomp.get("compression_vs_2n"),
                    "distinct_residual_classes": decomp.get("distinct_residual_classes"),
                }
            )

    suite_w_total = sum(c.get("w_total_reported") or 0 for c in cases)
    beats_direct = sum(
        1
        for c in cases
        if (c.get("decomposition_metrics") or {}).get("w_beats_direct_proxy")
    )
    used_count_dag = sum(
        1
        for c in cases
        if (c.get("decomposition_metrics") or {}).get("any_count_dag_child")
    )
    highlights: list[dict[str, Any]] = []
    max_speedup: float | None = None
    max_residual_compression: float | None = None
    max_best_probe_ratio: float | None = None
    residual_ratio_cases = 0
    for c in cases:
        m = c.get("decomposition_metrics") or {}
        ratio = m.get("speedup_ratio_split_proxy")
        beats = m.get("w_beats_direct_proxy")
        if beats or (ratio is not None and float(ratio) > 1.0):
            entry = {
                "case": c["case"],
                "w_beats_direct_proxy": bool(beats),
                "speedup_ratio_split_proxy": ratio,
                "phase_c_q": m.get("phase_c_q") or c.get("phase_c_q"),
            }
            highlights.append(entry)
            if ratio is not None:
                rf = float(ratio)
                max_speedup = rf if max_speedup is None else max(max_speedup, rf)
        rc_ratio = m.get("compression_ratio_branches_over_classes")
        if rc_ratio is not None and float(rc_ratio) > 1.0:
            residual_ratio_cases += 1
            mrf = float(rc_ratio)
            max_residual_compression = (
                mrf if max_residual_compression is None else max(max_residual_compression, mrf)
            )
        probe = c.get("branch_order_probe") or {}
        br = probe.get("best_compression_ratio_branches_over_classes")
        if br is not None:
            bf = float(br)
            max_best_probe_ratio = (
                bf if max_best_probe_ratio is None else max(max_best_probe_ratio, bf)
            )

    adversarial_grid = None
    if include_adversarial_grid:
        adversarial_grid = adversarial_grid_compression_summary()

    e2_summary = None
    if include_e2_generator_baselines and include_generator_cases:
        e2_summary = e2_generator_baseline_summary(
            external_timeout_s=e2_external_timeout_s,
            include_external=include_external_e2,
        )

    return {
        "schema": "VERITAS_SAT_MICRO_BENCHMARK_V3",
        "mode": "count",
        "case_count": len(cases),
        "cases": cases,
        "e2_generator_baseline_summary": e2_summary,
        "adversarial_grid_compression": adversarial_grid,
        "all_cross_checks_agree": all_agree,
        "suite_w_total_reported": suite_w_total,
        "elapsed_seconds": time.perf_counter() - t0,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "theorem_backed": False,
        "universal_speedup_claimed": False,
        "qualification": "pinned_tiny_3cnf_plus_seeded_generators_micro_tier",
        "phase_c_split_beats_direct_proxy_count": beats_direct,
        "count_dag_child_case_count": used_count_dag,
        "decomposition_highlight_cases": highlights,
        "max_speedup_ratio_split_proxy": max_speedup,
        "residual_compression_ratio_gt_one_count": residual_ratio_cases,
        "max_residual_compression_ratio": max_residual_compression,
        "max_branch_order_probe_compression_ratio": max_best_probe_ratio,
        "coupled_family_highlights": coupled_highlights,
        "adversarial_family_highlights": adversarial_highlights,
    }