"""Full nonconstant recovery and fail-closed actual shrinking transitions."""

from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r98 import general_engine as engine
from veritas.research.parent_child_r98.shrinking_cli import load_input


ROOT = Path(__file__).resolve().parents[1]


def general_parent():
    return load_input(ROOT / "examples/r98_general_matching22.json")


def test_nonconstant_full_grid_recomputes_all_actual_children():
    report = engine.contract_general_shrinking(general_parent())
    assert report["status"] == "PASS_FINITE_SCALED_GENERAL_SHRINKING_RECURSION", report
    assert report["result"] == ((31**22, 0, 0, 0, 0, 0, 0),)
    assert report["edge_layers"] == {"0": [22], "1": [0, 2]}
    assert report["ledger"]["actual_calls"] == 8577
    assert report["ledger"]["transitions"] == 8576
    assert report["ledger"]["point_evaluations"] == 134
    assert report["ledger"]["nonshrinking_children"] == 0
    assert report["maximal_precision_used"] == 1536
    assert not report["source_qualified"] and not report["theorem_mode_enabled"]
    assert len({point["term_sha256"] for point in report["transitions"]}) > 1
    for point in report["transitions"]:
        assert len(point["child_edges"]) == point["child_count"] == 64
        assert sum(point["child_edges"]) == 44
        assert all(64 * n <= 6 * 22 for n in point["child_edges"])


@pytest.mark.parametrize("name,value", (("max_calls", 100), ("max_precision", 1024),
                                         ("max_work", 1), ("max_certificate_bytes", 1)))
def test_resource_exhaustion_never_returns_partial_result(name, value):
    policy = replace(engine.DEFAULT_SHRINKING_POLICY, **{name: value})
    report = engine.contract_general_shrinking(general_parent(), policy=policy)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "result" not in report


def test_incomplete_interpolation_grid_is_not_a_smaller_experiment():
    report = engine.contract_general_shrinking(general_parent(), max_points=64)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert report["ledger"]["transitions"] == 0
    assert "result" not in report


def test_missing_child_rejected_before_any_recursive_child(monkeypatch):
    production = engine.construct_children
    monkeypatch.setattr(engine, "construct_children", lambda *a, **kw: production(*a, **kw)[:-1])
    report = engine.contract_general_shrinking(general_parent())
    assert "result" not in report
    assert "64 ordered" in report["reason"]
    assert report["ledger"]["actual_calls"] == 1


def test_dropped_empty_beta_is_not_an_oracle_answer(monkeypatch):
    monkeypatch.setattr(engine, "weighted_tuples", lambda *a, **kw: iter(()))
    report = engine.contract_general_shrinking(general_parent())
    assert "result" not in report
    assert "incomplete weighted" in report["reason"]
    assert report["ledger"]["transitions"] == 0


def test_corrupted_leaf_result_cannot_be_replaced_by_reference(monkeypatch):
    production = engine.leaf
    def corrupt(parent, budget):
        value = production(parent, budget)
        return ((value[0][0] ^ 1, *value[0][1:]),)
    monkeypatch.setattr(engine, "leaf", corrupt)
    report = engine.contract_general_shrinking(general_parent())
    assert "result" not in report
    assert "recursive child differs" in report["reason"]


def test_existing_constant_row_driver_stays_separate():
    from veritas.research.parent_child_r98.shrinking_engine import contract_shrinking
    report = contract_shrinking(general_parent())
    assert "result" not in report
    assert report["status"] != "PASS_FINITE_SCALED_SHRINKING_RECURSION"
