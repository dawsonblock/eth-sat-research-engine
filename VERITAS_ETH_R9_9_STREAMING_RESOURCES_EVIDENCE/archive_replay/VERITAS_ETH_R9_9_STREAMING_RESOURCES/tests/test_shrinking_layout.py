"""Actual port-load bounds for a finite shrinking packet construction."""

from dataclasses import replace

import pytest

from veritas.research.parent_child_r98.model import (
    Budget,
    ParentCall,
    Policy,
    Refusal,
    canonical,
)
from veritas.research.parent_child_r98.shrinking_layout import (
    audit_shrinking_layout,
    audit_vertex_shrinking_layout,
    construct_shrinking_layout,
    construct_vertex_shrinking_layout,
)
from veritas.research.tapered_v4.source_recipes import make_reference
from veritas.research.tapered_v4.source_state import SourceVertex


def path_components(lengths):
    """Disjoint bipartite paths; tensor arities never exceed two."""
    edges, row_base, column_base = [], 0, 0
    for length in lengths:
        for k in range(length):
            edges.append((row_base + (k + 1) // 2, column_base + k // 2))
        row_base += length // 2 + 1
        column_base += (length + 1) // 2
    return network_from_edges(edges)


def network_from_edges(edges):
    vertices = []
    refs = {}
    for side, index in (("row", 0), ("column", 1)):
        for vertex in sorted({edge[index] for edge in edges}):
            ports = tuple(i for i, edge in enumerate(edges) if edge[index] == vertex)
            arity = len(ports)
            if arity not in refs:
                refs[arity] = make_reference(
                    kind="dense",
                    arity=arity,
                    creation_precision=5,
                    defining_polynomial=7,
                    jet_length=1,
                    data=[[[1, 0]]] * (1 << arity),
                )
            vertices.append(SourceVertex(side, vertex, ports, refs[arity]))
    return ParentCall(1024, 0, 5, 7, len(edges), tuple(vertices))


def budget():
    return Budget(Policy(max_edges=1024))


@pytest.mark.parametrize("M,largest", ((484, 44), (44, 4)))
def test_vertex_balancing_shrinks_connected_cycles(M, largest):
    n = M // 2
    parent = network_from_edges(
        [(row, column) for row in range(n) for column in (row, (row + 1) % n)]
    )
    layout = construct_vertex_shrinking_layout(parent, budget=budget())
    report = audit_vertex_shrinking_layout(parent, layout)
    assert report["largest_child_edges"] == largest
    assert all(64 * edges <= 6 * M for edges in report["child_edge_counts"])
    assert sum(report["child_edge_counts"]) == 2 * M
    assert report["strict_shrink"] and report["group_load_bound_met"]
    source = layout.source
    assert any(
        source["row_labels"][str(r)] != source["column_labels"][str(c)]
        for r, c in parent.bipartite_edges()
    )
    assert any(packet["occupied_slots"][0][0] == 1 for packet in source["packets"])
    assert not report["source_qualified"]


def test_vertex_layout_refuses_an_unplaceable_whole_vertex():
    parent = network_from_edges(
        [(row, column) for row in range(11) for column in (row, (row + 1) % 11)]
    )
    with pytest.raises(Refusal, match="vertex degree exceeds"):
        construct_vertex_shrinking_layout(parent, budget=budget())


def test_vertex_layout_checks_reverse_orientation():
    parent = network_from_edges(
        [(row, column) for row in range(22) for column in (row, (row + 1) % 22)]
    )
    layout = construct_vertex_shrinking_layout(parent, budget=budget())
    source = layout.source
    packet = next(p for p in source["packets"] if p["occupied_slots"][0][0] == 1)
    packet["occupied_slots"][0][0] = 0
    with pytest.raises(ValueError):
        audit_vertex_shrinking_layout(
            parent, replace(layout, source_bytes=canonical(source))
        )


@pytest.mark.parametrize(
    "components,largest,nonempty",
    [((1,) * 484, 44, 22), ((2,) * 22, 4, 22)],
)
def test_component_layout_gives_actual_shrinking_half_edge_loads(
    components, largest, nonempty
):
    parent = path_components(components)
    layout = construct_shrinking_layout(parent, budget=budget())
    result = audit_shrinking_layout(parent, layout)
    assert result["largest_child_edges"] == largest
    assert sum(n > 0 for n in result["child_edge_counts"]) == nonempty
    assert sum(result["child_edge_counts"]) == 2 * parent.edge_count
    assert all(64 * n <= 6 * parent.edge_count for n in result["child_edge_counts"])
    assert result["group_load_bound_met"] and result["strict_shrink"]
    assert not result["source_qualified"] and not result["source_eligible"]
    assert not result["packet_bound_met"]
    assert (
        layout.content_digest
        == construct_shrinking_layout(parent, budget=budget()).content_digest
    )


def test_component_too_large_is_refused_without_splitting_vertices():
    parent = path_components((23,) + (1,) * 461)
    with pytest.raises(Refusal, match="component exceeds") as error:
        construct_shrinking_layout(parent, budget=budget())
    assert error.value.status == "INCONCLUSIVE_SHRINKING_LAYOUT"


def test_nonempty_small_parent_cannot_meet_this_strategys_side_bound():
    with pytest.raises(Refusal, match="per-side bound"):
        construct_shrinking_layout(path_components((1,) * 16), budget=budget())


def test_overloaded_but_geometrically_valid_group_is_rejected():
    parent = path_components((1,) * 484)
    layout = construct_shrinking_layout(parent, budget=budget())
    source = layout.source
    for side in ("row_labels", "column_labels"):
        for label in source[side].values():
            if label == [1]:
                label[0] = 0
    for packet in source["packets"]:
        if packet["symbol_pairs"] == [[1, 1]]:
            packet["symbol_pairs"] = [[0, 0]]
            packet["index"] += 22
    source["H_pad"] = 88
    forged = replace(layout, source_bytes=canonical(source))
    with pytest.raises(Refusal, match="load bound failed"):
        audit_shrinking_layout(parent, forged)


@pytest.mark.parametrize(
    "attack", ("missing", "duplicate", "orientation", "slot", "padding")
)
def test_mutated_packet_geometry_or_padding_is_rejected(attack):
    parent = path_components((2,) * 22)
    layout = construct_shrinking_layout(parent, budget=budget())
    source = layout.source
    if attack == "missing":
        source["packets"].pop()
    elif attack == "duplicate":
        source["packets"][1]["occupied_slots"][0][1] = source["packets"][0][
            "occupied_slots"
        ][0][1]
    elif attack == "orientation":
        source["packets"][0]["symbol_pairs"] = [[0, 1]]
    elif attack == "slot":
        source["packets"][0]["occupied_slots"][0][0] = 1
    else:
        source["H_pad"] *= 2
    with pytest.raises(ValueError):
        audit_shrinking_layout(parent, replace(layout, source_bytes=canonical(source)))
