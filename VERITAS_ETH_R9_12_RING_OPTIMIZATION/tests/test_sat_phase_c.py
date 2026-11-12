"""Phase C outer-reduction scaffold."""
from veritas.core.cnf import CNF
from veritas.research.sat_phase_c_reduction import (
    PhaseCBounds,
    phase_c_refusal_if_out_of_bounds,
    plan_primal_component_split,
)
from veritas.research.sat_work_accounting import exponential_width_proxy
from veritas.research.sat_universal import run_universal_sat
from veritas.research.source_cnf import source_cnf_network


def test_primal_split_q_two_on_disconnected_formula():
    cnf = CNF.from_lists(4, [[1, 2], [3, -4]])
    encoded = source_cnf_network(cnf, max_clause_width=3, max_wires=10_000, max_factors=10_000)
    w_old = exponential_width_proxy(4)
    summary, ledger = plan_primal_component_split(
        cnf, encoded, bounds=PhaseCBounds(), w_old=w_old
    )
    assert summary["q"] == 2
    assert ledger.q == 2
    assert len(ledger.child_works) == 2


def test_bounds_refuse_oversized():
    cnf = CNF.from_lists(100, [[1, -2, 3]] * 10)
    refusal = phase_c_refusal_if_out_of_bounds(cnf, PhaseCBounds(max_vars=64))
    assert refusal["status"] == "REFUSED_PHASE_C_BOUNDS"


def test_universal_run_includes_phase_c_split():
    cnf = CNF.from_lists(3, [[1, 2, -3]])
    report = run_universal_sat(cnf, "decision", timeout_s=2.0)
    split = report["reduction"]["phase_c_split"]
    assert split["status"] == "SCAFFOLD_COMPONENT_SPLIT"
    assert split["q"] >= 1
    names = [s["name"] for s in report["decomposition_work"]["steps"]]
    assert "phase_c_primal_component_split" in names
