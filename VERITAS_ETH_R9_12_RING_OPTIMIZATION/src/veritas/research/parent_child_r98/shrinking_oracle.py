"""Independent coefficient elimination and a constant-deformation certificate.

No production child constructor or packet-entry evaluator is imported.  Formal
coefficients are extracted from the original parent half-edge factors.  The
componentwise exponent cutoff computes one coefficient exactly; it never
changes the caller's complete weighted tuple domain.
"""

from itertools import product

from veritas.research.independent_r82.point_mode_oracle import (
    _evaluate_shifted,
    _IndependentExtension,
    _Meter,
    shifted_cauchy_polynomial,
)
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic, _entry

from .model import Refusal


def _arithmetic(parent, precision, budget):
    return ReferenceArithmetic(
        precision,
        parent.defining_polynomial,
        parent.jet_length,
        budget.policy.max_work - budget.work,
        max_precision_bits=budget.policy.max_precision,
    )


def _scope_check(ports, budget):
    if len(ports) > budget.policy.max_factor_bits:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "independent factor width cap")


def eliminate_factors(factors, arithmetic, *, budget):
    """Eliminate each connected Boolean component before multiplying results.

    Factor values may belong to the reference ring or to the truncated sparse
    polynomial semiring below. Components are formed from factor scopes, never
    from the production child partition. Min-scope searches therefore stay
    local on disconnected fixtures instead of scanning the whole graph for
    every eliminated variable.
    """
    factors = list(factors)
    representatives = {}

    def find(x):
        representatives.setdefault(x, x)
        root = x
        while representatives[root] != root:
            root = representatives[root]
        while representatives[x] != x:
            nxt = representatives[x]
            representatives[x] = root
            x = nxt
        return root

    for ports, _ in factors:
        _scope_check(ports, budget)
        if len(set(ports)) != len(ports):
            raise ValueError("duplicate variable in independent factor")
        for edge in ports:
            root, other = find(ports[0]), find(edge)
            representatives[max(root, other)] = min(root, other)
            budget.tick()
    components = {}
    result = arithmetic.one
    for ports, table in factors:
        if ports:
            components.setdefault(find(ports[0]), []).append((ports, table))
        else:
            result = arithmetic.mul(result, table[()])

    for component in sorted(components):
        current = components[component]
        while any(ports for ports, _ in current):
            incident = {}
            for index, (ports, _) in enumerate(current):
                for edge in ports:
                    incident.setdefault(edge, []).append(index)
                    budget.tick()
            scopes = {
                edge: set().union(*(set(current[j][0]) for j in indices))
                for edge, indices in incident.items()
            }
            edge = min(incident, key=lambda e: (len(scopes[e]), e))
            remaining = tuple(sorted(scopes[edge] - {edge}))
            _scope_check(remaining, budget)
            selected = set(incident[edge])
            joined = [factor for j, factor in enumerate(current) if j in selected]
            current = [factor for j, factor in enumerate(current) if j not in selected]
            table = {}
            for bits in product((0, 1), repeat=len(remaining)):
                budget.tick()
                assignment = dict(zip(remaining, bits))
                total = arithmetic.zero
                for bit in (0, 1):
                    assignment[edge] = bit
                    term = arithmetic.one
                    for ports, entries in joined:
                        term = arithmetic.mul(
                            term, entries[tuple(assignment[e] for e in ports)]
                        )
                    total = arithmetic.add(total, term)
                table[bits] = total
            current.append((remaining, table))
        for _, table in current:
            result = arithmetic.mul(result, table[()])
    return result


def _vertex_factors(parent, arithmetic, budget, *, half_edges=False):
    factors = []
    for vertex in parent.vertices:
        ports = tuple(
            edge + (parent.edge_count if half_edges and vertex.side == "column" else 0)
            for edge in vertex.ports
        )
        _scope_check(ports, budget)
        table = {}
        for bits in product((0, 1), repeat=len(ports)):
            budget.tick()
            table[bits] = _entry(vertex.tensor, bits, arithmetic)
        factors.append((ports, table))
    return factors


def contract_independent(parent, budget):
    """Original contraction via independent entry semantics and components."""
    ar = _arithmetic(parent, parent.precision, budget)
    result = eliminate_factors(_vertex_factors(parent, ar, budget), ar, budget=budget)
    budget.tick(ar.used)
    return result


def parent_point(parent, layout, modes, *, budget, max_extension_degree=8):
    """Direct half-edge Cauchy deformation, independent of mode factorization."""
    if (
        layout.parent_digest != parent.content_digest
        or modes.layout_digest != layout.content_digest
    ):
        raise ValueError("independent point ancestry mismatch")
    m, source = modes.certificate, layout.source
    ar = _arithmetic(parent, m["precision"], budget)
    meter = _Meter(
        min(5_000_000, budget.policy.max_work - budget.work),
        min(60, budget.policy.max_seconds),
    )
    scalar = _IndependentExtension(
        m["precision"],
        parent.defining_polynomial,
        meter,
        max_precision_bits=budget.policy.max_precision,
        max_extension_degree=max_extension_degree,
    )
    factors = _vertex_factors(parent, ar, budget, half_edges=True)
    # Slot-pair coefficients repeat across packets; cache by actual slot pair,
    # not by child/group data. Their independent rational derivation is shared.
    coefficients = {}
    for packet in source["packets"]:
        real = packet["occupied_slots"]
        columns = tuple(parent.edge_count + edge for _, edge in real)
        _scope_check((0,) + columns, budget)
        for x, row in real:
            values = []
            for y, _ in real:
                if (x, y) not in coefficients:
                    coefficients[x, y] = (
                        _evaluate_shifted(
                            scalar,
                            shifted_cauchy_polynomial(
                                source["L"],
                                m["node"],
                                2 * source["L"],
                                x,
                                y,
                                meter=meter,
                            ),
                            tuple(m["zeta"]),
                        ),
                    ) + ar.zero[1:]
                values.append(coefficients[x, y])
            table = {}
            for bits in product((0, 1), repeat=1 + len(columns)):
                budget.tick()
                value = ar.zero
                for bit, coefficient in zip(bits[1:], values):
                    if bit:
                        value = ar.add(value, coefficient)
                table[bits] = value if bits[0] else ar.add(ar.one, ar.neg(value))
            factors.append(((row, *columns), table))
    result = eliminate_factors(factors, ar, budget=budget)
    budget.tick(ar.used + meter.used)
    return result


class _CoefficientArithmetic:
    """Reference-ring polynomials modulo (Z_j ** (beta_j + 1)) for every j."""

    def __init__(self, arithmetic, beta, budget, max_terms):
        if type(max_terms) is not int or not 1 <= max_terms <= 100_000:
            raise ValueError("invalid independent polynomial term cap")
        self.ar = arithmetic
        self.beta = beta
        self.budget = budget
        self.max_terms = max_terms
        self.origin = (0,) * len(beta)
        self.zero = {}
        self.one = {self.origin: arithmetic.one}

    def constant(self, value):
        return {} if value == self.ar.zero else {self.origin: value}

    def _insert(self, result, exponent, coefficient):
        value = self.ar.add(result.get(exponent, self.ar.zero), coefficient)
        if value == self.ar.zero:
            result.pop(exponent, None)
        else:
            result[exponent] = value
        if len(result) > self.max_terms:
            raise Refusal(
                "INCONCLUSIVE_RESOURCE_LIMIT", "independent polynomial term cap"
            )

    def add(self, x, y):
        result = dict(x)
        for exponent, coefficient in y.items():
            self.budget.tick()
            self._insert(result, exponent, coefficient)
        return result

    def mul(self, x, y):
        result = {}
        for left, a in x.items():
            for right, b in y.items():
                self.budget.tick(1 + len(self.beta))
                exponent = tuple(u + v for u, v in zip(left, right))
                if all(u <= cap for u, cap in zip(exponent, self.beta)):
                    self._insert(result, exponent, self.ar.mul(a, b))
        return result


def tuple_coefficient(parent, layout, modes, beta, *, budget, max_terms=10_000):
    """Independent coefficient of a complete specified parent deformation term.

    The caller independently validates the mode basis and weighted stream.
    Here ancestry, coefficient index, point ring and weight membership are
    checked again. No child graphs, child tensor recipes or child values enter
    this calculation.
    """
    m = modes.certificate
    if (
        layout.parent_digest != parent.content_digest
        or modes.layout_digest != layout.content_digest
        or beta.modes_digest != modes.content_digest
        or len(beta.values) != len(m["modes"])
        or m["irreducible_polynomial"] != parent.defining_polynomial
        or m["precision"] < parent.precision
        or sum(n * mode["weight"] for n, mode in zip(beta.values, m["modes"]))
        >= m["precision"]
    ):
        raise ValueError("independent coefficient binding or exponent mismatch")
    ar = _arithmetic(parent, m["precision"], budget)
    if sum(beta.values) > parent.edge_count:
        # There are M affine row factors, so their total formal degree is <=M.
        return ar.zero
    poly = _CoefficientArithmetic(ar, beta.values, budget, max_terms)
    factors = []
    for vertex in parent.vertices:
        ports = tuple(
            edge + (parent.edge_count if vertex.side == "column" else 0)
            for edge in vertex.ports
        )
        _scope_check(ports, budget)
        table = {}
        for bits in product((0, 1), repeat=len(ports)):
            budget.tick()
            table[bits] = poly.constant(_entry(vertex.tensor, bits, ar))
        factors.append((ports, table))

    local = [[] for _ in range(parent.edge_count)]
    for row, column, value in m["local"]:
        local[row].append((column, tuple(map(tuple, value))))
    targets = [[] for _ in range(parent.edge_count)]
    for j, mode in enumerate(m["modes"]):
        if beta.values[j]:
            exponent = tuple(int(k == j) for k in range(len(beta.values)))
            for row, value in mode["rows"]:
                targets[row].append((exponent, tuple(map(tuple, value))))

    for row in range(parent.edge_count):
        columns = tuple(sorted({column for column, _ in local[row]}))
        ports = (row,) + tuple(parent.edge_count + column for column in columns)
        _scope_check(ports, budget)
        table = {}
        for bits in product((0, 1), repeat=len(ports)):
            budget.tick()
            assignment = dict(zip(columns, bits[1:]))
            constant = ar.zero
            for column, coefficient in local[row]:
                if assignment[column]:
                    constant = ar.add(constant, coefficient)
            if not bits[0]:
                constant = ar.add(ar.one, ar.neg(constant))
            value = poly.constant(constant)
            for exponent, coefficient in targets[row]:
                poly._insert(
                    value, exponent, coefficient if bits[0] else ar.neg(coefficient)
                )
            table[bits] = value
        factors.append((ports, table))

    for exponent, mode in zip(beta.values, m["modes"]):
        if not exponent:
            # Includes the exponent-zero convention even when the source is 0.
            continue
        columns = tuple(sorted({column for column, _ in mode["column_terms"]}))
        ports = tuple(parent.edge_count + column for column in columns)
        _scope_check(ports, budget)
        table = {}
        for bits in product((0, 1), repeat=len(ports)):
            budget.tick()
            assignment = dict(zip(columns, bits))
            scalar = sum(c * assignment[column] for column, c in mode["column_terms"])
            table[bits] = poly.constant(ar.power(ar.scalar(scalar), exponent))
        factors.append((ports, table))

    result = eliminate_factors(factors, poly, budget=budget).get(beta.values, ar.zero)
    budget.tick(ar.used)
    return result


def certify_constant_deformation(parent, *, budget):
    """Certify degree zero by independently checking every row tensor entry.

    A row tensor constant in all its Y bits factors out of the Y summation.
    For each edge, the two Boolean affine factors sum to one, as an exact
    polynomial identity, so the complete deformation is independent of T.
    Entries are reduced at their creation precision before comparison. The
    certificate binds the parent and reports no contraction result.
    """
    ar = _arithmetic(parent, parent.precision, budget)
    rows = entries = 0
    for vertex in parent.vertices:
        if vertex.side != "row":
            continue
        _scope_check(vertex.ports, budget)
        baseline = None
        for bits in product((0, 1), repeat=len(vertex.ports)):
            budget.tick()
            value = _entry(vertex.tensor, bits, ar)
            if baseline is None:
                baseline = value
            elif value != baseline:
                raise ValueError("row tensor is not constant in its inherited bits")
            entries += 1
        rows += 1
    budget.tick(ar.used)
    return {
        "status": "PASS_CONSTANT_DEFORMATION_DEGREE_BOUND",
        "parent_digest": parent.content_digest,
        "degree_bound": 0,
        "row_tensors_checked": rows,
        "row_entries_checked": entries,
        "creation_precision_inheritance": True,
        "proof_rule": "SUM_Y_OF_BOOLEAN_AFFINE_FACTOR_IS_ONE",
        "source_qualified": False,
    }
