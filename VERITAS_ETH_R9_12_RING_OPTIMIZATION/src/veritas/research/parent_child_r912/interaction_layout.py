"""Circulant interaction packet layouts (separated singleton groups)."""
from __future__ import annotations

from veritas.research.parent_child_r98.model import (
    Budget,
    ChildGraph,
    PacketLayout,
    ParentCall,
    canonical,
)
from veritas.research.parent_child_r98.packing import audit_layout, construct_layout
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout


def _packet_for_parent_edge(source: dict, parent_edge: int) -> dict:
    for packet in source["packets"]:
        for _slot, edge in packet["occupied_slots"]:
            if edge == parent_edge:
                return packet
    raise ValueError(f"no packet occupies parent edge {parent_edge}")


def circulant_separated_layout(
    parent: ParentCall,
    a: int,
    u: int,
    budget: Budget,
    *,
    min_circulant_vertices: int = 32,
) -> PacketLayout:
    """D3 layout with one row/column group per circulant vertex (requires ``3n`` wires).

    The interaction research fixture uses ``n == min_circulant_vertices`` (default 32,
    i.e. 96 wires).  Smaller circulants generally fail vertex-shrinking preflight.
    """
    if (a, u) != (1, 1):
        raise ValueError("circulant separated layout uses a=u=1")
    n = parent.edge_count // 3
    if n < min_circulant_vertices or parent.edge_count != 3 * n:
        raise ValueError(
            f"circulant separated layout requires at least {min_circulant_vertices} "
            f"vertices per side (3n wires); got n={n}"
        )
    src = construct_vertex_shrinking_layout(parent, budget=budget).source
    src["row_labels"] = {str(i): [i] for i in range(n)}
    src["column_labels"] = {str(i): [n + i] for i in range(n)}
    src["H_pad"] = 2
    src["packets"] = sorted(
        [
            {
                "symbol_pairs": [[r, n + c]],
                "index": 0,
                "occupied_slots": [[0, e]],
            }
            for e, (r, c) in enumerate(parent.bipartite_edges())
        ],
        key=lambda p: p["symbol_pairs"],
    )
    layout = PacketLayout(
        parent.content_digest, 1, 1, canonical(src), "balanced_vertices"
    )
    if not audit_layout(parent, layout)["group_load_bound_met"]:
        raise ValueError("circulant separated layout failed group load audit")
    return layout


def child_layout_for_nesting(
    child: ChildGraph,
    call: ParentCall,
    ancestor_layout: PacketLayout,
    *,
    budget: Budget,
) -> PacketLayout:
    """Preserve ancestor circulant labels when nesting on a constructed child.

    Default ``construct_layout`` uses canonical implicit packing and renumbers
    group labels. Grandchild products must inherit ``balanced_vertices`` row/column
    groups from the ancestor jet layout.
    """
    if ancestor_layout.strategy != "balanced_vertices":
        return construct_layout(
            call, a=ancestor_layout.a, u=ancestor_layout.u, budget=budget
        )
    ancestor_source = ancestor_layout.source
    parent_edges = ancestor_source["edges"]
    edges = [list(edge) for edge in call.bipartite_edges()]
    row_labels: dict[str, list[int]] = {}
    column_labels: dict[str, list[int]] = {}
    packets = []
    for child_edge in range(call.edge_count):
        parent_edge = child.edge_map[child_edge][1]
        parent_row, parent_col = parent_edges[parent_edge]
        child_row, child_col = edges[child_edge]
        row_labels.setdefault(str(child_row), list(ancestor_source["row_labels"][str(parent_row)]))
        column_labels.setdefault(
            str(child_col), list(ancestor_source["column_labels"][str(parent_col)])
        )
        parent_packet = _packet_for_parent_edge(ancestor_source, parent_edge)
        packets.append(
            {
                "symbol_pairs": [list(pair) for pair in parent_packet["symbol_pairs"]],
                "index": parent_packet["index"],
                "occupied_slots": [[0, child_edge]],
            }
        )
    packets.sort(key=lambda packet: packet["symbol_pairs"])
    inherited_keys = ("schema", "L", "a", "r", "D", "H_pad", "claim")
    source = {key: ancestor_source[key] for key in inherited_keys if key in ancestor_source}
    source.update(
        M=call.edge_count,
        edges=edges,
        row_labels=row_labels,
        column_labels=column_labels,
        packets=packets,
    )
    layout = PacketLayout(
        call.content_digest,
        ancestor_layout.a,
        ancestor_layout.u,
        canonical(source),
        ancestor_layout.strategy,
    )
    try:
        audit_layout(call, layout)
        return layout
    except ValueError:
        return construct_layout(
            call, a=ancestor_layout.a, u=ancestor_layout.u, budget=budget
        )
