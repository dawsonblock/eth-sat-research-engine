"""Finite radix metadata and independent complete-child inventories."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.independent import reference_children, verify_children
from veritas.research.parent_child_r98.model import (
    Budget, ChildGraph, ChildReductionTerm, ExponentTuple, ParentCall,
    Semantics, SourceVertex, canonical, decode, layout_group_count,
)
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_engine import (
    DEFAULT_SHRINKING_POLICY, build_zero_node_modes,
)
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.tapered_v4.source_recipes import make_reference


def matching(edges):
    ref = make_reference(kind="dense", arity=1, creation_precision=5,
                         defining_polynomial=7, jet_length=1,
                         data=[[[1, 0]], [[1, 0]]])
    return ParentCall(1024, 0, 5, 7, edges, tuple(
        SourceVertex(side, edge, (edge,), ref)
        for side in ("row", "column") for edge in range(edges)))


def children_case(groups, edges):
    parent = matching(edges)
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    layout = construct_vertex_shrinking_layout(parent, groups=groups, budget=budget)
    modes = build_zero_node_modes(parent, layout, 1, budget=budget)
    beta = ExponentTuple(modes.content_digest, ())
    children = construct_children(parent, layout, modes, beta, budget=budget,
                                  _admitted=True, require_shrink=True)
    return parent, layout, modes, beta, children


@pytest.mark.parametrize("groups,edges", ((64, 22), (65, 22), (128, 44), (512, 172)))
def test_constructor_and_independent_verifier_use_bound_group_count(groups, edges):
    parent, layout, modes, beta, children = children_case(groups, edges)
    assert len(children) == groups
    assert tuple(child.group for child in children) == tuple(range(groups))
    assert all(child.group_count == groups for child in children)
    assert sum(child.edge_count for child in children) == 2 * edges
    assert all(groups * child.edge_count <= 6 * edges for child in children)
    report = verify_children(parent, layout, modes, beta, children,
                             budget=Budget(DEFAULT_SHRINKING_POLICY), _admitted=True)
    assert report["child_count"] == len(report["values"]) == groups
    assert report["all_group_shrink"] and report["all_source_shrink"]
    assert all(decode(c.schedule_bytes)["source"]["r"] == 64 for c in children)
    last = children[-1]
    assert ChildGraph.deserialize(last.serialize()) == last


@pytest.fixture(scope="module")
def case128():
    return children_case(128, 44)


def test_reference_materializer_independently_uses_all_groups(case128, monkeypatch):
    parent, layout, modes, beta, children = case128
    import veritas.research.parent_child_r98.constructor as production
    monkeypatch.setattr(production, "construct_children", lambda *a, **k: pytest.fail("production called"))
    assert reference_children(parent, layout, modes, beta) == children


@pytest.mark.parametrize("bad", (True, 63, 1025))
def test_bad_group_schedule_is_rejected(case128, bad):
    child = case128[-1][-1]
    record = decode(child.schedule_bytes)
    record["used"]["r"] = bad
    with pytest.raises(ValueError):
        replace(child, schedule_bytes=canonical(record))


def test_child_group_range_is_schedule_bound(case128):
    child = case128[-1][-1]
    with pytest.raises(ValueError, match="group"):
        replace(child, group=128)
    record = decode(child.schedule_bytes)
    record["used"]["r"] = 64
    with pytest.raises(ValueError, match="group"):
        replace(child, schedule_bytes=canonical(record))


def test_source_schedule_cannot_use_finite_radix(case128):
    child = case128[-1][0]
    record = decode(child.schedule_bytes)
    record["semantics"] = Semantics.SOURCE_QUALIFIED.value
    with pytest.raises(ValueError, match="exactly 64"):
        replace(child, schedule_bytes=canonical(record))
    with pytest.raises(ValueError, match="non-64"):
        layout_group_count(SimpleNamespace(semantics=Semantics.SOURCE_QUALIFIED), case128[1])
    # _admitted skips mode replay, never the pinned group-count admission.
    with pytest.raises(ValueError, match="non-64"):
        construct_children(SimpleNamespace(semantics=Semantics.SOURCE_QUALIFIED),
                           case128[1], case128[2], case128[3],
                           budget=Budget(DEFAULT_SHRINKING_POLICY), _admitted=True)
    record = decode(child.schedule_bytes)
    record["source"]["r"] = 128
    with pytest.raises(ValueError, match="pinned source"):
        replace(child, schedule_bytes=canonical(record))


@pytest.mark.parametrize("attack", ("missing", "duplicate", "schedule"))
def test_independent_inventory_rejects_group_mutations(case128, attack):
    parent, layout, modes, beta, children = case128
    changed = list(children)
    if attack == "missing":
        changed.pop()
    elif attack == "duplicate":
        changed[-1] = changed[-2]
    else:
        record = decode(changed[0].schedule_bytes)
        record["used"]["r"] = 256
        changed[0] = replace(changed[0], schedule_bytes=canonical(record))
    with pytest.raises(ValueError):
        verify_children(parent, layout, modes, beta, tuple(changed),
                        budget=Budget(DEFAULT_SHRINKING_POLICY), _admitted=True)


def test_reduction_term_rejects_partial_and_mixed_group_schedules(case128):
    _, _, _, beta, children = case128
    values = tuple(((1, 0),) for _ in children)
    term = ChildReductionTerm(beta, children, values, ((1, 0),))
    assert len(term.children) == 128
    with pytest.raises(ValueError):
        ChildReductionTerm(beta, children[:-1], values[:-1], ((1, 0),))
    record = decode(children[-1].schedule_bytes)
    record["used"]["r"] = 256
    mixed = children[:-1] + (replace(children[-1], schedule_bytes=canonical(record)),)
    with pytest.raises(ValueError):
        ChildReductionTerm(beta, mixed, values, ((1, 0),))


def test_changed_layout_group_count_cannot_reuse_old_mode_admission(case128):
    parent, layout, modes, beta, children = case128
    source = layout.source
    source["r"], source["D"] = 256, 256**2
    changed = replace(layout, source_bytes=canonical(source))
    with pytest.raises(ValueError, match="ancestry"):
        construct_children(parent, changed, modes, beta, budget=Budget(DEFAULT_SHRINKING_POLICY),
                           _admitted=True)
    with pytest.raises(ValueError, match="ancestry"):
        verify_children(parent, changed, modes, beta, children,
                        budget=Budget(DEFAULT_SHRINKING_POLICY), _admitted=True)


@pytest.mark.parametrize("attack", ("strategy", "class_count", "group_bool", "source_radix"))
def test_layout_group_metadata_rejected(case128, attack):
    parent, layout, *_ = case128
    if attack == "strategy":
        changed = replace(layout, strategy="canonical")
    else:
        source = layout.source
        if attack == "class_count":
            source["D"] += 1
        elif attack == "group_bool":
            source["r"] = True
        else:
            source["r"] = 64
        changed = replace(layout, source_bytes=canonical(source))
    with pytest.raises(ValueError):
        audit_layout(parent, changed)
