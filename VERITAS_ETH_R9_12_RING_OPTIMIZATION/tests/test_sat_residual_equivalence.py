"""Residual equivalence counting scaffold."""
from veritas.core.cnf import CNF
from veritas.research.sat_phase_c_reduction import PhaseCBounds, plan_primal_component_split
from veritas.research.sat_phase_c_r94_lane import primal_component_partition_certificate
from veritas.research.sat_residual_equivalence import (
    count_by_residual_equivalence,
    xor_system_solution_count,
)
from veritas.research.sat_universal import run_universal_sat
from veritas.research.source_cnf import source_cnf_network


def test_xyz_clause_merge_counts_five():
    # (x ∨ z) ∧ (y ∨ z) with x=1, y=2, z=3
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    report = count_by_residual_equivalence(cnf, branch_order=(1, 2))
    assert report["status"] == "EXACT_COUNT"
    assert report["count"] == 5
    assert report["agreement"] is True
    assert report["distinct_residual_classes"] < report["full_assignment_branches"]
    assert report["distinct_residual_classes"] == 2


def test_residual_merge_matches_exhaustive_on_disconnected():
    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    report = count_by_residual_equivalence(cnf)
    assert report["count"] == report["oracle_exhaustive_count"] == 9


def test_xor_rank_demo_matches_power_of_two():
    assert xor_system_solution_count(96, rank=86, consistent=True) == 1 << 10


def test_residual_equivalence_phase_c_child_with_dag_disabled():
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    encoded = source_cnf_network(cnf, max_clause_width=3, max_wires=10_000, max_factors=10_000)
    cert = primal_component_partition_certificate(cnf)
    bounds = PhaseCBounds(prefer_count_dag=False, prefer_residual_equivalence=True)
    summary, _ = plan_primal_component_split(
        cnf, encoded, bounds=bounds, w_old=8, task="count", partition_certificate=cert
    )
    assert summary["components"][0]["child_solve"]["engine"] == "residual_equivalence"
    assert summary["recombined"]["count"] == 5


def test_universal_count_emits_residual_compression_probe():
    cnf = CNF.from_lists(3, [[1, 2, -3], [1, -2, 3], [-1, 2, 3]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=8.0)
    probe = report["reduction"]["residual_compression"]
    assert probe["schema"] == "VERITAS_RESIDUAL_COMPRESSION_PROBE_V1"
    assert probe["status"] == "EXACT_COUNT"
    assert probe["distinct_residual_classes"] is not None
    assert probe["compression_ratio_branches_over_classes"] is not None
    kinds = report["count_invariants"]["kinds"]
    assert "RESIDUAL_EQUIVALENCE_MERGE" in kinds
    assert report["universal_speedup_claimed"] is False
    assert "residual_compression_probe" in [
        s["name"] for s in report["decomposition_work"]["steps"]
    ]
