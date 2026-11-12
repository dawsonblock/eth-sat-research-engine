"""Optional source-shaped finite count lane (tiny class, count mode only)."""
from __future__ import annotations

from typing import Any

from veritas.core.cnf import CNF
from veritas.research.sat_cnf_parent_bridge import (
    DEFAULT_TINY_CNF_CLASS,
    TinyFixedCnfClass,
    admit_tiny_fixed_cnf_class,
)
from veritas.research.sat_work_accounting import DecompositionWorkLedger
from veritas.research.tapered_v4.cnf_count import count_source_cnf_finite
from veritas.research.tapered_v4.model import RecursionPolicy


def try_source_finite_count_lane(
    cnf: CNF,
    *,
    cnf_class: TinyFixedCnfClass = DEFAULT_TINY_CNF_CLASS,
    max_wires: int = 64,
    max_active_wires: int = 8,
    w_old: int,
) -> tuple[dict[str, Any], DecompositionWorkLedger | None]:
    """Run ``count_source_cnf_finite`` when bridge class admits; does not replace direct lane."""
    refusal = admit_tiny_fixed_cnf_class(cnf, cnf_class)
    if refusal:
        detail = {
            "schema": "VERITAS_SOURCE_FINITE_COUNT_LANE_V1",
            "status": "REFUSED",
            "reason": refusal["reason"],
        }
        return detail, None
    # Conservative policy aligned with existing finite tests
    policy = RecursionPolicy(
        max_active_wires=max_active_wires,
        max_precision_bits=min(1024, max(8, cnf.n + 1)),
        max_work=500_000,
        max_seconds=15.0,
    )
    encode_cap = min(max_wires, 64)
    result = count_source_cnf_finite(
        cnf,
        policy,
        max_wires=encode_cap,
        max_factors=10_000,
        max_clause_width=3,
        verify_exhaustive=False,
    )
    status = result.get("status", "UNKNOWN")
    w_work = int(result.get("ledger", {}).get("counters", {}).get("work", 0) or 0)
    if w_work <= 0:
        w_work = max(1, cnf.n * len(cnf.clauses))
    ledger = DecompositionWorkLedger(
        name="source_finite_count_lane",
        w_old=w_old,
        w_transform=w_work,
        child_works=(),
        w_reconstruct=0,
        w_check=1,
        metadata={
            "phase": "source_finite",
            "status": status,
            "count": result.get("count"),
            "qualification": "tapered_v4_finite_scaffold_not_r94",
        },
    )
    detail = {
        "schema": "VERITAS_SOURCE_FINITE_COUNT_LANE_V1",
        "status": status,
        "count": result.get("count"),
        "reason": result.get("reason"),
        "network_edges": result.get("network_edges"),
        "original_edges": result.get("original_edges"),
        "theorem_backed": False,
        "universal_speedup_claimed": False,
    }
    return detail, ledger
