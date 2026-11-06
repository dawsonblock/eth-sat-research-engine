"""Construct actual 64-group children, retaining lazy creation-time recipes."""

from veritas.research.tapered_v4.source_recipes import EntryLimits, make_reference
from veritas.research.tapered_v4.source_state import SourceVertex

from .model import ChildGraph, canonical, schedule_record
from .modes import verify_modes


def construct_children(parent, layout, modes, beta, *, budget, _admitted=False):
    if not _admitted:
        verify_modes(parent, layout, modes, budget=budget)
    m, src = modes.certificate, layout.source
    if (
        beta.modes_digest != modes.content_digest
        or len(beta.values) != len(m["modes"])
        or sum(x * z["weight"] for x, z in zip(beta.values, m["modes"]))
        >= m["precision"]
    ):
        raise ValueError("invalid child exponent tuple")
    coordinate = (abs(m["node"]) & -abs(m["node"])).bit_length() - 1
    labels = {"row": src["row_labels"], "column": src["column_labels"]}
    groups = {
        (v.side, v.vertex_id): labels[v.side].get(str(v.vertex_id), [0] * layout.a)[
            coordinate
        ]
        for v in parent.vertices
    }
    owners = {
        (v.side, e): (v.vertex_id, pos)
        for v in parent.vertices
        for pos, e in enumerate(v.ports)
    }
    packets = {
        e: (pid, slot)
        for pid, packet in enumerate(src["packets"])
        for slot, e in packet["occupied_slots"]
    }
    schedule = canonical(schedule_record(parent, layout))
    result = []
    for g in range(64):
        budget.tick()
        inherited = tuple(
            (v.side, v.vertex_id)
            for v in parent.vertices
            if groups[v.side, v.vertex_id] == g
        )
        variables = tuple(
            (kind, e)
            for side, kind in (("row", "Y"), ("column", "X"))
            for e in range(parent.edge_count)
            if groups[side, owners[side, e][0]] == g
        )
        edges = {key: i for i, key in enumerate(variables)}
        edge_map = tuple(
            (kind, e, *packets[e], *owners["row" if kind == "Y" else "column", e])
            for kind, e in variables
        )
        vertices = []
        for v in parent.vertices:
            if (v.side, v.vertex_id) in inherited:
                ports = tuple(
                    edges["Y" if v.side == "row" else "X", e] for e in v.ports
                )
                vertices.append(SourceVertex("row", len(vertices), ports, v.tensor))
        packet_ids = []
        zero = [[0] * m["extension_degree"]]
        for pid, packet in enumerate(src["packets"]):
            ys = [e for _, e in packet["occupied_slots"] if ("Y", e) in edges]
            xs = [e for _, e in packet["occupied_slots"] if ("X", e) in edges]
            if not ys and not xs:
                continue
            ports = tuple(
                edges[kind, e] for kind, es in (("Y", ys), ("X", xs)) for e in es
            )
            coefficients = {(y, x): c for y, x, c in m["local"]}
            local = [[coefficients.get((y, x), zero) for x in xs] for y in ys]
            targets, sources = [], []
            for mid, mode in enumerate(m["modes"]):
                if mode["packet"] != pid:
                    continue
                if mode["target_group"] == g:
                    byrow = dict(mode["rows"])
                    targets.append([beta.values[mid], [byrow.get(y, zero) for y in ys]])
                if mode["source_group"] == g:
                    bycol = dict(mode["column_terms"])
                    sources.append(
                        [
                            beta.values[mid],
                            [bycol.get(x, 0) % (1 << m["precision"]) for x in xs],
                        ]
                    )
            data = [
                list(range(len(ys))),
                list(range(len(ys), len(ports))),
                local,
                targets,
                sources,
            ]
            tensor = make_reference(
                kind="packet",
                arity=len(ports),
                creation_precision=m["precision"],
                defining_polynomial=parent.defining_polynomial,
                jet_length=1,
                data=data,
                limits=EntryLimits(max_seconds=60),
            )
            vertices.append(SourceVertex("column", len(packet_ids), ports, tensor))
            packet_ids.append(pid)
        child = ChildGraph(
            parent.content_digest,
            layout.content_digest,
            modes.content_digest,
            schedule,
            parent.depth + 1,
            m["node"],
            tuple(m["zeta"]),
            beta,
            g,
            edge_map,
            inherited,
            tuple(packet_ids),
            tuple(vertices),
            m["precision"],
            parent.defining_polynomial,
        )
        result.append(child)
    return tuple(result)
