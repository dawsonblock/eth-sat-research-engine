"""Optional source-shaped finite count lane (tiny class, count mode only)."""
from __future__ import annotations

from typing import Any

from veritas.core.cnf import CNF
from veritas.research.sat_work_accounting import DecompositionWorkLedger
from veritas.research.sat_source_finite_admission import try_source_finite_tiered


def try_source_finite_count_lane(
    cnf: CNF,
    *,
    w_old: int,
    **_kwargs: Any,
) -> tuple[dict[str, Any], DecompositionWorkLedger | None]:
    """Tiered finite count lane; does not replace direct exact fallback."""
    tiered = try_source_finite_tiered(cnf)
    status = tiered.get("status", "UNKNOWN")
    last_attempt = (tiered.get("tier_attempts") or [{}])[-1]
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
            "count": tiered.get("count"),
            "admission_tier": tiered.get("admission_tier"),
            "qualification": "tapered_v4_tiered_finite_scaffold_not_r94",
        },
    )
    detail = {
        **tiered,
        "network_edges": last_attempt.get("network_edges"),
        "original_edges": last_attempt.get("original_edges"),
        "reason": tiered.get("reason") or last_attempt.get("reason"),
    }
    if status != "EXACT_COUNT_FINITE":
        return detail, None
    return detail, ledger
