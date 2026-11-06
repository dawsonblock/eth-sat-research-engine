"""Bounded vertex-balanced packet layouts with checked child shrinkage.

These are finite scaled constructions, not the source's universal packer.
The vertex strategy admits connected networks by balancing the two sides
independently; a separate component-preserving specialization is retained.
Both refuse unsatisfied per-side loads and use the X/Y half-edge geometry
consumed by the ordinary child constructor.
"""

from veritas.research.eth_packing_v26.geometry_audit import (
    audit_sparse_packet_geometry,
)
from veritas.research.eth_packing_v26.implicit import SPARSE_MODE_SCHEMA

from .model import PacketLayout, Refusal, Semantics, canonical
from .packing import audit_layout

STRATEGY = "balanced_components"
VERTEX_STRATEGY = "balanced_vertices"


def audit_vertex_shrinking_layout(parent, layout):
    """Audit actual side loads without assuming components stay in one group."""
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError("vertex shrinking layouts require finite scaled semantics")
    if (layout.strategy, layout.a, layout.u) != (VERTEX_STRATEGY, 1, 1):
        raise ValueError("unsupported vertex shrinking layout")
    report = audit_layout(parent, layout)
    source = layout.source
    geometry = audit_sparse_packet_geometry(source)
    if not geometry.get("valid"):
        raise ValueError(
            "independent shrinking geometry: " + geometry.get("reason", "refused")
        )
    coordinate = geometry["coordinates"][0]
    if (
        not report["group_load_bound_met"]
        or not coordinate["per_side_port_bound"]
        or not coordinate["per_child_six_M_over_r"]
    ):
        raise Refusal(
            "INCONCLUSIVE_SHRINKING_LAYOUT", "actual vertex group load bound failed"
        )
    counts = {}
    for packet in source["packets"]:
        pair = tuple(packet["symbol_pairs"][0])
        if len(packet["occupied_slots"]) != 1:
            raise ValueError("vertex shrinking packet must contain one real edge")
        if packet["index"] != counts.get(pair, 0):
            raise ValueError("noncanonical vertex packet index")
        counts[pair] = counts.get(pair, 0) + 1
    required = max(
        (count * (2 if pair[0] == pair[1] else 1) for pair, count in counts.items()),
        default=0,
    )
    height = 2 * ((required + 1) // 2)
    if source["H_pad"] != height:
        raise ValueError("vertex packet padding differs from actual pattern occupancy")
    child_edges = tuple(
        group["predicted_child_wires"] for group in coordinate["groups"]
    )
    if sum(child_edges) != 2 * parent.edge_count or any(
        64 * n > 6 * parent.edge_count for n in child_edges
    ):
        raise ValueError("vertex child half-edge count mismatch")
    return {
        **report,
        "status": "PASS_FINITE_SHRINKING_LAYOUT",
        "strategy": VERTEX_STRATEGY,
        "vertex_assignment_verified": True,
        "child_edge_counts": child_edges,
        "largest_child_edges": max(child_edges, default=0),
        "all_child_six_M_over_r": True,
        "strict_shrink": all(n < parent.edge_count for n in child_edges),
        "source_qualified": False,
        "universal_packer_proved": False,
    }


def construct_vertex_shrinking_layout(parent, *, budget):
    """Balance whole vertices independently on the two sides.

    Connected components may span groups. Each side uses deterministic first
    fit by decreasing vertex degree, with capacity floor(3M/64). This is a
    bounded sufficient construction and refuses any unplaceable vertex.
    """
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError("vertex shrinking layouts require finite scaled semantics")
    M = parent.edge_count
    if not 1 <= M <= budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "shrinking layout parent edge cap")
    capacity = 3 * M // 64
    if capacity == 0:
        raise Refusal(
            "INCONCLUSIVE_SHRINKING_LAYOUT",
            "nonempty vertex cannot meet the per-side bound",
        )
    labels = {"row": {}, "column": {}}
    for side, side_labels in labels.items():
        loads = [0] * 64
        vertices = sorted(
            (v for v in parent.vertices if v.side == side and v.ports),
            key=lambda v: (-len(v.ports), v.vertex_id),
        )
        for vertex in vertices:
            degree = len(vertex.ports)
            if degree > capacity:
                raise Refusal(
                    "INCONCLUSIVE_SHRINKING_LAYOUT",
                    "vertex degree exceeds the per-side group capacity",
                )
            group = next(
                (g for g, load in enumerate(loads) if load + degree <= capacity), None
            )
            if group is None:
                raise Refusal(
                    "INCONCLUSIVE_SHRINKING_LAYOUT",
                    "vertex first-fit exhausted 64 groups",
                )
            side_labels[str(vertex.vertex_id)] = [group]
            loads[group] += degree
            budget.tick(degree + 64)
    edges, counts, packets = parent.bipartite_edges(), {}, []
    for edge, (row, column) in enumerate(edges):
        rg, cg = labels["row"][str(row)][0], labels["column"][str(column)][0]
        pair = min(rg, cg), max(rg, cg)
        index = counts.get(pair, 0)
        packets.append(
            {
                "symbol_pairs": [list(pair)],
                "index": index,
                "occupied_slots": [[int(rg > cg), edge]],
            }
        )
        counts[pair] = index + 1
    required = max(
        count * (2 if pair[0] == pair[1] else 1) for pair, count in counts.items()
    )
    source = {
        "schema": SPARSE_MODE_SCHEMA,
        "claim": "FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS",
        "r": 64,
        "a": 1,
        "L": 2,
        "D": 4096,
        "M": M,
        "H_pad": 2 * ((required + 1) // 2),
        "edges": [list(edge) for edge in edges],
        "row_labels": labels["row"],
        "column_labels": labels["column"],
        "packets": sorted(packets, key=lambda p: (p["symbol_pairs"], p["index"])),
    }
    layout = PacketLayout(
        parent.content_digest, 1, 1, canonical(source), VERTEX_STRATEGY
    )
    audit_vertex_shrinking_layout(parent, layout)
    return layout


def _edge_components(parent, budget):
    """Union edges sharing either endpoint; isolated scalars have no edge load."""
    roots = list(range(parent.edge_count))

    def find(edge):
        while roots[edge] != edge:
            roots[edge] = roots[roots[edge]]
            edge = roots[edge]
        return edge

    for vertex in parent.vertices:
        budget.tick(len(vertex.ports) + 1)
        if vertex.ports:
            head = find(vertex.ports[0])
            for edge in vertex.ports[1:]:
                other = find(edge)
                roots[other] = head
    components = {}
    for edge in range(parent.edge_count):
        components.setdefault(find(edge), []).append(edge)
    return sorted(components.values(), key=lambda es: (-len(es), es[0]))


def audit_shrinking_layout(parent, layout):
    """Independently count actual ports and enforce the finite shrink premise.

    No component assignment or packet construction is replayed here. The two
    independent geometry auditors inspect the submitted endpoints and slots.
    Whole-component ownership follows because both ends of every edge carry
    the same group label.
    """
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError("component shrinking layouts require finite scaled semantics")
    if (layout.strategy, layout.a, layout.u) != (STRATEGY, 1, 1):
        raise ValueError("unsupported component shrinking layout")
    report = audit_layout(parent, layout)
    source = layout.source
    geometry = audit_sparse_packet_geometry(source)
    if not geometry.get("valid"):
        raise ValueError(
            "independent shrinking geometry: " + geometry.get("reason", "refused")
        )
    if not report["group_load_bound_met"] or not all(
        c["per_side_port_bound"] and c["per_child_six_M_over_r"]
        for c in geometry["coordinates"]
    ):
        raise Refusal(
            "INCONCLUSIVE_SHRINKING_LAYOUT", "actual component group load bound failed"
        )

    counts = [0] * 64
    for packet in source["packets"]:
        pair = packet["symbol_pairs"][0]
        if pair[0] != pair[1] or len(packet["occupied_slots"]) != 1:
            raise ValueError("component packet must have one same-group edge")
        if packet["occupied_slots"][0][0] != 0:
            raise ValueError("component packet must use slot zero")
        group = pair[0]
        if packet["index"] != counts[group]:
            raise ValueError("noncanonical component packet index")
        counts[group] += 1
    if source["H_pad"] != 2 * max(counts, default=0):
        raise ValueError("component padding differs from actual group occupancy")
    child_edges = tuple(2 * count for count in counts)
    if sum(child_edges) != 2 * parent.edge_count or any(
        64 * edges > 6 * parent.edge_count for edges in child_edges
    ):
        raise ValueError("component child half-edge count mismatch")
    return {
        **report,
        "status": "PASS_FINITE_SHRINKING_LAYOUT",
        "strategy": STRATEGY,
        "component_assignment_verified": True,
        "child_edge_counts": child_edges,
        "largest_child_edges": max(child_edges, default=0),
        "all_child_six_M_over_r": True,
        "strict_shrink": all(edges < parent.edge_count for edges in child_edges),
        "source_qualified": False,
        "universal_packer_proved": False,
    }


def construct_shrinking_layout(parent, *, budget):
    """First-fit whole components into 64 bins of capacity floor(3M/64).

    At each group both side loads equal its original edge count. The generated
    child therefore has twice that many edges and satisfies 64*M_child<=6*M.
    First fit fills lower-numbered groups before opening another one; spreading
    tiny components uniformly is unnecessary and can defeat a second active
    shrinking level in bounded examples.
    """
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError("component shrinking layouts require finite scaled semantics")
    M = parent.edge_count
    if not 1 <= M <= budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "shrinking layout parent edge cap")
    capacity = 3 * M // 64
    if capacity == 0:
        raise Refusal(
            "INCONCLUSIVE_SHRINKING_LAYOUT",
            "nonempty same-group component cannot meet the per-side bound",
        )
    assignments, loads = {}, [0] * 64
    for component in _edge_components(parent, budget):
        if len(component) > capacity:
            raise Refusal(
                "INCONCLUSIVE_SHRINKING_LAYOUT",
                "connected component exceeds the component-preserving group capacity",
            )
        group = next(
            (g for g, load in enumerate(loads) if load + len(component) <= capacity),
            None,
        )
        if group is None:
            raise Refusal(
                "INCONCLUSIVE_SHRINKING_LAYOUT",
                "component first-fit exhausted 64 groups",
            )
        loads[group] += len(component)
        assignments.update((edge, group) for edge in component)
        budget.tick(len(component) + 64)

    edges = parent.bipartite_edges()
    row_labels, column_labels = {}, {}
    indices, packets = [0] * 64, []
    for edge, (row, column) in enumerate(edges):
        group = assignments[edge]
        for labels, vertex in ((row_labels, row), (column_labels, column)):
            previous = labels.setdefault(str(vertex), [group])
            if previous != [group]:
                raise ValueError("component assignment split a vertex")
        packets.append(
            {
                "symbol_pairs": [[group, group]],
                "index": indices[group],
                "occupied_slots": [[0, edge]],
            }
        )
        indices[group] += 1
    packets.sort(key=lambda p: (p["symbol_pairs"][0][0], p["index"]))
    source = {
        "schema": SPARSE_MODE_SCHEMA,
        "claim": "FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS",
        "r": 64,
        "a": 1,
        "L": 2,
        "D": 4096,
        "M": M,
        "H_pad": 2 * max(loads),
        "edges": [list(edge) for edge in edges],
        "row_labels": row_labels,
        "column_labels": column_labels,
        "packets": packets,
    }
    layout = PacketLayout(parent.content_digest, 1, 1, canonical(source), STRATEGY)
    audit_shrinking_layout(parent, layout)
    return layout
