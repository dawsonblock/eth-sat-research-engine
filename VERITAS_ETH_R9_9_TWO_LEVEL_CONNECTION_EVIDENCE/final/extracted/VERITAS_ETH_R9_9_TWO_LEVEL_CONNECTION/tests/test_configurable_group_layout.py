"""Finite group opt-in uses actual whole-vertex loads and packet geometry."""

from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.eth_packing_v26.geometry_audit import audit_sparse_packet_geometry
from veritas.research.parent_child_r98.model import Budget, Policy, Refusal, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_layout import (
    audit_vertex_shrinking_layout,
    construct_vertex_shrinking_layout,
)


def cycle_parent():
    return load_input(Path(__file__).resolve().parents[1] / "examples/r98_shrinking_cycle484.json")


def budget():
    return Budget(Policy(max_edges=1024))


@pytest.mark.parametrize("groups,largest,crossings", ((64, 44, 22), (128, 20, 49),
                                                     (256, 8, 121), (512, 4, 242)))
def test_actual_cycle_loads_and_crossings(groups, largest, crossings):
    parent = cycle_parent()
    layout = construct_vertex_shrinking_layout(parent, budget=budget(), groups=groups)
    report = audit_vertex_shrinking_layout(parent, layout)
    source = layout.source
    assert source["r"] == report["group_count"] == groups
    assert source["D"] == groups**2
    assert report["per_side_capacity"] == 3 * 484 // groups
    assert len(report["child_edge_counts"]) == groups
    assert report["largest_child_edges"] == largest
    assert sum(report["child_edge_counts"]) == 968
    assert all(groups * edges <= 6 * 484 for edges in report["child_edge_counts"])
    assert sum(source["row_labels"][str(r)] != source["column_labels"][str(c)]
               for r, c in parent.bipartite_edges()) == crossings
    assert report["strict_shrink"] and report["group_load_bound_met"]
    assert not report["source_eligible"] and not report["source_qualified"]


@pytest.mark.parametrize("groups", (True, 63, 1025, 64.0, "512", None))
def test_group_parameter_is_bounded_and_strictly_typed(groups):
    with pytest.raises(ValueError, match="group count"):
        construct_vertex_shrinking_layout(cycle_parent(), budget=budget(), groups=groups)


def test_too_many_groups_refuse_degree_two_without_splitting_vertices():
    with pytest.raises(Refusal, match="vertex degree exceeds") as error:
        construct_vertex_shrinking_layout(cycle_parent(), budget=budget(), groups=1024)
    assert error.value.status == "INCONCLUSIVE_SHRINKING_LAYOUT"


def test_default_and_explicit_64_keep_identical_layout_bytes():
    parent = cycle_parent()
    default = construct_vertex_shrinking_layout(parent, budget=budget())
    explicit = construct_vertex_shrinking_layout(parent, budget=budget(), groups=64)
    assert default.source_bytes == explicit.source_bytes
    assert default.content_digest == explicit.content_digest
    # Recorded from the sealed general checkout before the group extension.
    assert default.content_digest == "9e4c04045d91e559eb00438e18a71a5342f712e0110e2a27a176839a8a345bde"


def test_geometry_requires_explicit_high_group_opt_in():
    layout = construct_vertex_shrinking_layout(cycle_parent(), budget=budget(), groups=512)
    assert not audit_sparse_packet_geometry(layout.source)["valid"]
    assert audit_sparse_packet_geometry(layout.source, max_groups=512)["valid"]
    for invalid in (True, 1, 1025, 512.0):
        with pytest.raises(ValueError, match="group audit cap"):
            audit_sparse_packet_geometry(layout.source, max_groups=invalid)


@pytest.mark.parametrize("attack", ("class_count", "radix", "label", "padding", "slot"))
def test_high_group_geometry_rejects_corrupted_metadata(attack):
    parent = cycle_parent()
    layout = construct_vertex_shrinking_layout(parent, budget=budget(), groups=512)
    source = layout.source
    if attack == "class_count":
        source["D"] = 64**2
    elif attack == "radix":
        source["r"] = 64
    elif attack == "label":
        source["row_labels"]["0"] = [512]
    elif attack == "padding":
        source["H_pad"] *= 2
    else:
        source["packets"][0]["occupied_slots"][0][0] ^= 1
    with pytest.raises(ValueError):
        audit_vertex_shrinking_layout(parent, replace(layout, source_bytes=canonical(source)))
