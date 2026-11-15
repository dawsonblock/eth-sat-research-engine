"""Tiered source-finite admission and next-step hints."""
from veritas.core.cnf import CNF
from veritas.research.sat_source_finite_admission import (
    next_admission_step,
    try_source_finite_tiered,
)
from veritas.research.sat_universal import run_universal_sat


def test_next_admission_step_maps_precision_cap():
    step = next_admission_step(
        status="INCONCLUSIVE_RESOURCE_LIMIT",
        reason="finite tapered plan unavailable: source node precision exceeds cap",
    )
    assert step["step"] == "RAISE_MAX_PRECISION_BITS"


def test_tiered_inconclusive_includes_next_step():
    cnf = CNF.from_lists(3, [[1, 2, -3], [1, -2, 3]])
    detail = try_source_finite_tiered(cnf)
    assert detail["schema"] == "VERITAS_SOURCE_FINITE_COUNT_LANE_V2"
    assert detail["status"] != "EXACT_COUNT_FINITE"
    assert detail.get("next_admission_step", {}).get("step")
    assert len(detail.get("tier_attempts") or []) >= 1


def test_universal_run_exposes_count_invariants_and_source_v2():
    cnf = CNF.from_lists(3, [[1, -2, 3]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=8.0)
    reg = report["count_invariants"]
    assert reg["schema"] == "VERITAS_COUNT_INVARIANT_REGISTRY_V1"
    assert len(reg["entries"]) >= 1
    src = report["reduction"]["source_finite_count"]
    assert src["schema"] == "VERITAS_SOURCE_FINITE_COUNT_LANE_V2"
