"""Count-mode micro-benchmark suite with decomposition ledger totals."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from veritas.core.cnf import CNF
from veritas.research.sat_universal import run_universal_sat


def _suite() -> tuple[tuple[str, CNF], ...]:
    return (
        ("unit_sat", CNF.from_lists(1, [[1]])),
        ("unit_unsat", CNF.from_lists(1, [[1], [-1]])),
        ("two_var_sat", CNF.from_lists(2, [[1, 2]])),
        ("two_var_unsat", CNF.from_lists(2, [[1], [-1]])),
        ("disjoint_4", CNF.from_lists(4, [[1, 2], [3, -4]])),
        ("triangle_3cnf", CNF.from_lists(3, [[1, 2, -3], [1, -2, 3], [-1, 2, 3]])),
    )


def run_micro_benchmark_suite(
    *,
    adaptive_timeout_s: float = 12.0,
    timeout_s: float = 4.0,
    include_baseline_matrix: bool = False,
) -> dict[str, Any]:
    """Run universal count mode on pinned tiny 3-CNFs; aggregate ledger work."""
    t0 = time.perf_counter()
    cases: list[dict[str, Any]] = []
    all_agree = True
    for name, cnf in _suite():
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
        cases.append(
            {
                "case": name,
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
            }
        )
    return {
        "schema": "VERITAS_SAT_MICRO_BENCHMARK_V1",
        "mode": "count",
        "case_count": len(cases),
        "cases": cases,
        "all_cross_checks_agree": all_agree,
        "elapsed_seconds": time.perf_counter() - t0,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "theorem_backed": False,
        "qualification": "pinned_tiny_3cnf_suite_only",
    }
