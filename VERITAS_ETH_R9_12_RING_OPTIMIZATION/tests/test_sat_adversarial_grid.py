"""Adversarial grid compression probe (research, not CI-pinned)."""
from veritas.research.sat_micro_benchmark import adversarial_grid_compression_summary


def test_adversarial_grid_schema_and_agreement():
    summary = adversarial_grid_compression_summary(n_min=6, n_max=7, seeds=(0, 1))
    assert summary["schema"] == "VERITAS_SAT_ADVERSARIAL_GRID_COMPRESSION_V1"
    assert summary["agreement_count"] == summary["case_count"]
    p = summary["compression_vs_2n_percentiles"]
    assert p["p50"] is not None
    assert summary["universal_speedup_claimed"] is False