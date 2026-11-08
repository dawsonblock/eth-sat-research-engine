"""Configurable finite groups preserve exact recursion and fail closed."""

from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r98 import shrinking_engine, general_engine
from veritas.research.parent_child_r98.shrinking_cli import load_input

ROOT = Path(__file__).resolve().parents[1]


def cycle():
    return load_input(ROOT / "examples/r98_shrinking_cycle484.json")


def matching():
    return load_input(ROOT / "examples/r98_general_matching22.json")


def test_512_cycle_executes_every_actual_child_at_exact_call_and_precision_limits():
    policy = replace(shrinking_engine.DEFAULT_SHRINKING_POLICY,
                     max_calls=1025, max_depth=1, max_precision=31488)
    report = shrinking_engine.contract_shrinking(cycle(), groups=512, policy=policy)
    assert report["status"] == "PASS_FINITE_SCALED_SHRINKING_RECURSION", report
    assert report["result"] == ((1 << 484, 0),)
    assert report["edge_layers"] == {"0": [484], "1": [0, 4]}
    assert report["ledger"]["actual_calls"] == 1025
    assert report["ledger"]["transitions"] == 1024
    assert report["ledger"]["point_evaluations"] == 2
    assert report["ledger"]["nonshrinking_children"] == 0
    assert report["maximal_precision_used"] == 31488
    assert report["active_calls"] == 1
    assert report["finite_group_count"] == report["child_count_per_tuple"] == 512
    assert report["source_group_count"] == 64 and not report["source_qualified"]
    for point in report["transitions"]:
        assert point["child_count"] == len(point["child_edges"]) == 512
        assert sum(point["child_edges"]) == 968
        assert all(512 * n <= 6 * 484 for n in point["child_edges"])
        assert point["cross_group_pairs"] == 242
        assert point["retained_modes"] == 0 and point["complete_tuple_count"] == 1


@pytest.mark.parametrize("groups", (128, 256, 1024))
def test_unreachable_leaves_refuse_before_any_production_call(groups):
    report = shrinking_engine.contract_shrinking(cycle(), groups=groups)
    assert report["status"].startswith("INCONCLUSIVE_"), report
    assert "result" not in report
    assert report["ledger"]["actual_calls"] == 0
    assert report["group_preflight"]


@pytest.mark.parametrize("name,value", (("max_calls", 1024), ("max_precision", 31487),
                                         ("max_certificate_bytes", 128), ("max_work", 1)))
def test_group_budgets_refuse_without_partial_answer(name, value):
    policy = replace(shrinking_engine.DEFAULT_SHRINKING_POLICY, **{name: value})
    report = shrinking_engine.contract_shrinking(cycle(), groups=512, policy=policy)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "result" not in report
    assert report["ledger"]["actual_calls"] == 0


def test_generic_cycle_still_refuses_complete_weighted_stream():
    report = general_engine.contract_general_shrinking(cycle(), groups=512)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "tuple" in report["reason"].lower()
    assert "result" not in report and report["ledger"]["actual_calls"] == 0
    assert report["group_preflight"]


def test_general_nonconstant_matching_uses_65_children():
    report = general_engine.contract_general_shrinking(matching(), groups=65)
    assert report["status"] == "PASS_FINITE_SCALED_GENERAL_SHRINKING_RECURSION", report
    assert report["result"] == ((31**22, 0, 0, 0, 0, 0, 0),)
    assert report["ledger"]["actual_calls"] == 8711
    assert report["ledger"]["transitions"] == 8710
    assert report["ledger"]["point_evaluations"] == 134
    assert report["child_count_per_tuple"] == 65
    assert report["source_group_count"] == 64
    assert all(len(point["child_edges"]) == 65 for point in report["transitions"])
    assert not report["source_qualified"]


@pytest.mark.parametrize("groups", (True, 63, 1025, 64.0, "512"))
def test_group_count_requires_explicit_bounded_integer(groups):
    report = shrinking_engine.contract_shrinking(matching(), groups=groups)
    assert "result" not in report and report["ledger"]["actual_calls"] == 0


def test_missing_configured_child_is_rejected_before_recursing(monkeypatch):
    production = shrinking_engine.construct_children
    monkeypatch.setattr(shrinking_engine, "construct_children",
                        lambda *a, **kw: production(*a, **kw)[:-1])
    # The row-constant fixture has a valid one-level 65-group layout.
    parent = load_input(ROOT / "examples/r98_shrinking_484.json")
    report = shrinking_engine.contract_shrinking(parent, groups=512)
    assert "result" not in report and "512 ordered" in report["reason"]
    assert report["ledger"]["actual_calls"] == 1


def test_source_call_cannot_select_finite_groups():
    from veritas.research.parent_child_r98.engine import contract_source
    with pytest.raises(TypeError):
        contract_source(None, groups=512)
