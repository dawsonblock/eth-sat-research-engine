"""General occupied-packet geometric modes, without singleton assumptions.

The inventory is independent of tuple admission. Zero source forms and zero
coefficient vectors may be removed algebraically; no binary exponent cap is
used. This bounded implementation is not the source-sized algorithm.
"""
from collections import defaultdict

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value
from veritas.research.paper_verification.exact_parameters import hermite_parameters
from veritas.research.parent_child_r98.model import ModeSet, Refusal, Semantics, canonical
from veritas.research.parent_child_r98.modes import independent_modes, weighted_count
from veritas.research.parent_child_r98.packing import audit_layout

FIELDS = {"d3_certificate", "node", "precision", "jet_length", "extension_degree",
          "irreducible_polynomial", "zeta", "local", "cross_pairs", "modes", "mode_tuple_count"}


def _admit(parent, layout, node, zeta, budget):
    audit_layout(parent, layout)
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise Refusal("INCONCLUSIVE_SOURCE_REFINEMENT", "bounded packet modes require finite semantics")
    if layout.source["r"] != 64:
        raise ValueError("general packet path requires 64 groups")
    if parent.edge_count > budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general packet reference parent edge cap")
    pars = hermite_parameters(parent.edge_count, layout.a, layout.u, parent.precision,
                              max_wires=budget.policy.max_edges, max_precision=budget.policy.max_precision)
    selected = next((n for n in pars["nodes"] if type(node) is int and n[0] == node), None)
    if selected is None:
        raise ValueError("inactive or invalid Hermite node")
    precision = selected[-1]
    if precision > budget.policy.max_precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "independent packet arithmetic precision cap")
    degree = parent.defining_polynomial.bit_length() - 1
    if not 2 <= degree <= 12:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "independent packet field degree cap")
    if (type(zeta) not in (list, tuple) or len(zeta) != degree or
            any(type(z) is not int or not 0 <= z < 1 << precision for z in zeta)):
        raise ValueError("noncanonical interpolation coordinates")
    return precision, degree, selected[1]


def _count(modes, precision, budget):
    # Bound count storage before the exact generating-function computation.
    bits = len(modes) * precision.bit_length()
    if bits > 65536:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "weighted cardinality bit cap")
    budget.tick(max(1, precision * len(modes)))
    return weighted_count(tuple(m["weight"] for m in modes), precision, 1 << bits)


def iter_packet_components(parent, layout, node, zeta, *, budget, row_certificate=None):
    """Lazy geometric inventory; early cancellation requires independent proof checks."""
    active_rows = None
    if row_certificate is not None:
        from .row_degree import verify_row_degree
        active_rows = set(verify_row_degree(parent, layout.a, row_certificate, budget=budget))
    precision, degree, i = _admit(parent, layout, node, zeta, budget)
    ring = ExtensionRing(precision, parent.defining_polynomial,
                         max_precision_bits=budget.policy.max_precision)
    zeta = tuple(zeta)
    def coefficient(value):
        return [list(value)] + [[0]*degree for _ in range(parent.jet_length-1)]
    source, L = layout.source, 1 << layout.a
    B, alpha = 1 << (i + 1), 2 * L
    values = {}

    def kernel(x, y):
        if (x, y) not in values:
            budget.tick(8 * L * degree**2)
            values[x, y] = cauchy_point_value(L, node, ring, x, y, zeta)
        return values[x, y]

    for pid, packet in enumerate(source["packets"]):
        occupied = packet["occupied_slots"]
        rows = [(x, e, source["row_labels"][str(source["edges"][e][0])][i]) for x, e in occupied]
        cols = [(y, e, source["column_labels"][str(source["edges"][e][1])][i]) for y, e in occupied]
        for x, row, target in rows:
            for y, col, origin in cols:
                budget.tick()
                if target != origin:
                    yield 'cross', [row, col]
                elif kernel(x, y) != ring.zero:
                    yield 'local', [row, col, coefficient(kernel(x, y))]
        tiles = defaultdict(list)
        for y, col, origin in cols:
            tiles[y % B].append((col, y // B, origin))
        for y0, columns in sorted(tiles.items()):
            origins = {origin for _, _, origin in columns}
            if len(origins) != 1:
                raise ValueError("mixed source groups in one tile")
            origin = next(iter(origins))
            for target in sorted({g for _, _, g in rows} - {origin}):
                states = []
                for x, row, g in rows:
                    if g != target or (active_rows is not None and row not in active_rows):
                        continue
                    d = node + x - y0
                    v = (abs(d) & -abs(d)).bit_length() - 1
                    if not d or v > i:
                        raise ValueError("cross-tile denominator valuation")
                    unit = ring.add(ring.elem([d // (1 << v)]),
                                    ring.mul(ring.elem([alpha >> v]), zeta))
                    ratio = ring.mul(ring.elem([B >> v]), ring.inverse(unit))
                    states.append([row, kernel(x, y0), ratio])
                if not states:
                    continue
                for b in range(precision - 1):
                    budget.tick(max(1, len(states) * degree**2))
                    terms = [[col, j**b] for col, j, _ in columns if j**b]
                    if not terms:
                        break  # all j=0 and b>0: every later source form is zero
                    coefficients = [[row, coefficient(value)] for row, value, _ in states if value != ring.zero]
                    if not coefficients:
                        break  # coefficient recurrence multiplies only by integral ratios
                    if any(ring.valuation(value) < b + 1 for _, value, _ in states):
                        raise ValueError("geometric coefficient lacks required divisibility")
                    yield "mode", {"packet": pid, "tile_residue": y0, "exponent": b,
                                  "weight": b + 1, "source_group": origin, "target_group": target,
                                  "rows": coefficients, "column_terms": terms}
                    for state in states:
                        state[1] = ring.mul(state[1], state[2])


def build_packet_modes(parent, layout, node, zeta, *, budget, row_certificate=None):
    """Materialize only the admitted lazy inventory, with incremental byte caps.

    Optional row cancellation changes the basis explicitly. It does not claim
    to enumerate the unreduced weighted stream. Both builders check the premise.
    """
    precision, degree, _ = _admit(parent, layout, node, zeta, budget)
    local, crossing, modes = [], [], []
    source = layout.source
    size = len(layout.source_bytes)
    for kind, item in iter_packet_components(parent, layout, node, zeta, budget=budget, row_certificate=row_certificate):
        size += len(canonical(item))
        if size > min(20_000_000, budget.policy.max_certificate_bytes):
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "incremental packet basis byte cap")
        {"local": local, "cross": crossing, "mode": modes}[kind].append(item)
    record = {"d3_certificate": source, "node": node, "precision": precision,
              "jet_length": parent.jet_length, "extension_degree": degree,
              "irreducible_polynomial": parent.defining_polynomial, "zeta": list(zeta),
              "local": local, "cross_pairs": sorted(crossing), "modes": modes,
              "mode_tuple_count": _count(modes, precision, budget)}
    if row_certificate is not None:
        record["row_cancellation"] = row_certificate
    raw = canonical(record)
    if len(raw) > min(20_000_000, budget.policy.max_certificate_bytes):
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "packet basis byte cap")
    return ModeSet(layout.content_digest, raw)


def verify_packet_modes(parent, layout, modes, *, budget):
    """Rebuild via rational shifted polynomials and separate extension arithmetic."""
    m = modes.certificate
    if set(m) not in (FIELDS, FIELDS | {"row_cancellation"}) or modes.layout_digest != layout.content_digest:
        raise ValueError("mode fields or layout binding")
    precision, degree, _ = _admit(parent, layout, m["node"], m["zeta"], budget)
    if (any(type(m[k]) is not int for k in ("precision", "jet_length", "extension_degree",
                                          "irreducible_polynomial", "mode_tuple_count")) or
        (m["precision"], m["jet_length"], m["extension_degree"], m["irreducible_polynomial"])
            != (precision, parent.jet_length, degree, parent.defining_polynomial) or
        canonical(m["d3_certificate"]) != layout.source_bytes):
        raise ValueError("point arithmetic or source metadata changed")
    active = None
    if "row_cancellation" in m:
        from .row_degree import verify_row_degree
        active = set(verify_row_degree(parent, layout.a, m["row_cancellation"], budget=budget))
    local, cross, expected = independent_modes(layout.source, m["node"], precision,
                                              parent.defining_polynomial, tuple(m["zeta"]), budget=budget,
                                              max_precision_bits=budget.policy.max_precision, max_extension_degree=12, active_rows=active, jet_length=parent.jet_length)
    if canonical((local, cross, expected)) != canonical((m["local"], m["cross_pairs"], m["modes"])):
        raise ValueError("missing, duplicated or altered general mode")
    count = _count(expected, precision, budget)
    if count != m["mode_tuple_count"]:
        raise ValueError("complete weighted count changed")
    return {"mode_completeness": ("INDEPENDENT_ROW_CANCELLED_PACKET_BASIS" if "row_cancellation" in m
                                 else "INDEPENDENT_RATIONAL_GENERAL_PACKET_BASIS"),
            "weighted_tuple_count": count, "tuple_stream_enumerated": False,
            "binary_pruning": False, "source_qualified": False}
