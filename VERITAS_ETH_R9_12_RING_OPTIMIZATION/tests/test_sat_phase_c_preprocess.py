"""Phase C preprocessing and count_dag child integration."""
from veritas.core.cnf import CNF
from veritas.research.sat_phase_c_preprocess import apply_phase_c_preprocess
from veritas.research.sat_phase_c_reduction import PhaseCBounds, plan_primal_component_split
from veritas.research.sat_phase_c_r94_lane import primal_component_partition_certificate
from veritas.research.sat_universal import run_universal_sat
from veritas.research.source_cnf import source_cnf_network
from veritas.solvers.reference import exhaustive_count


def test_unit_propagation_preserves_count():
    cnf = CNF.from_lists(3, [[1], [1, 2], [-2, 3]])
    reduced, detail, _ledger = apply_phase_c_preprocess(cnf, w_old=8)
    assert detail["status"] in ("REDUCED", "UNCHANGED")
    assert exhaustive_count(cnf) == exhaustive_count(reduced)


def test_preprocess_detects_unsat_unit_conflict():
    cnf = CNF.from_lists(2, [[1], [-1]])
    reduced, detail, _ = apply_phase_c_preprocess(cnf, w_old=4)
    assert detail["status"] == "UNSAT"
    assert len(reduced.clauses) == 0


def test_count_dag_used_for_small_component():
    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    encoded = source_cnf_network(cnf, max_clause_width=3, max_wires=10_000, max_factors=10_000)
    cert = primal_component_partition_certificate(cnf)
    summary, _ = plan_primal_component_split(
        cnf,
        encoded,
        bounds=PhaseCBounds(prefer_count_dag=True, max_count_dag_vars=24),
        w_old=16,
        task="count",
        partition_certificate=cert,
    )
    engines = {c["child_solve"]["engine"] for c in summary["components"]}
    assert "count_dag_certificate" in engines
    assert summary["recombined"]["count"] == exhaustive_count(cnf)


def test_universal_includes_preprocess_ledger_step():
    cnf = CNF.from_lists(3, [[1], [1, 2], [-2, 3]])
    report = run_universal_sat(cnf, "count", adaptive_timeout_s=8.0)
    names = [s["name"] for s in report["decomposition_work"]["steps"]]
    assert "phase_c_preprocess" in names
    assert report["reduction"]["phase_c_split"]["preprocess"]["status"] in (
        "REDUCED",
        "UNCHANGED",
    )
    metrics = report["reduction"]["phase_c_split"].get("decomposition_metrics") or {}
    assert metrics.get("schema") == "VERITAS_PHASE_C_DECOMP_METRICS_V1"
