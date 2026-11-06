"""Actual shrinking recursion, strict transition guards and exact recovery."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from veritas.research.parent_child_r98.model import (
    Budget,
    ModeSet,
    ParentCall,
    Policy,
    SourceVertex,
    canonical,
)
from veritas.research.parent_child_r98 import shrinking_engine as engine
from veritas.research.parent_child_r98.shrinking_layout import (
    construct_vertex_shrinking_layout as construct_shrinking_layout,
)
from veritas.research.parent_child_r98.shrinking_oracle import (
    certify_constant_deformation,
)
from veritas.research.tapered_v4.source_recipes import make_reference


def matching_parent(edges=44, precision=64, creation_precision=None):
    ref = make_reference(
        kind="dense",
        arity=1,
        creation_precision=creation_precision or precision,
        defining_polynomial=7,
        jet_length=1,
        data=[[[1, 0]], [[1, 0]]],
    )
    return ParentCall(
        1024,
        0,
        precision,
        7,
        edges,
        tuple(
            SourceVertex(side, i, (i,), ref)
            for side in ("row", "column")
            for i in range(edges)
        ),
    )


def test_one_level_recomputes_every_actual_shrinking_child():
    report = engine.contract_shrinking(matching_parent())
    assert report["status"] == "PASS_FINITE_SCALED_SHRINKING_RECURSION"
    assert report["result"] == ((1 << 44, 0),)
    assert report["edge_layers"] == {"0": [44], "1": [0, 4]}
    assert report["ledger"]["actual_calls"] == 129
    assert report["ledger"]["transitions"] == 128
    assert report["ledger"]["nonshrinking_children"] == 0
    for transition in report["transitions"]:
        assert len(transition["child_edges"]) == 64
        assert all(
            64 * n <= 6 * transition["parent_edges"] for n in transition["child_edges"]
        )
    assert not report["source_qualified"]


def cycle_parent(edges=484, precision=512, *, row_constant=1, column_table=None):
    count = edges // 2
    row_ref = make_reference(
        kind="dense",
        arity=2,
        creation_precision=precision,
        defining_polynomial=7,
        jet_length=1,
        data=[[[row_constant, 0]]] * 4,
    )
    column_ref = make_reference(
        kind="dense",
        arity=2,
        creation_precision=precision,
        defining_polynomial=7,
        jet_length=1,
        data=[[[value, 0]] for value in (column_table or (1, 1, 1, 1))],
    )
    vertices = tuple(
        SourceVertex("row", i, (2 * i, 2 * i + 1), row_ref) for i in range(count)
    ) + tuple(
        SourceVertex("column", i, (2 * i + 1, 2 * ((i + 1) % count)), column_ref)
        for i in range(count)
    )
    return ParentCall(1024, 0, precision, 7, edges, vertices)


@pytest.mark.parametrize("family", ("matching", "weighted_connected_cycle"))
def test_two_levels_shrink_484_to_44_to_4_with_exact_recovery(family):
    p = (
        matching_parent(484, 512)
        if family == "matching"
        else cycle_parent(484, 512, row_constant=3, column_table=(5, 5, 5, 5))
    )
    expected = (
        (1 << 484) if family == "matching" else ((1 << 484) * 15**242) % (1 << 512)
    )
    report = engine.contract_shrinking(p)
    assert report["status"] == "PASS_FINITE_SCALED_SHRINKING_RECURSION"
    assert report["result"] == ((expected, 0),)
    assert report["edge_layers"] == {"0": [484], "1": [0, 44], "2": [0, 4]}
    assert report["active_calls"] == 45
    assert report["ledger"]["actual_calls"] == 5761
    assert report["ledger"]["transitions"] == 5760
    assert report["ledger"]["point_evaluations"] == 90
    assert report["ledger"]["nonshrinking_children"] == 0
    assert report["maximal_precision_used"] == 34304
    assert len(report["hermite_recoveries"]) == 45
    assert report["termination"] == "STRICT_EDGE_DECREASE_TO_LEAF_THRESHOLD"


def test_connected_cycle_with_nonconstant_column_entries():
    p = cycle_parent(64, 256, column_table=(2, 3, 5, 7))
    report = engine.contract_shrinking(p)
    assert report["status"] == "PASS_FINITE_SCALED_SHRINKING_RECURSION"
    assert report["result"] == ((17**32, 0),)
    assert report["edge_layers"] == {"0": [64], "1": [0, 4]}
    assert report["ledger"]["nonshrinking_children"] == 0


def test_nonconstant_row_is_refused_before_any_transition():
    p = matching_parent()
    v = p.vertices[0]
    ref = make_reference(
        kind="dense",
        arity=1,
        creation_precision=64,
        defining_polynomial=7,
        jet_length=1,
        data=[[[1, 0]], [[2, 0]]],
    )
    p = replace(p, vertices=(replace(v, tensor=ref), *p.vertices[1:]))
    report = engine.contract_shrinking(p)
    assert "result" not in report
    assert "row tensor is not constant" in report["reason"]
    assert report["ledger"]["actual_calls"] == 1


@pytest.mark.parametrize("attack", ("nonshrinking", "degree"))
def test_actual_child_guards_run_before_any_child_recursive_call(monkeypatch, attack):
    original = engine.construct_children

    def forged(*args, **kwargs):
        children = list(original(*args, **kwargs))
        children[0] = SimpleNamespace(
            group=0,
            edge_count=args[0].edge_count if attack == "nonshrinking" else 4,
            vertices=()
            if attack == "nonshrinking"
            else (SimpleNamespace(ports=tuple(range(5))),),
        )
        return tuple(children)

    monkeypatch.setattr(engine, "construct_children", forged)
    report = engine.contract_shrinking(matching_parent())
    assert "result" not in report
    assert report["ledger"]["actual_calls"] == 1
    assert report["ledger"]["transitions"] == 0
    if attack == "nonshrinking":
        assert report["status"] == "INCONCLUSIVE_CHILD_SHRINK"
    else:
        assert "degree invariant" in report["reason"]


def test_corrupted_recursive_value_is_never_replaced_by_oracle(monkeypatch):
    monkeypatch.setattr(engine, "leaf", lambda *args, **kwargs: ((0, 0),))
    report = engine.contract_shrinking(matching_parent())
    assert "result" not in report
    assert "recursive child differs" in report["reason"]
    assert report["ledger"]["actual_calls"] == 2


def test_incomplete_independent_child_inventory_cannot_skip_calls(monkeypatch):
    original = engine.verify_children

    def incomplete(*args, **kwargs):
        report = original(*args, **kwargs)
        report["values"] = report["values"][:-1]
        return report

    monkeypatch.setattr(engine, "verify_children", incomplete)
    report = engine.contract_shrinking(matching_parent())
    assert "result" not in report
    assert report["ledger"]["actual_calls"] == 1


def test_depth_budget_refuses_instead_of_becoming_a_leaf():
    policy = replace(engine.DEFAULT_SHRINKING_POLICY, max_depth=1)
    report = engine.contract_shrinking(matching_parent(484, 512), policy=policy)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert "result" not in report
    assert "descendant depth" in report["reason"]
    assert report["group_preflight"]["failing_depth"] > policy.max_depth
    assert report["ledger"]["actual_calls"] == 0


@pytest.mark.parametrize(
    "change",
    ({"max_precision": 1024}, {"max_certificate_bytes": 1000}, {"max_calls": 1}),
)
def test_arithmetic_evidence_and_call_caps_never_return_partial_counts(change):
    policy = replace(engine.DEFAULT_SHRINKING_POLICY, **change)
    report = engine.contract_shrinking(matching_parent(), policy=policy)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert "result" not in report


def test_zero_node_mode_checker_rejects_forged_coefficient():
    p, budget = matching_parent(), Budget(engine.DEFAULT_SHRINKING_POLICY)
    layout = construct_shrinking_layout(p, budget=budget)
    modes = engine.build_zero_node_modes(p, layout, -1, budget=budget)
    data = modes.certificate
    data["local"] = [[0, 0, [[1, 0]]]]
    with pytest.raises(ValueError, match="altered or incomplete"):
        engine.verify_zero_node_modes(
            p, layout, ModeSet(layout.content_digest, canonical(data)), budget=budget
        )


@pytest.mark.parametrize(
    "attack", ("missing_node", "boolean_node", "point_value", "degree_certificate")
)
def test_constant_recovery_requires_exact_premises_and_both_recursive_values(attack):
    p, budget = matching_parent(), Budget(engine.DEFAULT_SHRINKING_POLICY)
    certificate = certify_constant_deformation(p, budget=budget)
    value = ((1 << 44, 0),)
    points = {-1: value, 1: value}
    if attack == "missing_node":
        del points[1]
    elif attack == "boolean_node":
        points = {-1: value, True: value}
    elif attack == "point_value":
        points[1] = ((0, 0),)
    else:
        certificate["degree_bound"] = 1
    with pytest.raises(ValueError):
        engine.recover_constant_points(p, certificate, points, budget=budget)


def test_original_creation_residue_is_inherited_before_lifting():
    p = matching_parent(44, 64, creation_precision=8)
    ref = make_reference(
        kind="dense",
        arity=1,
        creation_precision=8,
        defining_polynomial=7,
        jet_length=1,
        data=[[[255, 0]], [[255, 0]]],
    )
    p = replace(p, vertices=(replace(p.vertices[0], tensor=ref), *p.vertices[1:]))
    report = engine.contract_shrinking(p)
    expected = (255 * (1 << 44)) % (1 << 64)
    assert report["result"] == ((expected, 0),)
    assert expected != (-(1 << 44)) % (1 << 64)


def test_small_leaf_does_not_claim_a_shrinking_transition():
    report = engine.contract_shrinking(matching_parent(2))
    assert report["status"] == "PASS_FINITE_SCALED_LEAF"
    assert report["result"] == ((4, 0),)
    assert report["active_calls"] == 0
    assert report["actual_child_shrink"] == "NOT_RUN_LEAF"
    assert report["ledger"]["actual_calls"] == 1


def test_connected_zero_node_basis_preserves_all_cross_group_interactions():
    p, budget = cycle_parent(64, 256), Budget(engine.DEFAULT_SHRINKING_POLICY)
    layout = construct_shrinking_layout(p, budget=budget)
    modes = engine.build_zero_node_modes(p, layout, 1, budget=budget)
    data = modes.certificate
    assert data["cross_pairs"]
    assert data["modes"] == []
    assert {packet["occupied_slots"][0][0] for packet in layout.source["packets"]} == {
        0,
        1,
    }
    data["cross_pairs"].pop()
    with pytest.raises(ValueError, match="altered or incomplete"):
        engine.verify_zero_node_modes(
            p, layout, ModeSet(layout.content_digest, canonical(data)), budget=budget
        )
