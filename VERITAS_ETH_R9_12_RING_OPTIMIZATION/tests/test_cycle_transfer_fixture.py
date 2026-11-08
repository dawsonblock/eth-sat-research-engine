"""Independent concrete oracles for finite cycle transfer experiments.

The 44-edge example has genuinely interacting nonconstant tensors. Its oracle
contracts alternating 2x2 matrices using plain Python integer arithmetic, not
the production child constructor, production entry evaluator or transfer code.
"""

from copy import deepcopy
from itertools import product
from math import comb
from types import SimpleNamespace

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.independent import verify_children
from veritas.research.parent_child_r98.model import (
    Budget, ExponentTuple, ModeSet, PacketLayout, ParentCall, canonical,
)
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import (
    audit_vertex_shrinking_layout, construct_vertex_shrinking_layout,
)
from veritas.research.parent_child_r98.shrinking_oracle import parent_point, tuple_coefficient
from veritas.research.tapered_v4.source_recipes import make_reference
from veritas.research.tapered_v4.source_state import SourceVertex


def _reference(table, arity, precision, defining_polynomial=7):
    degree = defining_polynomial.bit_length() - 1
    return make_reference(kind="dense", arity=arity, creation_precision=precision,
                          defining_polynomial=defining_polynomial, jet_length=1,
                          data=[[[value] + [0] * (degree - 1)] for value in table])


def cycle_parent(edges=44, precision=128):
    assert edges >= 4 and edges % 2 == 0
    count = edges // 2
    row = _reference((1, 2, 3, 4), 2, precision)
    column = _reference((1, 2, 3, 5), 2, precision)
    vertices = tuple(SourceVertex("row", i, (2*i, 2*i+1), row)
                     for i in range(count)) + tuple(
        SourceVertex("column", i, (2*i+1, 2*((i+1) % count)), column)
        for i in range(count)
    )
    return ParentCall(1024, 0, precision, 7, edges, vertices)


def _matmul(a, b, modulus):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(2)) % modulus
                       for j in range(2)) for i in range(2))


def scalar_cycle_oracle(edges, point_precision, w):
    """trace((K^T R K C)^(M/2)) with K[y,x]=(1-y)+(2y-1)wx."""
    modulus = 1 << point_precision
    k = ((1, 1-w), (0, w))
    kt = ((k[0][0], k[1][0]), (k[0][1], k[1][1]))
    row = ((1, 2), (3, 4))
    column = ((1, 2), (3, 5))
    factor = _matmul(_matmul(_matmul(kt, row, modulus), k, modulus), column, modulus)
    acc = ((1, 0), (0, 1))
    for _ in range(edges // 2):
        acc = _matmul(acc, factor, modulus)
    return (acc[0][0] + acc[1][1]) % modulus


def extension_cycle_oracle(edges, point_precision, w):
    """Independent 2x2 matrices over Z/2^p[U]/(U^2+U+1)."""
    modulus = 1 << point_precision
    zero, one = (0, 0), (1, 0)

    def add(a, b):
        return ((a[0]+b[0]) % modulus, (a[1]+b[1]) % modulus)

    def mul(a, b):
        # U^2 = -U-1, applied to integer coordinates before reduction.
        return ((a[0]*b[0] - a[1]*b[1]) % modulus,
                (a[0]*b[1] + a[1]*b[0] - a[1]*b[1]) % modulus)

    def mm(a, b):
        return tuple(tuple(add(mul(a[i][0], b[0][j]), mul(a[i][1], b[1][j]))
                           for j in range(2)) for i in range(2))

    k = ((one, ((1-w[0]) % modulus, -w[1] % modulus)), (zero, w))
    kt = ((k[0][0], k[1][0]), (k[0][1], k[1][1]))
    row = (((1, 0), (2, 0)), ((3, 0), (4, 0)))
    column = (((1, 0), (2, 0)), ((3, 0), (5, 0)))
    factor = mm(mm(mm(kt, row), k), column)
    acc = ((one, zero), (zero, one))
    for _ in range(edges // 2):
        acc = mm(acc, factor)
    return add(acc[0][0], acc[1][1])


def point_basis(parent, layout, node=1):
    """Independently form this singleton fixture's complete nonzero basis.

    It intentionally does not enumerate the huge weighted tuple stream. This
    helper is only used to exercise the pre-existing child constructor on eight
    explicitly listed binary tuples; it does not certify production admission.
    """
    source, precision = layout.source, parent.precision + 64 * parent.edge_count
    integer = {-1: -20, 1: -84}[node]
    degree = parent.defining_polynomial.bit_length() - 1
    coefficient = [[integer % (1 << precision)] + [0] * (degree - 1)]
    local, crossing, modes = [], [], []
    for pid, packet in enumerate(source["packets"]):
        slot, edge = packet["occupied_slots"][0]
        row, column = source["edges"][edge]
        target = source["row_labels"][str(row)][0]
        origin = source["column_labels"][str(column)][0]
        if target == origin:
            local.append([edge, edge, coefficient])
        else:
            crossing.append([edge, edge])
            modes.append({"packet": pid, "tile_residue": slot, "exponent": 0,
                          "weight": 1, "source_group": origin, "target_group": target,
                          "rows": [[edge, coefficient]], "column_terms": [[edge, 1]]})
    record = {"d3_certificate": source, "node": node, "precision": precision,
              "jet_length": 1, "extension_degree": degree,
              "irreducible_polynomial": parent.defining_polynomial,
              "zeta": [1] + [0] * (degree - 1), "local": local,
              "cross_pairs": sorted(crossing),
              "modes": modes, "mode_tuple_count": comb(precision+len(modes)-1, len(modes))}
    return ModeSet(layout.content_digest, canonical(record))


def three_crossing_matching(*, extension_degree=2, precision=8):
    """A 22-edge matching with a separately audited three-group mode cycle."""
    M = 22
    f = first_irreducible(extension_degree)
    row = _reference((1, 3), 1, precision, f)
    col = _reference((2, 5), 1, precision, f)
    parent = ParentCall(1024, 0, precision, f, M,
                        tuple(SourceVertex("row", i, (i,), row) for i in range(M)) +
                        tuple(SourceVertex("column", i, (i,), col) for i in range(M)))
    original = construct_vertex_shrinking_layout(parent, groups=64,
                                                   budget=Budget(DEFAULT_SHRINKING_POLICY))
    source = deepcopy(original.source)
    for edge, group in enumerate((1, 2, 0)):
        source["column_labels"][str(edge)] = [group]
    counts, packets = {}, []
    for edge, (r, c) in enumerate(source["edges"]):
        rg, cg = source["row_labels"][str(r)][0], source["column_labels"][str(c)][0]
        pair = (min(rg, cg), max(rg, cg))
        index = counts.get(pair, 0)
        counts[pair] = index + 1
        packets.append({"symbol_pairs": [list(pair)], "index": index,
                        "occupied_slots": [[int(rg > cg), edge]]})
    required = max(n*(2 if a == b else 1) for (a, b), n in counts.items())
    source["H_pad"] = 2*((required + 1)//2)
    source["packets"] = sorted(packets, key=lambda p: (p["symbol_pairs"], p["index"]))
    layout = PacketLayout(parent.content_digest, 1, 1, canonical(source), "balanced_vertices")
    audit = audit_vertex_shrinking_layout(parent, layout)
    assert max(audit["child_edge_counts"]) == 2
    modes = point_basis(parent, layout)
    assert len(modes.certificate["modes"]) == 3
    return parent, layout, modes


@pytest.mark.parametrize("node,w", ((-1, -20), (1, -84)))
def test_connected_cycle_matrix_oracle_agrees_with_independent_half_edge_elimination(node, w):
    parent = cycle_parent()
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    layout = construct_vertex_shrinking_layout(parent, groups=64, budget=budget)
    audit = audit_vertex_shrinking_layout(parent, layout)
    assert max(audit["child_edge_counts"]) == 4
    modes = point_basis(parent, layout, node)
    assert len(modes.certificate["modes"]) == 22
    expected = scalar_cycle_oracle(44, 2944, w)
    assert expected != 0
    assert parent_point(parent, layout, modes, budget=budget) == ((expected, 0),)


def test_exhaustive_three_cross_modes_equal_child_products_and_direct_parent():
    parent, layout, modes = three_crossing_matching()
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    ring = JetRing(ExtensionRing(1416, 7, max_precision_bits=65536), 1)
    total = ring.zero
    for values in product((0, 1), repeat=3):
        beta = ExponentTuple(modes.content_digest, values)
        children = construct_children(parent, layout, modes, beta, budget=budget,
                                      _admitted=True, require_shrink=True)
        assert len(children) == 64 and all(64*c.edge_count <= 6*22 for c in children)
        verified = verify_children(parent, layout, modes, beta, children,
                                   budget=budget, _admitted=True)
        assert len(verified["values"]) == 64
        value = ring.one
        for child, expected in zip(children, verified["values"]):
            budget.call(child.depth)
            actual = leaf(child.as_parent(parent), budget)
            assert actual == expected
            value = ring.mul(value, actual)
        assert value == tuple_coefficient(parent, layout, modes, beta, budget=budget)
        total = ring.add(total, value)
    expected = pow(-833, 22, 1 << 1416)
    assert total == ((expected, 0),)
    assert total == parent_point(parent, layout, modes, budget=budget)


@pytest.mark.parametrize("values", ((2, 0, 0), (0, 3, 1), (1, 0, 5)))
def test_high_exponent_term_has_an_identically_zero_target_child(values):
    """Sample the structural degree bound using two independent evaluators."""
    parent, layout, modes = three_crossing_matching()
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    beta = ExponentTuple(modes.content_digest, values)
    children = construct_children(parent, layout, modes, beta, budget=budget,
                                  _admitted=True, require_shrink=True)
    target = modes.certificate["modes"][next(i for i, n in enumerate(values) if n > 1)]["target_group"]
    child = children[target]
    assert leaf(child.as_parent(parent), budget) == ((0, 0),)
    assert tuple_coefficient(parent, layout, modes, beta, budget=budget) == ((0, 0),)


def test_extension_point_matrix_oracle_matches_direct_half_edge_deformation():
    parent = cycle_parent()
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    layout = construct_vertex_shrinking_layout(parent, groups=64, budget=budget)
    # At t=1 and zeta=U, the exact diagonal Cauchy value is 8+28U.
    oracle = extension_cycle_oracle(44, 2944, (8, 28))
    point = SimpleNamespace(layout_digest=layout.content_digest,
                            certificate={"precision": 2944, "node": 1, "zeta": [0, 1]})
    assert parent_point(parent, layout, point, budget=budget) == (oracle,)


@pytest.mark.parametrize("node,zeta", ((1, (1, 0)), (-1, (1, 0)), (1, (0, 1)), (1, (0, 0))))
def test_certified_transfer_point_matches_independent_cycle_matrix(node, zeta):
    from veritas.research.parent_child_r98.cycle_transfer import evaluate_cycle_transfer
    from veritas.research.parent_child_r98.transfer_verify import verify_transfer_certificate

    parent = cycle_parent()
    layout = construct_vertex_shrinking_layout(parent, groups=64,
                                                budget=Budget(DEFAULT_SHRINKING_POLICY))
    report = evaluate_cycle_transfer(parent, layout, node, zeta)
    assert report["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", report
    expected = (extension_cycle_oracle(44, 2944, (8, 28)) if zeta == (0, 1) else
                (scalar_cycle_oracle(44, 2944, 0 if zeta == (0, 0) else
                                     {-1: -20, 1: -84}[node]), 0))
    assert report["result"] == (expected,)
    nonzero = zeta != (0, 0)
    assert report["retained_modes"] == (22 if nonzero else 0)
    assert report["cycle_groups"] == (22 if nonzero else 0)
    assert report["potentially_nonzero_binary_tuple_count"] == (1 << 22 if nonzero else 1)
    assert report["crossing_pairs"] == 22
    assert report["ledger"]["actual_calls"] == (131 if nonzero else 65)
    assert report["full_hermite_grid"] == "NOT_RUN"
    assert report["parent_contraction_recovered"] is False
    assert report["source_qualified"] is False
    certificate = report["certificate"]
    checked = verify_transfer_certificate(parent, layout, certificate,
                                           expected_point=(node, zeta, 2944))
    assert checked["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", checked
    assert checked["result"] == (expected,)


@pytest.mark.parametrize("name,value", (("max_calls", 130), ("max_precision", 2943),
                                         ("max_work", 1), ("max_certificate_bytes", 128)))
def test_transfer_resource_exhaustion_returns_no_point_value(name, value):
    from dataclasses import replace
    from veritas.research.parent_child_r98.cycle_transfer import evaluate_cycle_transfer
    parent = cycle_parent()
    layout = construct_vertex_shrinking_layout(parent, groups=64,
                                                budget=Budget(DEFAULT_SHRINKING_POLICY))
    policy = replace(DEFAULT_SHRINKING_POLICY, **{name: value})
    report = evaluate_cycle_transfer(parent, layout, 1, (1, 0), policy=policy)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "result" not in report and "certificate" not in report
