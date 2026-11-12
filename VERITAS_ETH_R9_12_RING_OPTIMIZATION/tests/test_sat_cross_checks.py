"""Phase C vs direct cross-check helper."""
from veritas.research.sat_cross_checks import cross_check_phase_c_vs_direct


def test_cross_check_skipped_when_phase_c_inactive():
    detail, ledger = cross_check_phase_c_vs_direct(
        mode="count",
        phase_c_split={"status": "SKIPPED"},
        direct_result={"count": "4"},
        w_old=16,
    )
    assert detail["status"] == "SKIPPED"
    assert ledger is None


def test_cross_check_count_agreement():
    detail, ledger = cross_check_phase_c_vs_direct(
        mode="count",
        phase_c_split={
            "status": "SCAFFOLD_COMPONENT_SPLIT",
            "recombined": {"count": 6},
        },
        direct_result={"count": "6"},
        w_old=16,
    )
    assert detail["agreement"] is True
    assert ledger is not None
    assert ledger.name == "phase_c_vs_direct_cross_check"
