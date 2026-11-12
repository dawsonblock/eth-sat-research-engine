"""Phase C R9.4 partial lane: partition certificate + outer reduction pipeline."""
from veritas.core.cnf import CNF
from veritas.research.sat_phase_c_r94_lane import (
    primal_component_partition_certificate,
    run_phase_c_outer_reduction,
)
from veritas.research.sat_phase_c_reduction import PhaseCBounds
from veritas.research.sat_universal import run_universal_sat
from veritas.research.sat_work_accounting import exponential_width_proxy
from veritas.research.source_cnf import source_cnf_network
from veritas.solvers.reference import exhaustive_count


def test_partition_certificate_valid_on_disconnected_formula():
    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    cert = primal_component_partition_certificate(cnf)
    assert cert["valid"] is True
    assert cert["q"] == 2


def test_partition_certificate_isolated_variable_component():
    cnf = CNF.from_lists(3, [[1, 2]])
    cert = primal_component_partition_certificate(cnf)
    assert cert["valid"] is True
    assert cert["q"] == 2  # {1,2} and {3}


def test_outer_reduction_count_invariant_and_r94_snapshot():
    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    encoded = source_cnf_network(cnf, max_clause_width=3, max_wires=10_000, max_factors=10_000)
    summary, ledger = run_phase_c_outer_reduction(
        cnf, encoded, bounds=PhaseCBounds(), w_old=exponential_width_proxy(4), task="count"
    )
    assert summary["schema"] == "VERITAS_PHASE_C_OUTER_REDUCTION_V1"
    assert summary["count_invariant"]["proved_in_repo"] is True
    assert summary["r94_obligations"]["outer_reduction"].startswith("PARTIAL")
    assert summary["recombined"]["count"] == exhaustive_count(cnf)
    assert ledger is not None
    assert ledger.metadata.get("partition_certificate_valid") is True
    for child in summary["components"]:
        assert child["count_preserving_reduction_proved"] is True


def test_universal_count_mode_exposes_phase_c_r94_fields():
    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=10.0, timeout_s=4.0)
    split = report["reduction"]["phase_c_split"]
    assert split["schema"] == "VERITAS_PHASE_C_OUTER_REDUCTION_V1"
    assert split["count_invariant"]["type"] == "PRODUCT_OVER_PRIMAL_COMPONENTS"
    assert report["cross_checks"]["phase_c_vs_direct"]["partition_certificate_valid"] is True
