import random
from itertools import product

import pytest

from research_anthropic.eight_square import crossing_coefficients
from research_anthropic.factors import CrossingFactor
from research_anthropic.network_clique import (
    Clique, Edge, Network, Node, Work, WorkLimitExceeded, clique_direct, cnf_to_network, count_cnf,
    direct_network, find_good_grouping, grouping_is_good, network_to_clique,
    rectangle_network, recursive_clique,
)
from eth_sat.model import CNF


def table(values):
    return lambda index: values[index]


def test_recursive_grid_against_original_and_both_orientations():
    rng = random.Random(2026)
    for _ in range(8):
        tables = tuple(table(tuple(rng.randrange(-2, 3) for _ in range(8))) for _ in range(4))
        clique = Clique(4, 1, tables)
        expected = clique_direct(clique, Work())
        actual = recursive_clique(clique, (2,), Work(), grouping="relaxed")
        assert actual == expected
        for direction in ("row", "column"):
            # The original pair functions directly compute the A_i polynomial.
            modes = []
            for i in range(2):
                work = Work()
                modes.append(direct_network(rectangle_network(clique, (i,), direction, work), work))
            assert sum(modes) == 2 * expected


def test_three_by_three_edges_factor_exactly_in_each_orientation():
    rng = random.Random(890)
    clique = Clique(9, 1, (lambda _: 1,) * 9)
    for direction in ("row", "column"):
        for _ in range(3):
            degrees = tuple(rng.randrange(2) for _ in range(9))
            net = rectangle_network(clique, degrees, direction, Work())
            assert len(net.edges) == 3
            for edge in net.edges:
                for a, b in ((0, 0), (rng.randrange(1 << 24), rng.randrange(1 << 24))):
                    got = sum(edge.left(a, theta) * edge.right(b, theta)
                              for theta in range(1 << edge.bits))
                    assert got == edge.pair(a, b)
                    if a == b == 0:
                        assert got == 1


def test_nine_rectangle_expansion_for_matching_and_mismatched_diagonal():
    clique = Clique(9, 1, (lambda _: 1,) * 9)
    for direction in ("row", "column"):
        for first_setting, expected in ((0, 1), (1 << 3, 0)):
            subtotal = 0
            settings = (first_setting, 0, 0)
            for degrees in product(range(2), repeat=9):
                net = rectangle_network(clique, degrees, direction, Work())
                term = 1
                for edge in net.edges:
                    term *= edge.pair(settings[edge.a], settings[edge.b])
                subtotal += term
            assert subtotal == 2**9 * expected


def test_compressed_crossing_flows_through_lazy_network_and_clique():
    factor = CrossingFactor(6, 0, "row")
    assert factor.bits == 8 and not factor.direct
    x, y, u, v = 0, 1, 2, 3
    edge = Edge(0, 1, factor.bits,
                lambda _, theta: factor.evaluate((x, y), (0, 0), theta)[0],
                lambda _, theta: factor.evaluate((0, 0), (u, v), theta)[1],
                lambda _a, _b: crossing_coefficients(x, y, u, v, 6)[0])
    network = Network((Node(0, lambda _: 2), Node(0, lambda _: -3)), (edge,))
    original = direct_network(network, Work())
    work = Work()
    clique, good = network_to_clique(network, 2, work, labels=(0, 1), require_good=False)
    assert not good
    assert clique.width == 8
    assert clique_direct(clique, work) == original != 0
    assert work.factor_queries > 0


def test_grouping_padding_domains_and_internal_edges():
    equal = Edge(0, 1, 1, lambda a, t: int(a == t), lambda b, t: int(b == t),
                 lambda a, b: int(a == b))
    other = Edge(1, 2, 1, lambda a, t: int(a == t), lambda b, t: int(b == t),
                 lambda a, b: int(a == b))
    net = Network((Node(1, lambda x: 2 + x), Node(1, lambda x: -1 - x),
                   Node(1, lambda x: 3 + x, (0,))), (equal, other))
    expected = direct_network(net, Work())
    for labels in ((0, 0, 1), (0, 1, 2), (0, 0, 0)):
        work = Work()
        clique, _ = network_to_clique(net, 3, work, labels, require_good=False)
        assert clique_direct(clique, work) == expected
    no_edges = Network((Node(0, lambda _: 2), Node(0, lambda _: 3)), ())
    labels = find_good_grouping(no_edges, 2, Work())
    assert grouping_is_good(no_edges, labels, 2)
    work = Work()
    clique, good = network_to_clique(no_edges, 2, work, labels)
    assert good and clique_direct(clique, work) == 6
    with pytest.raises(ValueError, match="originating Work"):
        clique_direct(clique, Work())


def test_resource_limits_and_bad_inputs_fail_closed():
    with pytest.raises(WorkLimitExceeded):
        clique_direct(Clique(2, 40, (lambda _: 1,) * 2), Work(limit=5))
    with pytest.raises(ValueError):
        recursive_clique(Clique(3, 1, (lambda _: 1,) * 3), (2,), Work())
    with pytest.raises(ValueError):
        rectangle_network(Clique(4, 1, (lambda _: 1,) * 4), (9,), "row", Work())
    with pytest.raises(ValueError):
        Network((Node(1, lambda _: 1, (2,)),), ())
    heavy = Network((Node(0, lambda _: 1), Node(0, lambda _: 1)),
                    (Edge(0, 1, 8, lambda a, t: 1, lambda b, t: 1, lambda a, b: 256),))
    with pytest.raises(ValueError, match="does not satisfy"):
        network_to_clique(heavy, 2, Work(), (0, 1), True)


def test_cnf_through_factorized_network_and_clique():
    rng = random.Random(340)
    formulas = [CNF.from_signed_clauses(4, []), CNF.from_signed_clauses(4, [[]]),
                CNF.from_signed_clauses(4, [[1, -1, 1], [-1, 2], [1, -2]])]
    for _ in range(20):
        formulas.append(CNF.from_signed_clauses(4, [
            [rng.choice((-1, 1)) * rng.randrange(1, 5) for _ in range(rng.randrange(4))]
            for _ in range(rng.randrange(5))]))
    for formula in formulas:
        expected = sum(formula.is_satisfied(bits) for bits in product((0, 1), repeat=4))
        network, unused = cnf_to_network(formula, clusters=2)
        assert direct_network(network, Work()) * (1 << unused) == expected
        assert count_cnf(formula, grouping="relaxed") == expected


def test_cnf_runs_through_one_rectangle_recursion():
    formula = CNF.from_signed_clauses(2, [[1], [-1, 2], [2], [-2, 1]])
    expected = sum(formula.is_satisfied(bits) for bits in product((0, 1), repeat=2))
    work = Work(limit=5_000_000)
    assert count_cnf(formula, 4, 4, (2,), grouping="relaxed", work=work) == expected
    assert work.max_depth == 1 and work.modes == 2


def test_dense_10_and_15_edge_factorized_networks():
    rng = random.Random(118)
    for n in (5, 6):
        nodes = tuple(Node(1, table((rng.randrange(-2, 3), rng.randrange(-2, 3))))
                      for _ in range(n))
        edges = []
        for a in range(n):
            for b in range(a + 1, n):
                values = tuple(rng.randrange(-2, 3) for _ in range(4))
                edges.append(Edge(a, b, 1, lambda x, t: int(x == t),
                                  lambda y, t, values=values: values[2*t+y],
                                  lambda x, y, values=values: values[2*x+y]))
        net = Network(nodes, tuple(edges))
        original = direct_network(net, Work())
        work = Work(limit=5_000_000)
        clique, _ = network_to_clique(net, 2, work, tuple(i % 2 for i in range(n)), False)
        assert clique_direct(clique, work) == original


def test_two_level_schedule_stops_at_work_limit():
    work = Work(limit=10_000)
    with pytest.raises(WorkLimitExceeded):
        recursive_clique(Clique(16, 1, (lambda _: 1,) * 16), (4, 2), work, "relaxed")
    assert work.max_depth == 2
