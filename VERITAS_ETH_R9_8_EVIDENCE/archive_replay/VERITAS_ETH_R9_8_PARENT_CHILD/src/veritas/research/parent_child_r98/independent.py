"""Independent child semantics and half-edge oracles; no child-builder imports.

The port checker derives incidence by scanning original tensor occurrences.
Packet coefficients are formed as a formal polynomial by the independent R95
entry oracle. The parent oracle uses rational Cauchy factors and bucket
elimination on the 2M half-edge variables, not a 2^M original contraction.
"""

from itertools import product

from veritas.research.independent_r82.point_mode_oracle import (
    _evaluate_shifted,
    _IndependentExtension,
    _Meter,
    shifted_cauchy_polynomial,
)
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic, _entry

from .model import (
    ChildGraph,
    Refusal,
    SourceTensorReference,
    SourceVertex,
    canonical,
    schedule_record,
)
from .modes import verify_modes


def eliminate_tables(factors, ar, budget):
    """Deterministic min-scope variable elimination with an explicit table cap."""
    factors = list(factors)
    while any(ports for ports, _ in factors):
        variables = {e for ports, _ in factors for e in ports}

        def scope(e, current=factors):
            return {x for ports, _ in current if e in ports for x in ports}

        edge = min(variables, key=lambda e: (len(scope(e)), e))
        incident = [(ports, table) for ports, table in factors if edge in ports]
        remaining = tuple(sorted(scope(edge) - {edge}))
        if len(remaining) > budget.policy.max_factor_bits:
            raise Refusal(
                "INCONCLUSIVE_RESOURCE_LIMIT", "independent elimination table cap"
            )
        factors = [(ports, table) for ports, table in factors if edge not in ports]
        table = {}
        for bits in product((0, 1), repeat=len(remaining)):
            budget.tick()
            assignment = dict(zip(remaining, bits))
            total = ar.zero
            for value in (0, 1):
                assignment[edge] = value
                term = ar.one
                for ports, entries in incident:
                    term = ar.mul(term, entries[tuple(assignment[p] for p in ports)])
                total = ar.add(total, term)
            table[bits] = total
        factors.append((remaining, table))
    value = ar.one
    for _, table in factors:
        value = ar.mul(value, table[()])
    return value


def vertex_tables(parent, ar, budget, *, half_edges=False):
    factors = []
    for v in parent.vertices:
        if len(v.ports) > budget.policy.max_factor_bits:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "independent tensor table cap")
        ports = (
            tuple(e + (parent.edge_count if v.side == "column" else 0) for e in v.ports)
            if half_edges
            else v.ports
        )
        table = {
            bits: _entry(v.tensor, bits, ar)
            for bits in product((0, 1), repeat=len(ports))
        }
        factors.append((ports, table))
    return factors


def contract_independent(parent, budget):
    ar = ReferenceArithmetic(
        parent.precision,
        parent.defining_polynomial,
        1,
        budget.policy.max_work - budget.work,
    )
    result = eliminate_tables(vertex_tables(parent, ar, budget), ar, budget)
    budget.tick(ar.used)
    return result


def parent_point(parent, layout, modes, *, budget):
    m, src = modes.certificate, layout.source
    ar = ReferenceArithmetic(
        m["precision"],
        parent.defining_polynomial,
        1,
        budget.policy.max_work - budget.work,
    )
    meter = _Meter(5_000_000, 60)
    scalar = _IndependentExtension(m["precision"], parent.defining_polynomial, meter)
    factors = vertex_tables(parent, ar, budget, half_edges=True)
    L = src["L"]
    for packet in src["packets"]:
        real = packet["occupied_slots"]
        cols = tuple(parent.edge_count + e for _, e in real)
        if 1 + len(cols) > budget.policy.max_factor_bits:
            raise Refusal(
                "INCONCLUSIVE_RESOURCE_LIMIT", "independent Cauchy row factor cap"
            )
        for x, row in real:
            coefficients = [
                (
                    _evaluate_shifted(
                        scalar,
                        shifted_cauchy_polynomial(
                            L, m["node"], 2 * L, x, y, meter=meter
                        ),
                        tuple(m["zeta"]),
                    ),
                )
                for y, _ in real
            ]
            table = {}
            for bits in product((0, 1), repeat=1 + len(cols)):
                value = ar.zero
                for bit, coefficient in zip(bits[1:], coefficients):
                    if bit:
                        value = ar.add(value, coefficient)
                table[bits] = value if bits[0] else ar.add(ar.one, ar.neg(value))
            factors.append(((row, *cols), table))
    value = eliminate_tables(factors, ar, budget)
    budget.tick(ar.used + meter.used)
    return value


def expected_packet_reference(src, m, g, pid, beta, f):
    """Wire format derived from source occurrences, not from an existing recipe."""
    i = (abs(m["node"]) & -abs(m["node"])).bit_length() - 1
    occupied = src["packets"][pid]["occupied_slots"]
    rows = [
        e for _, e in occupied if src["row_labels"][str(src["edges"][e][0])][i] == g
    ]
    cols = [
        e for _, e in occupied if src["column_labels"][str(src["edges"][e][1])][i] == g
    ]
    positions = [("Y", e) for e in rows] + [("X", e) for e in cols]
    zero = [[0] * (f.bit_length() - 1)]
    coefficients = []
    for row in rows:
        entries = []
        for col in cols:
            values = [c for y, x, c in m["local"] if (y, x) == (row, col)]
            if len(values) > 1:
                raise ValueError("duplicate local coefficient")
            entries.append(values[0] if values else zero)
        coefficients.append(entries)
    targets, sources = [], []
    for j, z in enumerate(m["modes"]):
        if z["packet"] == pid and z["target_group"] == g:
            targets.append(
                [
                    beta[j],
                    [next((c for e, c in z["rows"] if e == row), zero) for row in rows],
                ]
            )
        if z["packet"] == pid and z["source_group"] == g:
            sources.append(
                [
                    beta[j],
                    [
                        next((c for e, c in z["column_terms"] if e == col), 0)
                        % (1 << m["precision"])
                        for col in cols
                    ],
                ]
            )
    payload = {
        "schema": "VERITAS_SOURCE_ENTRY_V1",
        "kind": "packet",
        "arity": len(positions),
        "creation_precision": m["precision"],
        "polynomial": f,
        "jet_length": 1,
        "data": [
            list(range(len(rows))),
            list(range(len(rows), len(positions))),
            coefficients,
            targets,
            sources,
        ],
    }
    return positions, SourceTensorReference(
        len(positions),
        m["precision"],
        f,
        1,
        "VERITAS_SOURCE_ENTRY_V1:packet",
        canonical(payload),
    )


def reference_children(parent, layout, modes, beta):
    """Independent materialization for a compact submitted point transcript.

    This shares schema and reference packet semantics with the verifier only;
    neither the production constructor nor its packet recipe builder is used.
    """
    src, m = layout.source, modes.certificate
    i = (abs(m["node"]) & -abs(m["node"])).bit_length() - 1
    schedule = canonical(schedule_record(parent, layout))
    result = []
    for g in range(64):
        inherited, mapping = [], []
        for v in parent.vertices:
            labels = src["row_labels"] if v.side == "row" else src["column_labels"]
            if labels.get(str(v.vertex_id), [0] * layout.a)[i] != g:
                continue
            inherited.append(v)
            for pos, edge in enumerate(v.ports):
                hits = [
                    (pid, slot)
                    for pid, p in enumerate(src["packets"])
                    for slot, e in p["occupied_slots"]
                    if e == edge
                ]
                if len(hits) != 1:
                    raise ValueError("reference packet coverage")
                mapping.append(
                    ("Y" if v.side == "row" else "X", edge, *hits[0], v.vertex_id, pos)
                )
        mapping.sort(key=lambda x: (x[0] != "Y", x[1]))
        keys = [(row[0], row[1]) for row in mapping]
        vertices = [
            SourceVertex(
                "row",
                j,
                tuple(
                    keys.index(("Y" if v.side == "row" else "X", e)) for e in v.ports
                ),
                v.tensor,
            )
            for j, v in enumerate(inherited)
        ]
        pids = []
        for pid in range(len(src["packets"])):
            positions, ref = expected_packet_reference(
                src, m, g, pid, beta.values, parent.defining_polynomial
            )
            if positions:
                vertices.append(
                    SourceVertex(
                        "column",
                        len(pids),
                        tuple(keys.index(k) for k in positions),
                        ref,
                    )
                )
                pids.append(pid)
        result.append(
            ChildGraph(
                parent.content_digest,
                layout.content_digest,
                modes.content_digest,
                schedule,
                parent.depth + 1,
                m["node"],
                tuple(m["zeta"]),
                beta,
                g,
                tuple(mapping),
                tuple((v.side, v.vertex_id) for v in inherited),
                tuple(pids),
                tuple(vertices),
                m["precision"],
                parent.defining_polynomial,
            )
        )
    return tuple(result)


def verify_children(parent, layout, modes, beta, children, *, budget, _admitted=False):
    if not _admitted:
        verify_modes(parent, layout, modes, budget=budget)
    src, m = layout.source, modes.certificate
    if len(children) != 64 or tuple(c.group for c in children) != tuple(range(64)):
        raise ValueError("exactly 64 ordered group children required")
    if (
        beta.modes_digest != modes.content_digest
        or len(beta.values) != len(m["modes"])
        or sum(x * z["weight"] for x, z in zip(beta.values, m["modes"]))
        >= m["precision"]
    ):
        raise ValueError("invalid retained beta")
    i = (abs(m["node"]) & -abs(m["node"])).bit_length() - 1
    # Each item originates in a parent vertex occurrence, preserving port index.
    occurrences, origin = {}, {}
    for v in parent.vertices:
        labels = src["row_labels"] if v.side == "row" else src["column_labels"]
        g = labels.get(str(v.vertex_id), [0] * layout.a)[i]
        origin[v.side, v.vertex_id] = g
        for pos, edge in enumerate(v.ports):
            kind = "Y" if v.side == "row" else "X"
            hits = [
                (pid, slot)
                for pid, p in enumerate(src["packets"])
                for slot, e in p["occupied_slots"]
                if e == edge
            ]
            if len(hits) != 1:
                raise ValueError("packet edge occurrence coverage")
            occurrences[kind, edge] = (g, (kind, edge, *hits[0], v.vertex_id, pos))
    schedule = canonical(schedule_record(parent, layout))
    values, reports = [], []
    total_edges = 0
    for g, child in enumerate(children):
        budget.tick()
        header = (
            child.parent_digest,
            child.layout_digest,
            child.modes_digest,
            child.schedule_bytes,
            child.depth,
            child.node,
            child.zeta,
            child.beta,
            child.precision,
            child.defining_polynomial,
        )
        expected_header = (
            parent.content_digest,
            layout.content_digest,
            modes.content_digest,
            schedule,
            parent.depth + 1,
            m["node"],
            tuple(m["zeta"]),
            beta,
            m["precision"],
            parent.defining_polynomial,
        )
        if header != expected_header:
            raise ValueError(
                "child parent, schedule, point, beta or creation context differs"
            )
        keys = sorted(
            (key for key, (owner, _) in occurrences.items() if owner == g),
            key=lambda x: (x[0] != "Y", x[1]),
        )
        expected_edges = tuple(occurrences[key][1] for key in keys)
        inherited = [v for v in parent.vertices if origin[v.side, v.vertex_id] == g]
        if child.edge_map != expected_edges or child.inherited != tuple(
            (v.side, v.vertex_id) for v in inherited
        ):
            raise ValueError("child half-edge map or inherited ordering differs")
        packets = tuple(
            pid
            for pid, p in enumerate(src["packets"])
            if any(
                (kind, e) in keys for _, e in p["occupied_slots"] for kind in ("Y", "X")
            )
        )
        if child.packet_ids != packets or len(child.vertices) != len(inherited) + len(
            packets
        ):
            raise ValueError("packet vertex inventory differs")
        ar = ReferenceArithmetic(
            m["precision"],
            parent.defining_polynomial,
            1,
            budget.policy.max_work - budget.work,
        )
        factors = []
        for v, old in zip(child.vertices, inherited):
            ports = tuple(
                keys.index(("Y" if old.side == "row" else "X", e)) for e in old.ports
            )
            if v.side != "row" or v.ports != ports or v.tensor != old.tensor:
                raise ValueError("inherited ports or original creation recipe changed")
            factors.append(
                (
                    ports,
                    {
                        bits: _entry(old.tensor, bits, ar)
                        for bits in product((0, 1), repeat=len(ports))
                    },
                )
            )
        for v, pid in zip(child.vertices[len(inherited) :], packets):
            positions, expected_ref = expected_packet_reference(
                src, m, g, pid, beta.values, parent.defining_polynomial
            )
            ports = tuple(keys.index(key) for key in positions)
            if v.side != "column" or v.ports != ports or v.tensor != expected_ref:
                raise ValueError(
                    "packet assignment, bit order, coefficient or creation metadata changed"
                )
            if len(ports) > budget.policy.max_factor_bits:
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT", "independent packet entry cap"
                )
            table = {}
            for bits in product((0, 1), repeat=len(ports)):
                # Coefficient extraction uses the reference polynomial evaluator.
                table[bits] = _entry(expected_ref, bits, ar)
            factors.append((ports, table))
        values.append(eliminate_tables(factors, ar, budget))
        budget.tick(ar.used)
        M = len(keys)
        total_edges += M
        maximum = max((len(v.ports) for v in child.vertices), default=0)
        reports.append(
            {
                "group": g,
                "edges": M,
                "maximum_degree": maximum,
                "source_shrink": 64 * M <= 6 * parent.edge_count,
                "strict_decrease": M < parent.edge_count,
                "degree_preserved": maximum <= max(parent.maximum_degree, 2 * src["L"]),
            }
        )
    if total_edges != 2 * parent.edge_count:
        raise ValueError("half-edge inventory does not cover both endpoints")
    return {
        "values": tuple(values),
        "children": reports,
        "creation_precision_inheritance": True,
        "independent_constructor_semantics": True,
        "child_count": 64,
        "all_source_shrink": all(x["source_shrink"] for x in reports),
    }


def tuple_coefficient(parent, layout, modes, beta, *, budget):
    """A global parent polynomial oracle, with no group-child construction."""
    m = modes.certificate
    ar = ReferenceArithmetic(
        m["precision"],
        parent.defining_polynomial,
        1,
        budget.policy.max_work - budget.work,
    )
    if sum(beta.values) > parent.edge_count:
        # M affine row factors have total formal degree at most M.
        return ar.zero
    if parent.edge_count > 4 or len(beta.values) > 8:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "independent one-tuple oracle cap")
    factors = vertex_tables(parent, ar, budget, half_edges=True)
    targets = [dict(z["rows"]) for z in m["modes"]]
    zero_exponent = (0,) * len(beta.values)
    result = ar.zero
    for bits in product((0, 1), repeat=2 * parent.edge_count):
        budget.tick()
        base = ar.one
        for ports, table in factors:
            base = ar.mul(base, table[tuple(bits[e] for e in ports)])
        poly = {zero_exponent: base}
        for row in range(parent.edge_count):
            local = ar.zero
            for y, x, c in m["local"]:
                if y == row and bits[parent.edge_count + x]:
                    local = ar.add(local, tuple(map(tuple, c)))
            factor = {
                zero_exponent: local if bits[row] else ar.add(ar.one, ar.neg(local))
            }
            for j, coefficients in enumerate(targets):
                if row in coefficients:
                    c = tuple(map(tuple, coefficients[row]))
                    factor[tuple(int(k == j) for k in range(len(beta.values)))] = (
                        c if bits[row] else ar.neg(c)
                    )
            newer = {}
            for left, x in poly.items():
                for right, y in factor.items():
                    exp = tuple(a + b for a, b in zip(left, right))
                    newer[exp] = ar.add(newer.get(exp, ar.zero), ar.mul(x, y))
            if len(newer) > 10000:
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT", "independent formal polynomial cap"
                )
            poly = newer
        term = poly.get(beta.values, ar.zero)
        for exponent, z in zip(beta.values, m["modes"]):
            scalar = sum(c * bits[parent.edge_count + e] for e, c in z["column_terms"])
            term = ar.mul(term, ar.power(ar.scalar(scalar), exponent))
        result = ar.add(result, term)
    budget.tick(ar.used)
    return result
