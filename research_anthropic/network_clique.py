"""Bounded, lazy finite reference for Lemma 1 and Algorithm 1.

Tiny configurable schedules are useful for testing identities, but do not
satisfy the paper's quantitative hypotheses merely by returning a count.
"""
from dataclasses import dataclass, field
from itertools import combinations
from math import isqrt

from .eight_square import crossing_coefficients
from .factors import CrossingFactor


class WorkLimitExceeded(RuntimeError):
    pass


@dataclass
class Work:
    limit: int = 2_000_000
    steps: int = 0
    additions: int = 0
    multiplications: int = 0
    table_queries: int = 0
    factor_queries: int = 0
    edge_queries: int = 0
    groupings_tried: int = 0
    modes: int = 0
    base_assignments: int = 0
    max_depth: int = 0

    def tick(self, field=None):
        if self.steps >= self.limit:
            raise WorkLimitExceeded(f"work limit {self.limit} exceeded")
        self.steps += 1
        if field:
            setattr(self, field, getattr(self, field) + 1)

    def add(self, x, y):
        self.tick("additions")
        return x + y

    def mul(self, x, y):
        self.tick("multiplications")
        return x * y


@dataclass(frozen=True)
class Node:
    bits: int
    weight: object
    # None denotes every bit string. Explicit domains support exact sparse
    # networks; constructing a clique grid below always uses full domains.
    domain: tuple | None = None

    def settings(self):
        return range(1 << self.bits) if self.domain is None else self.domain


@dataclass(frozen=True)
class Edge:
    a: int
    b: int
    bits: int
    left: object
    right: object
    pair: object


@dataclass(frozen=True)
class Network:
    nodes: tuple
    edges: tuple
    owner: object = field(default=None, compare=False, repr=False)

    def __post_init__(self):
        seen = set()
        for node in self.nodes:
            if node.bits < 0:
                raise ValueError("negative node bit width")
            if node.domain is not None and (len(set(node.domain)) != len(node.domain) or
                any(not isinstance(x, int) or x < 0 or x >= 1 << node.bits for x in node.domain)):
                raise ValueError("invalid node domain")
        for edge in self.edges:
            if not (0 <= edge.a < edge.b < len(self.nodes)) or edge.bits < 0:
                raise ValueError("invalid edge")
            if (edge.a, edge.b) in seen:
                raise ValueError("duplicate edge")
            seen.add((edge.a, edge.b))


@dataclass(frozen=True)
class Clique:
    n: int
    width: int
    tables: tuple
    owner: object = field(default=None, compare=False, repr=False)

    def __post_init__(self):
        if self.n < 2 or self.width < 1 or len(self.tables) != self.n:
            raise ValueError("invalid clique")


def _read(work, kind, func, *args):
    work.tick(kind)
    result = func(*args)
    if not isinstance(result, int):
        raise TypeError("network tables and factors must return integers")
    return result


def _assignments(domains, work):
    """Enumerate without itertools.product eagerly caching large ranges."""
    values = [0] * len(domains)
    def visit(depth):
        if depth == len(domains):
            yield tuple(values)
            return
        for value in domains[depth]:
            work.tick()
            values[depth] = value
            yield from visit(depth + 1)
    yield from visit(0)


def direct_network(network, work):
    """Reference sum using edge pair functions, independently of factors."""
    if network.owner is not None and network.owner is not work:
        raise ValueError("lazy network must use its originating Work object")
    total = 0
    for settings in _assignments(tuple(node.settings() for node in network.nodes), work):
        work.tick()
        term = 1
        for node, setting in zip(network.nodes, settings):
            term = work.mul(term, _read(work, "table_queries", node.weight, setting))
        for edge in network.edges:
            term = work.mul(term, _read(work, "edge_queries", edge.pair,
                                      settings[edge.a], settings[edge.b]))
        total = work.add(total, term)
    return total


def clique_direct(clique, work):
    if clique.owner is not None and clique.owner is not work:
        raise ValueError("lazy clique must use its originating Work object")
    edges = tuple(combinations(range(clique.n), 2))
    total = 0
    for values in _assignments((range(1 << clique.width),) * len(edges), work):
        work.tick("base_assignments")
        mapping = dict(zip(edges, values))
        term = 1
        for node in range(clique.n):
            setting = sum(mapping[tuple(sorted((node, other)))] << (j * clique.width)
                          for j, other in enumerate(x for x in range(clique.n) if x != node))
            term = work.mul(term, _read(work, "table_queries", clique.tables[node], setting))
        total = work.add(total, term)
    return total


def grouping_is_good(network, labels, k):
    """Exact integer form of Lemma 1 conditions (G1),(G2)."""
    g = len(network.nodes)
    if k < 2 or len(labels) != g or any(not isinstance(x, int) or not 0 <= x < k for x in labels):
        raise ValueError("invalid grouping")
    incident = [0] * g
    for edge in network.edges:
        incident[edge.a] += edge.bits
        incident[edge.b] += edge.bits
    p = max([1, *(n.bits for n in network.nodes), *incident])
    u = 2 * sum(edge.bits for edge in network.edges)
    if any(labels.count(group) * k > 2 * g for group in range(k)):
        return False
    return all(sum(e.bits for e in network.edges if {labels[e.a], labels[e.b]} == {a, b}) * k**3
               <= u * k + g * p for a, b in combinations(range(k), 2))


def find_good_grouping(network, k, work):
    for labels in _assignments((range(k),) * len(network.nodes), work):
        work.tick("groupings_tried")
        if grouping_is_good(network, labels, k):
            return labels
    raise ValueError("no grouping satisfies Lemma 1 conditions for this finite input")


def network_to_clique(network, k, work, labels=None, require_good=True):
    """Equation (26), with bit padding and lazily evaluated clique tables."""
    if network.owner is not None and network.owner is not work:
        raise ValueError("lazy network must use its originating Work object")
    g = len(network.nodes)
    if k < 2:
        raise ValueError("k must be at least 2")
    if labels is None:
        labels = find_good_grouping(network, k, work)
    labels = tuple(labels)
    good = grouping_is_good(network, labels, k)
    if require_good and not good:
        raise ValueError("grouping does not satisfy Lemma 1 conditions")
    groups = tuple(tuple(i for i, x in enumerate(labels) if x == c) for c in range(k))
    between = {}
    for a, b in combinations(range(k), 2):
        between[a, b] = tuple(e for e in network.edges if {labels[e.a], labels[e.b]} == {a, b})
    width = max([1, *(sum(e.bits for e in edges) for edges in between.values())])
    if require_good:
        incident = [0] * g
        for edge in network.edges:
            incident[edge.a] += edge.bits
            incident[edge.b] += edge.bits
        p = max([1, *(node.bits for node in network.nodes), *incident])
        u = 2 * sum(edge.bits for edge in network.edges)
        width = max(1, (u * k + g * p) // k**3)

    def make_table(group):
        own = groups[group]
        internal = tuple(e for e in network.edges if labels[e.a] == labels[e.b] == group)
        neighbors = tuple(x for x in range(k) if x != group)
        def table(setting):
            indices = {}
            for j, other in enumerate(neighbors):
                packed = (setting >> (j * width)) & ((1 << width) - 1)
                offset = 0
                for edge in between[min(group, other), max(group, other)]:
                    indices[edge.a, edge.b] = (packed >> offset) & ((1 << edge.bits) - 1)
                    offset += edge.bits
                if packed >> offset:
                    return 0
            total = 0
            for values in _assignments(tuple(network.nodes[i].settings() for i in own), work):
                work.tick()
                states = dict(zip(own, values))
                term = 1
                for i in own:
                    term = work.mul(term, _read(work, "table_queries", network.nodes[i].weight, states[i]))
                for edge in internal:
                    term = work.mul(term, _read(work, "edge_queries", edge.pair, states[edge.a], states[edge.b]))
                for edge in network.edges:
                    if labels[edge.a] == group and labels[edge.b] != group:
                        term = work.mul(term, _read(work, "factor_queries", edge.left, states[edge.a], indices[edge.a, edge.b]))
                    elif labels[edge.b] == group and labels[edge.a] != group:
                        term = work.mul(term, _read(work, "factor_queries", edge.right, states[edge.b], indices[edge.a, edge.b]))
                total = work.add(total, term)
            return total
        return table

    return Clique(k, width, tuple(make_table(i) for i in range(k)), work), good


def rectangle_network(clique, degrees, direction, work):
    """One row or column network of Proposition 3 for an arbitrary square grid."""
    if clique.owner is not None and clique.owner is not work:
        raise ValueError("lazy clique must use its originating Work object")
    g = isqrt(clique.n)
    if g * g != clique.n or direction not in ("row", "column"):
        raise ValueError("clique must be a square grid and direction row or column")
    rectangles = tuple((a, b, c, d) for a, b in combinations(range(g), 2)
                       for c, d in combinations(range(g), 2))
    t = (clique.width + 2) // 3
    if len(degrees) != len(rectangles) or any(not 0 <= i <= t for i in degrees):
        raise ValueError("invalid rectangle degree selection")
    w, n = clique.width, clique.n
    node_bits = (n - 1) * w
    mask = (1 << w) - 1
    def vertex(a, b):
        return a * g + b if direction == "row" else b * g + a
    def local(setting, pos):
        return (setting >> (pos * node_bits)) & ((1 << node_bits) - 1)
    def edge_value(z, v, other):
        j = other if other < v else other - 1
        return (z >> (j * w)) & mask
    def make_weight(group):
        def weight(setting):
            result = 1
            for pos in range(g):
                v = vertex(group, pos)
                result = work.mul(result, _read(work, "table_queries", clique.tables[v], local(setting, pos)))
            for p, q in combinations(range(g), 2):
                a, b = vertex(group, p), vertex(group, q)
                result = work.mul(result, int(edge_value(local(setting, p), a, b) == edge_value(local(setting, q), b, a)))
            return result
        return weight
    nodes = tuple(Node(g * node_bits, make_weight(a)) for a in range(g))
    edges = []
    for a, b in combinations(range(g), 2):
        relevant = []
        for rect, degree in zip(rectangles, degrees):
            ra, rb, ca, cb = rect
            group_pair = (ra, rb) if direction == "row" else (ca, cb)
            if group_pair == (a, b):
                relevant.append((rect, CrossingFactor(w, degree, direction)))
        bits = g * w + sum(f.bits for _, f in relevant)
        def boundary(setting, group, rect, side):
            ra, rb, ca, cb = rect
            v0, v1, v2, v3 = ra*g+ca, ra*g+cb, rb*g+ca, rb*g+cb
            if direction == "row":
                specs = ((ca, v0, v3), (cb, v1, v2)) if side == 0 else ((ca, v2, v1), (cb, v3, v0))
            else:
                specs = ((ra, v0, v3), (rb, v2, v1)) if side == 0 else ((ra, v1, v2), (rb, v3, v0))
            return tuple(edge_value(local(setting, pos), v, other) for pos, v, other in specs)
        def make_factor(group, side, relevant, a, b):
            def factor(setting, theta):
                result = 1
                for pos in range(g):
                    v, other = vertex(group, pos), vertex(b if side == 0 else a, pos)
                    chosen = (theta >> (pos*w)) & mask
                    result = work.mul(result, int(edge_value(local(setting, pos), v, other) == chosen))
                offset = g*w
                for rect, fac in relevant:
                    index = (theta >> offset) & ((1 << fac.bits) - 1)
                    bd = boundary(setting, group, rect, side)
                    pair = fac.evaluate(bd if side == 0 else (0, 0), bd if side == 1 else (0, 0), index)
                    result = work.mul(result, pair[side])
                    offset += fac.bits
                return result
            return factor
        def make_pair(a, b, relevant):
            def pair(left, right):
                result = 1
                for pos in range(g):
                    va, vb = vertex(a, pos), vertex(b, pos)
                    result = work.mul(result, int(edge_value(local(left, pos), va, vb) == edge_value(local(right, pos), vb, va)))
                for rect, fac in relevant:
                    first, second = boundary(left, a, rect, 0), boundary(right, b, rect, 1)
                    if direction == "row":
                        x, y = first
                        u, v = second
                    else:
                        x, u = first
                        y, v = second
                    result = work.mul(result, crossing_coefficients(x, y, u, v, w)[fac.degree])
                return result
            return pair
        edges.append(Edge(a, b, bits, make_factor(a, 0, tuple(relevant), a, b),
                          make_factor(b, 1, tuple(relevant), a, b), make_pair(a, b, tuple(relevant))))
    return Network(nodes, tuple(edges), work)


def recursive_clique(clique, levels, work, grouping="good", depth=0):
    """Algorithm 1 shape with an explicit finite schedule of next clique sizes.

    A relaxed grouping is only a finite identity experiment. It provides no
    implication about the theorem's good partition or asymptotic recurrence.
    """
    work.max_depth = max(work.max_depth, depth)
    if not levels:
        return clique_direct(clique, work)
    g = isqrt(clique.n)
    if g * g != clique.n:
        raise ValueError("non-base clique must have square node count")
    if grouping not in ("good", "relaxed"):
        raise ValueError("grouping must be good or relaxed")
    k = levels[0]
    if k < 2 or k > g:
        raise ValueError("next clique size must be between 2 and grid side")
    r = len(tuple(combinations(range(g), 2))) ** 2
    t = (clique.width + 2) // 3
    total = 0
    for degrees in _assignments((range(t + 1),) * r, work):
        work.tick("modes")
        row = rectangle_network(clique, degrees, "row", work)
        col = rectangle_network(clique, degrees, "column", work)
        selected = row if sum(e.bits for e in row.edges) <= sum(e.bits for e in col.edges) else col
        labels = None if grouping == "good" else tuple(i % k for i in range(g))
        child, _ = network_to_clique(selected, k, work, labels, grouping == "good")
        total = work.add(total, recursive_clique(child, levels[1:], work, grouping, depth + 1))
    denominator = 1 << (t * r)
    quotient, remainder = divmod(total, denominator)
    if remainder:
        raise ArithmeticError("rectangle reconstruction is not exactly divisible")
    return quotient


def cnf_to_network(formula, clusters=2):
    """Occurrence-chain encoding of a CNF, with round-robin clause clusters.

    Returns (network, unused variables). Duplicate literals and empty clauses
    are retained, and all equality chains include every occurrence.
    """
    from eth_sat.model import CNF
    if not isinstance(formula, CNF) or clusters < 2:
        raise ValueError("expected CNF and at least two clusters")
    counts = [0] * clusters
    local_clauses = [[] for _ in range(clusters)]
    occurrences = {}
    for ci, clause in enumerate(formula.clauses):
        group = ci % clusters
        encoded = []
        for literal in clause:
            pos = counts[group]
            counts[group] += 1
            encoded.append((pos, not literal.negated))
            occurrences.setdefault(literal.variable, []).append((group, pos))
        local_clauses[group].append(tuple(encoded))
    internal = [[] for _ in range(clusters)]
    external = {}
    for chain in occurrences.values():
        for (a, pa), (b, pb) in zip(chain, chain[1:]):
            if a == b:
                internal[a].append((pa, pb))
            else:
                if a > b:
                    a, b, pa, pb = b, a, pb, pa
                external.setdefault((a, b), []).append((pa, pb))
    def make_weight(clauses, equalities):
        def weight(z):
            return int(all(any(bool((z >> pos) & 1) == positive for pos, positive in clause)
                           for clause in clauses)
                       and all(((z >> a) & 1) == ((z >> b) & 1) for a, b in equalities))
        return weight
    nodes = tuple(Node(counts[i], make_weight(tuple(local_clauses[i]), tuple(internal[i])))
                  for i in range(clusters))
    edges = []
    for (a, b), positions in sorted(external.items()):
        positions = tuple(positions)
        def packed(z, side, positions=positions):
            return sum(((z >> pair[side]) & 1) << j for j, pair in enumerate(positions))
        def left(z, theta, packed=packed):
            return int(packed(z, 0) == theta)
        def right(z, theta, packed=packed):
            return int(packed(z, 1) == theta)
        def pair(x, y, packed=packed):
            return int(packed(x, 0) == packed(y, 1))
        edges.append(Edge(a, b, len(positions), left, right, pair))
    return Network(nodes, tuple(edges)), formula.num_variables - len(occurrences)


def count_cnf(formula, clusters=2, clique_nodes=2, levels=(), *, grouping="good", work=None):
    """Bounded experimental exact count; no sparsification or solver proof."""
    if grouping not in ("good", "relaxed"):
        raise ValueError("grouping must be good or relaxed")
    if clique_nodes > clusters or clique_nodes < 2:
        raise ValueError("clique_nodes must be between 2 and clusters")
    if work is None:
        work = Work()
    network, unused = cnf_to_network(formula, clusters)
    labels = None if grouping == "good" else tuple(i % clique_nodes for i in range(clusters))
    clique, _ = network_to_clique(network, clique_nodes, work, labels, grouping == "good")
    return work.mul(recursive_clique(clique, tuple(levels), work, grouping), 1 << unused)
