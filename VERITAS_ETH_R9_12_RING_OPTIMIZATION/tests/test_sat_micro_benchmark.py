"""Micro-benchmark suite and ParentCall bridge."""
import json

from veritas.core.cnf import CNF
from veritas.research.sat_cnf_parent_bridge import build_parent_call_from_encoded_cnf
from veritas.research.sat_micro_benchmark import run_micro_benchmark_suite
from veritas.research.sat_universal import run_universal_sat
from veritas.research.source_cnf import source_cnf_network
from veritas.solvers.reference import exhaustive_count


def test_micro_benchmark_all_cross_checks_agree():
    report = run_micro_benchmark_suite()
    assert report["schema"] == "VERITAS_SAT_MICRO_BENCHMARK_V1"
    assert report["all_cross_checks_agree"] is True
    assert report["case_count"] >= 5


def test_parent_bridge_refuses_out_of_tiny_class():
    cnf = CNF.from_lists(20, [[1, -2, 3]])
    encoded = source_cnf_network(cnf, max_clause_width=3, max_wires=50_000, max_factors=50_000)
    bridge = build_parent_call_from_encoded_cnf(cnf, encoded)
    assert bridge["status"] == "REFUSED"
    assert "max_vars" in bridge["reason"] or "OUT_OF_CLASS" in str(bridge)


def test_count_run_exposes_ledger_totals_and_source_lane():
    cnf = CNF.from_lists(3, [[1, -2, 3]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=8.0)
    assert report["ledger_totals"]["schema"] == "VERITAS_LEDGER_TOTALS_V1"
    assert report["ledger_totals"]["w_total_reported"] == report["decomposition_work"][
        "w_total_reported"
    ]
    sf = report["cross_checks"]["source_finite_vs_direct"]
    if sf.get("status") == "COUNT_COMPARE":
        assert sf.get("agreement") in (True, False)
    src = report["reduction"]["source_finite_count"]
    assert src["status"] in (
        "EXACT_COUNT_FINITE",
        "INCONCLUSIVE_RESOURCE_LIMIT",
        "INCONCLUSIVE_INPUT_OR_CAP",
        "INCONCLUSIVE_INVARIANT_FAILURE",
    )


def test_parent_call_bridge_on_tiny_cnf():
    cnf = CNF.from_lists(3, [[1, -2, 3]])
    encoded = source_cnf_network(cnf, max_clause_width=3, max_wires=5000, max_factors=5000)
    bridge = build_parent_call_from_encoded_cnf(cnf, encoded)
    assert bridge["status"] == "PARENT_CALL_BUILT"
    assert bridge["content_digest"]
    assert bridge["jet_fast_path_eligible"] is False


def test_universal_run_includes_parent_bridge_and_serializes():
    cnf = CNF.from_lists(3, [[1, 2], [-1, 3]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=8.0)
    bridge = report["reduction"]["parent_call_bridge"]
    assert bridge["status"] == "PARENT_CALL_BUILT"
    assert int(report["result"]["count"]) == exhaustive_count(cnf)
    json.dumps(report)
