"""Packer admission and an occurrence-based packet audit, with separate scopes."""

from collections import Counter

from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing,
    implicit_sparse_mode_source,
)
from veritas.research.paper_verification.exact_parameters import source_schedule

from .model import PacketLayout, Refusal, Semantics, canonical


def preconditions(parent):
    q = source_schedule(parent.root_s, parent.depth)
    M, L, D, delta = (
        parent.edge_count,
        q["L"],
        q["packing_class_count"],
        q["degree_limit"],
    )
    checks = {
        "M_ge_2_D_squared_delta": M >= 2 * D * D * delta,
        "M_ge_LD": M >= L * D,
        "2L_le_delta": 2 * L <= delta,
    }
    active = M > q["leaf_threshold"] and q["u"] > 0
    status = (
        "INCONCLUSIVE_SOURCE_SCHEDULE"
        if not active
        else "NUMERIC_PRECONDITIONS_MET"
        if all(checks.values())
        else "INCONCLUSIVE_SOURCE_PACKING"
    )
    return {
        "status": status,
        "source_active": active,
        "checks": checks,
        "schedule": q,
        "scope": "CURRENT_NODE_NUMERICS_ONLY",
        "above_leaf_cutoff": M > q["leaf_threshold"],
        "positive_u": q["u"] > 0,
        "actual_packing_verified": False,
        "descendant_schedules_verified": False,
        "source_qualified": False,
    }


def construct_layout(parent, *, a=2, u=1, strategy="canonical", budget):
    budget.tick()
    numeric = preconditions(parent)
    if parent.semantics is Semantics.FINITE_BOUNDARY_EXACT:
        raise ValueError("boundary semantics cannot enter the packet algorithm")
    if parent.semantics is Semantics.SOURCE_QUALIFIED:
        if numeric["status"] != "NUMERIC_PRECONDITIONS_MET":
            raise Refusal(
                numeric["status"],
                "source packing preconditions failed before construction",
            )
        if (a, u, strategy) != (
            numeric["schedule"]["a"],
            numeric["schedule"]["u"],
            "canonical",
        ):
            raise Refusal(
                "INCONCLUSIVE_SOURCE_SCHEDULE", "source parameters may not be scaled"
            )
    if not 1 <= parent.edge_count <= budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "bounded packet parent edge cap")
    packing = construct_implicit_packing(
        parent.bipartite_edges(), r=64, a=a, max_work=3_000_000
    )
    src = implicit_sparse_mode_source(packing, max_work=1_000_000)
    if strategy == "scaled_singletons":
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise ValueError("singleton fixtures require scaled semantics")
        # A deterministic finite layout with one real slot per packet. It has
        # no cross-group modes, and intentionally fails the source load bound.
        src["row_labels"] = {
            str(v.vertex_id): [0] * a
            for v in parent.vertices
            if v.side == "row" and v.ports
        }
        src["column_labels"] = {
            str(v.vertex_id): [0] * a
            for v in parent.vertices
            if v.side == "column" and v.ports
        }
        src["H_pad"] = parent.edge_count * (1 << a)
        src["packets"] = [
            {
                "symbol_pairs": [[0, 0] for _ in range(a)],
                "index": e,
                "occupied_slots": [[0, e]],
            }
            for e in range(parent.edge_count)
        ]
    layout = PacketLayout(parent.content_digest, a, u, canonical(src), strategy)
    report = audit_layout(parent, layout)
    if strategy == "canonical":
        from veritas.research.paper_verification.packing_checker import check_packing

        prior = check_packing(src, parent.bipartite_edges())
        if (
            prior["padded_packets"],
            prior["packet_bound_met"],
            prior["both_port_bounds_met"],
        ) != (
            report["padded_packets"],
            report["packet_bound_met"],
            report["group_load_bound_met"],
        ):
            raise ValueError("independent packet checker disagreement")
    if parent.semantics is Semantics.SOURCE_QUALIFIED and not report["source_eligible"]:
        raise Refusal("INCONCLUSIVE_SOURCE_PACKING", "actual packet loads failed")
    return layout


def audit_layout(parent, layout):
    if layout.parent_digest != parent.content_digest:
        raise ValueError("layout belongs to another parent")
    src = layout.source
    M, L, a = parent.edge_count, 1 << layout.a, layout.a
    if any(type(src[k]) is not int for k in ("M", "L", "a", "r")):
        raise ValueError("integer packing dimensions required")
    if (src["M"], src["L"], src["a"], src["r"]) != (M, L, a, 64):
        raise ValueError("packet dimensions differ")
    if (
        type(src["edges"]) is not list
        or any(
            type(pair) is not list
            or len(pair) != 2
            or any(type(endpoint) is not int for endpoint in pair)
            for pair in src["edges"]
        )
        or src["edges"] != [list(e) for e in parent.bipartite_edges()]
    ):
        raise ValueError("packet edge endpoints differ")
    rows, columns = src["row_labels"], src["column_labels"]
    for side, labels in (("row", rows), ("column", columns)):
        used = {str(v.vertex_id) for v in parent.vertices if v.side == side and v.ports}
        if set(labels) != used:
            raise ValueError("packet vertex label coverage")
        for label in labels.values():
            if (
                type(label) is not list
                or len(label) != a
                or any(type(x) is not int or not 0 <= x < 64 for x in label)
            ):
                raise ValueError("invalid vertex label")
    seen, addresses, order = set(), set(), []
    loads = [[Counter(), Counter()] for _ in range(a)]
    H = src["H_pad"]
    if type(H) is not int or H <= 0 or H % L:
        raise ValueError("padded occupancy capacity")
    for packet in src["packets"]:
        if set(packet) != {"symbol_pairs", "index", "occupied_slots"}:
            raise ValueError("explicit sparse packet required")
        pairs = packet["symbol_pairs"]
        if (
            type(pairs) is not list
            or len(pairs) != a
            or any(
                type(x) is not list
                or len(x) != 2
                or any(type(y) is not int or not 0 <= y < 64 for y in x)
                or x[0] > x[1]
                for x in pairs
            )
        ):
            raise ValueError("invalid packet symbols")
        index = packet["index"]
        # A packet uses 2**k slots from each compatible directed label class
        # when k coordinates have equal symbols.
        # The pattern therefore has H / 2**k packets, not always H / L.
        copies = 1 << sum(x == y for x, y in pairs)
        if type(index) is not int or not 0 <= index < H // copies:
            raise ValueError("packet index exceeds capacity")
        key = (tuple(map(tuple, pairs)), index)
        order.append(key)
        if key in addresses:
            raise ValueError("duplicate packet address")
        addresses.add(key)
        previous = -1
        if not packet["occupied_slots"]:
            raise ValueError("sparse packet must have a real port")
        for slot, e in packet["occupied_slots"]:
            if (
                type(slot) is not int
                or type(e) is not int
                or not previous < slot < L
                or not 0 <= e < M
                or e in seen
            ):
                raise ValueError("duplicated edge or slot")
            previous = slot
            seen.add(e)
            row, col = src["edges"][e]
            for j, (x, y) in enumerate(zip(rows[str(row)], columns[str(col)])):
                if pairs[j] != [min(x, y), max(x, y)] or (
                    x != y and ((slot >> j) & 1) != int(x > y)
                ):
                    raise ValueError("wrong packet orientation or label")
                loads[j][0][x] += 1
                loads[j][1][y] += 1
    if seen != set(range(M)) or order != sorted(order):
        raise ValueError("omitted edge or noncanonical packet ordering")
    padded_packets = 64 ** (2 * a) * H // L
    port_bound = all(
        64 * n <= 3 * M
        for coordinate in loads
        for side in coordinate
        for n in side.values()
    )
    packet_bound = padded_packets * L <= 3 * M
    numeric = preconditions(parent)
    q = numeric["schedule"]
    matched = (a, layout.u) == (q["a"], q["u"])
    eligible = (
        numeric["status"] == "NUMERIC_PRECONDITIONS_MET"
        and matched
        and packet_bound
        and port_bound
        and parent.maximum_degree <= q["degree_limit"]
    )
    return {
        "packing_precondition_verdict": numeric,
        "source_eligible": eligible,
        "scaled_experiment": parent.semantics is Semantics.FINITE_SCALED_EXPERIMENT,
        "occupied_packets": len(order),
        "padded_packets": padded_packets,
        "packet_bound_met": packet_bound,
        "group_load_bound_met": port_bound,
        "actual_group_loads": [
            [{str(g): n for g, n in x.items()} for x in coord] for coord in loads
        ],
        "exact_edge_coverage": True,
        "same_slot_endpoints": True,
        "source_qualified": False,
        "packet_load_proof": "FINITE_OCCURRENCE_AUDIT",
    }
