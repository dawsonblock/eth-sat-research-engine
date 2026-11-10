"""Complete weighted streams and independent geometric point-mode enumeration."""

from collections import defaultdict

from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.independent_r82.point_mode_oracle import (
    _evaluate_shifted,
    _IndependentExtension,
    _Meter,
    meter_from_budget,
    shifted_cauchy_polynomial,
    verify_point_mode_action,
)
from veritas.research.paper_verification.exact_parameters import hermite_parameters

from .model import ExponentTuple, ModeSet, Refusal, canonical
from .packing import audit_layout


MODE_BASIS_SCOPE = "ZERO_REDUCED_GEOMETRIC_POINT_MODES"
TUPLE_DOMAIN = "ALL_WEIGHTED_TUPLES_OVER_RETAINED_MODES"


def weighted_count(weights, precision, cap):
    """Independent generating-function coefficient count, not a stream replay."""
    if any(type(w) is not int or w < 1 for w in weights):
        raise ValueError("mode weights must be positive integers")
    counts = [1] + [0] * (precision - 1)
    for w in weights:
        for n in range(w, precision):
            counts[n] = min(cap + 1, counts[n] + counts[n - w])
    total = sum(counts)
    if total > cap:
        raise Refusal(
            "INCONCLUSIVE_RESOURCE_LIMIT",
            "complete weighted tuple count exceeds policy",
        )
    return total


def weighted_tuples(modes, *, budget):
    m = modes.certificate
    if type(m["node"]) is not int or type(m["precision"]) is not int:
        raise ValueError("integer node and precision required")
    weights = tuple(x["weight"] for x in m["modes"])
    expected = weighted_count(weights, m["precision"], budget.policy.max_tuples)
    if expected != m["mode_tuple_count"]:
        raise ValueError("weighted count differs from mode metadata")

    def visit(i, remaining, prefix):
        budget.tick()
        if i == len(weights):
            yield ExponentTuple(modes.content_digest, prefix)
        else:
            for n in range((remaining - 1) // weights[i] + 1):
                yield from visit(i + 1, remaining - n * weights[i], prefix + (n,))

    yield from visit(0, m["precision"], ())


class TupleChecker:
    """Strict order + legality + independent finite cardinality imply coverage."""

    def __init__(self, modes, budget):
        m = modes.certificate
        self.modes = modes
        self.weights = tuple(x["weight"] for x in m["modes"])
        self.precision = m["precision"]
        self.expected = weighted_count(
            self.weights, self.precision, budget.policy.max_tuples
        )
        self.previous = None
        self.seen = 0
        self.budget = budget

    def accept(self, beta):
        self.budget.tick()
        if (
            type(beta) is not ExponentTuple
            or beta.modes_digest != self.modes.content_digest
            or len(beta.values) != len(self.weights)
            or sum(x * w for x, w in zip(beta.values, self.weights)) >= self.precision
            or (self.previous is not None and beta.values <= self.previous)
        ):
            raise ValueError("illegal, duplicated or unordered weighted tuple")
        self.previous = beta.values
        self.seen += 1
        if self.seen > self.expected:
            raise ValueError("excess tuple")

    def finish(self):
        if self.seen != self.expected:
            raise ValueError("incomplete weighted tuple stream")


def independent_modes(src, node, precision, f, zeta, *, budget,
                      max_precision_bits=1024, max_extension_degree=8, active_rows=None, jet_length=1):
    """Generate the actual basis using rational polynomials and separate ring code."""
    meter = meter_from_budget(budget, 'independent_modes')
    ar = _IndependentExtension(precision, f, meter, max_precision_bits=max_precision_bits,
                               max_extension_degree=max_extension_degree)
    L = src["L"]
    i = (abs(node) & -abs(node)).bit_length() - 1
    B, alpha = 2 ** (i + 1), 2 * L
    local, cross, output = [], [], []
    kernels = {}
    def coefficient_jet(value):
        return [list(value)] + [[0]*ar.e for _ in range(jet_length-1)]
    for pid, packet in enumerate(src["packets"]):
        real = packet["occupied_slots"]
        rows = [(x, e, src["row_labels"][str(src["edges"][e][0])][i]) for x, e in real]
        cols = [
            (y, e, src["column_labels"][str(src["edges"][e][1])][i]) for y, e in real
        ]

        def W(x, y):
            key=(x,y)
            if key not in kernels:
                kernels[key]=_evaluate_shifted(
                    ar, shifted_cauchy_polynomial(L,node,alpha,x,y,meter=meter),zeta)
            return kernels[key]

        for x, row, target in rows:
            for y, col, origin in cols:
                if target != origin:
                    cross.append([row, col])
                else:
                    value = W(x, y)
                    if value != ar.zero:
                        local.append([row, col, coefficient_jet(value)])
        tiles = defaultdict(list)
        for y, col, origin in cols:
            tiles[y % B].append((col, (y - y % B) // B, origin))
        for y0, columns in sorted(tiles.items()):
            origins = {v[2] for v in columns}
            if len(origins) != 1:
                raise ValueError("mixed source groups in tile")
            origin = next(iter(origins))
            for target in sorted({v[2] for v in rows} - {origin}):
                selected = [(x, row) for x, row, group in rows if group == target
                            and (active_rows is None or row in active_rows)]
                if not selected:
                    continue
                for b in range(precision - 1):
                    terms = [[col, j**b] for col, j, _ in columns if j**b]
                    if not terms:
                        if b:
                            break
                        continue
                    coefficients = []
                    for x, row in selected:
                        d = node + x - y0
                        if not d:
                            raise ValueError("zero geometric denominator")
                        v = (abs(d) & -abs(d)).bit_length() - 1
                        if v > i:
                            raise ValueError("geometric denominator valuation")
                        unit = ar.add(
                            ar.scalar(d // 2**v), ar.mul(ar.scalar(alpha // 2**v), zeta)
                        )
                        coefficient = ar.mul(
                            W(x, y0),
                            ar.pow(ar.mul(ar.scalar(B // 2**v), ar.inverse(unit)), b),
                        )
                        if ar.valuation(coefficient) < b + 1:
                            raise ValueError("mode divisibility fails")
                        if coefficient != ar.zero:
                            coefficients.append([row, coefficient_jet(coefficient)])
                    if coefficients:
                        output.append(
                            {
                                "packet": pid,
                                "tile_residue": y0,
                                "exponent": b,
                                "weight": b + 1,
                                "source_group": origin,
                                "target_group": target,
                                "rows": coefficients,
                                "column_terms": terms,
                            }
                        )
    budget.tick(meter.used)
    return local, sorted(cross), output


def verify_modes(parent, layout, modes, *, budget):
    audit_layout(parent, layout)
    if modes.layout_digest != layout.content_digest:
        raise ValueError("mode layout binding")
    m = modes.certificate
    if any(
        type(m[name]) is not int
        for name in (
            "node",
            "precision",
            "extension_degree",
            "irreducible_polynomial",
            "jet_length",
            "mode_tuple_count",
        )
    ):
        raise ValueError("point arithmetic metadata requires integers")
    if (
        canonical(m["d3_certificate"]) != layout.source_bytes
        or m["irreducible_polynomial"] != parent.defining_polynomial
    ):
        raise ValueError("mode source/ring mismatch")
    plan = hermite_parameters(
        parent.edge_count,
        layout.a,
        layout.u,
        parent.precision,
        max_wires=budget.policy.max_edges,
        max_precision=budget.policy.max_precision,
    )
    n = next((n for n in plan["nodes"] if n[0] == m["node"]), None)
    if n is None or m["precision"] != n[-1] or m["jet_length"] != 1:
        raise ValueError("node or source-prescribed precision mismatch")
    if m["precision"] > budget.policy.max_precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "point precision cap")
    e = parent.defining_polynomial.bit_length() - 1
    if (
        m["extension_degree"] != e
        or len(m["zeta"]) != e
        or any(
            type(z) is not int or not 0 <= z < 2 ** m["precision"] for z in m["zeta"]
        )
    ):
        raise ValueError("noncanonical point coordinates")
    local, cross, actual = independent_modes(
        layout.source,
        m["node"],
        m["precision"],
        parent.defining_polynomial,
        tuple(m["zeta"]),
        budget=budget,
    )
    if canonical((m["local"], m["cross_pairs"], m["modes"])) != canonical(
        (local, cross, actual)
    ):
        raise ValueError("incomplete, altered or noncanonical geometric modes")
    action = verify_point_mode_action(
        layout.source, m, max_work=5_000_000, timeout_s=60
    )
    if action.get("valid") is not True:
        raise Refusal(
            action.get("status", "INVALID_MODE_ACTION"),
            action.get("reason", "independent Cauchy action mismatch"),
        )
    budget.tick(action["work_units"])
    count = weighted_count(
        tuple(x["weight"] for x in actual), m["precision"], budget.policy.max_tuples
    )
    if count != m["mode_tuple_count"]:
        raise ValueError("weighted tuple count metadata")
    return {
        "mode_completeness": "INDEPENDENT_BASIS_EQUALITY",
        "mode_basis_scope": MODE_BASIS_SCOPE,
        "tuple_domain": TUPLE_DOMAIN,
        "paper_formal_mode_domain_enumerated": False,
        "zero_mode_elision": "ZERO_SOURCE_FORM_OR_ALL_ZERO_TARGET_COEFFICIENTS",
        "weighted_tuple_count": count,
        "omitted_high_weight_terms": "DIVISIBLE_BY_2_TO_POINT_PRECISION",
        "universal_mode_theorem_proved": False,
    }


def build_modes(parent, layout, node, zeta, *, budget):
    pars = hermite_parameters(
        parent.edge_count,
        layout.a,
        layout.u,
        parent.precision,
        max_wires=budget.policy.max_edges,
        max_precision=budget.policy.max_precision,
    )
    n = next((x for x in pars["nodes"] if x[0] == node), None)
    if n is None:
        raise ValueError("invalid Hermite node")
    if n[-1] > budget.policy.max_precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "point precision cap")
    src = layout.source
    if layout.strategy == "canonical":
        cert = make_point_modes(
            src,
            node=node,
            precision=n[-1],
            extension_degree=parent.defining_polynomial.bit_length() - 1,
            defining_polynomial=parent.defining_polynomial,
            zeta=zeta,
            max_tuples=budget.policy.max_tuples,
            max_parent_wires=8,
        )
    else:
        # Experimental singleton layouts have only local entries; production
        # Cauchy evaluation remains separate from the independent polynomial oracle.
        from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
        from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value

        ar = ExtensionRing(n[-1], parent.defining_polynomial)
        local = []
        for packet in src["packets"]:
            for x, row in packet["occupied_slots"]:
                for y, col in packet["occupied_slots"]:
                    c = cauchy_point_value(src["L"], node, ar, x, y, zeta)
                    if c != ar.zero:
                        local.append([row, col, [list(c)]])
        cert = {
            "d3_certificate": src,
            "node": node,
            "precision": n[-1],
            "jet_length": 1,
            "extension_degree": ar.e,
            "irreducible_polynomial": ar.f,
            "zeta": list(zeta),
            "local": local,
            "cross_pairs": [],
            "modes": [],
            "mode_tuple_count": 1,
        }
    result = ModeSet(layout.content_digest, canonical(cert))
    verify_modes(parent, layout, result, budget=budget)
    return result
