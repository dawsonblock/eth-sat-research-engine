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
    if status == "REFUSED_UNSAT_AFTER_PREPROCESS":
        direct_count = direct_result.get("count")
        agreement = direct_count is not None and int(direct_count) == 0
        detail.update(
            {
                "status": "COUNT_COMPARE",
                "phase_c_count": 0,
                "direct_count": direct_count,
                "agreement": agreement,
                "reason": "preprocess_detected_unsat",
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
                "qualification": phase_c_split.get("qualification")
                or "scaffold_independent_components_only",
                "count_invariant": phase_c_split.get("count_invariant"),
                "partition_certificate_valid": phase_c_split.get(
                    "partition_certificate_valid"
                )
                or (phase_c_split.get("partition_certificate") or {}).get("valid"),
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


def cross_check_source_finite_vs_direct(
    *,
    source_finite: dict[str, Any],
    direct_result: dict[str, Any],
    w_old: int,
) -> tuple[dict[str, Any], Optional[DecompositionWorkLedger]]:
    """Compare optional source finite count lane to direct exact fallback."""
    src_status = source_finite.get("status")
    direct_count = direct_result.get("count")
    agreement = False
    detail: dict[str, Any] = {
        "schema": "VERITAS_SOURCE_FINITE_CROSS_CHECK_V1",
        "source_status": src_status,
    }
    if src_status in ("SKIPPED", "REFUSED") or direct_count is None:
        detail.update(
            {
                "status": "SKIPPED",
                "reason": "lane_not_applicable",
                "agreement": None,
            }
        )
        return detail, None
    if src_status == "EXACT_COUNT_FINITE":
        src_count = source_finite.get("count")
        if src_count is not None:
            agreement = int(src_count) == int(direct_count)
        detail.update(
            {
                "status": "COUNT_COMPARE",
                "source_count": src_count,
                "direct_count": direct_count,
                "agreement": agreement,
                "qualification": "finite_tapered_lane_not_r94_theorem",
            }
        )
    else:
        detail.update(
            {
                "status": "INCONCLUSIVE",
                "source_count": source_finite.get("count"),
                "direct_count": direct_count,
                "agreement": None,
                "reason": source_finite.get("reason"),
                "next_admission_step": source_finite.get("next_admission_step"),
                "admission_tier": source_finite.get("admission_tier"),
            }
        )
    w_check = 1 if agreement else 2
    ledger = DecompositionWorkLedger(
        name="source_finite_vs_direct_cross_check",
        w_old=w_old,
        w_transform=0,
        child_works=(),
        w_reconstruct=0,
        w_check=w_check,
        metadata={"phase": "cross_check", **detail},
    )
    return detail, ledger


def combine_cross_check_agreement(*details: dict[str, Any]) -> bool | None:
    flags = [
        bool(d["agreement"])
        for d in details
        if isinstance(d.get("agreement"), bool)
    ]
    if not flags:
        return None
    return all(flags)
