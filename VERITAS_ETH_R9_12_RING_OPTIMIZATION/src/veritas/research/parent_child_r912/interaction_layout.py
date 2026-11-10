"""Circulant interaction packet layouts (separated singleton groups)."""
from __future__ import annotations

from veritas.research.parent_child_r98.model import Budget, PacketLayout, ParentCall, canonical
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout


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
