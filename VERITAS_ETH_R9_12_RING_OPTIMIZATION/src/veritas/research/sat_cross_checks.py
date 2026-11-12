"""Cross-checks between Phase C reduction and direct exact lanes."""
from __future__ import annotations

from typing import Any, Literal, Optional

from veritas.research.sat_work_accounting import DecompositionWorkLedger


def cross_check_phase_c_vs_direct(
    *,
    mode: Literal["decision", "count"],
    phase_c_split: dict[str, Any],
    direct_result: dict[str, Any],
    w_old: int,
) -> tuple[dict[str, Any], Optional[DecompositionWorkLedger]]:
    """Record agreement between recombined Phase C output and direct fallback."""
    recombined = phase_c_split.get("recombined") or {}
    status = phase_c_split.get("status")
    agreement = False
    detail: dict[str, Any] = {
        "schema": "VERITAS_PHASE_C_CROSS_CHECK_V1",
        "phase_c_status": status,
        "mode": mode,
    }
    if status != "SCAFFOLD_COMPONENT_SPLIT":
        detail.update(
            {
                "status": "SKIPPED",
                "reason": "phase_c_not_applicable",
                "agreement": False,
            }
        )
        return detail, None

    if mode == "count":
        phase_count = recombined.get("count")
        direct_count = direct_result.get("count")
        if phase_count is not None and direct_count is not None:
            agreement = int(phase_count) == int(direct_count)
        detail.update(
            {
                "status": "COUNT_COMPARE",
                "phase_c_count": phase_count,
                "direct_count": direct_count,
                "agreement": agreement,
                "qualification": "scaffold_independent_components_only",
            }
        )
    else:
        phase_status = recombined.get("status")
        direct_status = direct_result.get("status")
        if phase_status in ("SAT", "UNSAT") and direct_status in ("SAT", "UNSAT"):
            agreement = phase_status == direct_status
        detail.update(
            {
                "status": "DECISION_COMPARE",
                "phase_c_status_recombined": phase_status,
                "direct_status": direct_status,
                "agreement": agreement,
            }
        )

    w_check = 1 if agreement else 2
    ledger = DecompositionWorkLedger(
        name="phase_c_vs_direct_cross_check",
        w_old=w_old,
        w_transform=0,
        child_works=(),
        w_reconstruct=0,
        w_check=w_check,
        metadata={"phase": "cross_check", **detail},
    )
    return detail, ledger
