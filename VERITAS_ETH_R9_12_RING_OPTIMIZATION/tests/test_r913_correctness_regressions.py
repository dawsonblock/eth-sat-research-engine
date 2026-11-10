"""Regression tests for R9.13 mathematical correctness (review findings)."""
import random

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r912.elimination import (
    EliminationBudget,
    plan_order,
    verify_order,
)
from veritas.research.parent_child_r913.algebraic_resummation import (
    RowFactor,
    build_packet_reference,
    expand_packet_polynomial,
)
from veritas.research.parent_child_r913.dependency_analyzer import mode_factor_graph_from_modes
from veritas.research.parent_child_r913.support_resummation import (
    compare_support_aware_resummation,
    modes_from_packet_rows,
)
from veritas.research.parent_child_r913.truncated_weighted_resummation import (
    explicit_enumeration_int,
    truncated_weighted_resummation,
    truncated_weighted_resummation_int,
)
from veritas.research.parent_child_r913.algebraic_resummation import (
    _jet_ring_and_arithmetic,
    substitution_resummation,
)
from veritas.research.tapered_v4.source_recipes import EntryBudget, EntryLimits
import pytest


@pytest.fixture
def small_ring():
    return JetRing(ExtensionRing(3, 7), 2)


def jet(ring, scalar):
    return ring.elem([[scalar % ring.base.modulus]])


def test_precision_cutoff_counterexample_independent_components():
    """(1+z1)(1+z2) at precision 2 must yield 3, not 4."""
    constants = (1, 1)
    coefficients = ((1, 0), (0, 1))
    subs = (1, 1)
    weights = (1, 1)
    assert truncated_weighted_resummation_int(constants, coefficients, subs, weights, 2, 32) == 3
    assert explicit_enumeration_int(constants, coefficients, subs, weights, 2, 32) == 3
    assert (1 + 1) * (1 + 1) == 4


def test_truncated_dp_matches_enumeration_randomized():
    rng = random.Random(9137)
    for _ in range(200):
        modes = rng.randint(1, 4)
        rows = rng.randint(1, 4)
        precision = rng.randint(1, 8)
        mode_weights = tuple(rng.randrange(0, 4) for _ in range(modes))
        constants = tuple(rng.randrange(1, 7) for _ in range(rows))
        coefficients = tuple(
            tuple(rng.randrange(0, 5) for _ in range(modes)) for _ in range(rows)
        )
        substitutions = tuple(rng.randrange(1, 7) for _ in range(modes))
        dp = truncated_weighted_resummation_int(
            constants, coefficients, substitutions, mode_weights, precision, 32
        )
        explicit = explicit_enumeration_int(
            constants, coefficients, substitutions, mode_weights, precision, 32
        )
        assert dp == explicit


def test_truncated_dp_jet_ring_matches_supported_enumeration(small_ring):
    ring = small_ring
    data = [
        [0],
        [1],
        [[jet(ring, 2)]],
        [[1, [jet(ring, 3)]], [1, [jet(ring, 4)]]],
        [],
    ]
    _, compiled = build_packet_reference(arity=2, data=data, creation_precision=3, jet_length=2)
    aware = compare_support_aware_resummation(
        compiled,
        (1, 0),
        (jet(ring, 2), jet(ring, 5)),
        precision=3,
        limits=EntryLimits(max_work=2_000_000),
    )
    assert aware.enumerate_agrees_with_hybrid
    assert aware.precision >= 1


def test_constant_only_row_retained_in_truncated_aggregate():
    ring = JetRing(ExtensionRing(5, 7), 1)
    factors = (
        RowFactor(jet(ring, 3), (jet(ring, 0),)),
        RowFactor(jet(ring, 5), (jet(ring, 2),)),
    )
    only_constants = truncated_weighted_resummation(
        (factors[0],), (jet(ring, 2),), (1,), 8, type("AR", (), {"ring": ring, "mul": ring.mul, "add": ring.add})()
    )
    both = truncated_weighted_resummation(
        factors, (jet(ring, 2),), (1,), 8, type("AR", (), {"ring": ring, "mul": ring.mul, "add": ring.add})()
    )
    assert only_constants != both


def test_mode_row_ports_preserve_certificate_ids():
    ring = JetRing(ExtensionRing(3, 7), 1)
    zero = ring.zero
    factors = (
        RowFactor(jet(ring, 1), (jet(ring, 1), jet(ring, 0))),
        RowFactor(jet(ring, 1), (jet(ring, 0), jet(ring, 1))),
    )
    modes = modes_from_packet_rows(factors, (1, 1), zero=zero, row_ports=(10, 20))
    assert [row[0] for row in modes[0]["rows"]] == [10]
    assert [row[0] for row in modes[1]["rows"]] == [20]


def test_absent_modes_omitted_from_elimination_order():
    modes = [
        {"packet": 0, "weight": 1, "rows": [[0, None]], "target_group": 0, "source_group": 0},
        {"packet": 0, "weight": 1, "rows": [], "target_group": 0, "source_group": 0},
    ]
    graph = mode_factor_graph_from_modes(modes)
    assert graph.variables == (0,)
    order = plan_order(graph.scopes, graph.variables)
    assert verify_order(graph.scopes, graph.variables, order, EliminationBudget())["fits"]


def test_empty_factor_product_has_correct_mode_dimension():
    ring = JetRing(ExtensionRing(3, 7), 1)
    budget = EntryBudget(EntryLimits())
    _, compiled = build_packet_reference(
        arity=1,
        data=[[0], [], [[]], [[1, [jet(ring, 1)]]], []],
        creation_precision=3,
        jet_length=1,
    )
    _, ar = _jet_ring_and_arithmetic(compiled, budget)
    poly = expand_packet_polynomial((), ar, mode_count=1)
    assert len(poly) == 1
    assert len(next(iter(poly))) == 1


def test_precision_defaults_to_at_least_one():
    ring = JetRing(ExtensionRing(3, 7), 1)
    data = [[0], [1], [[jet(ring, 1)]], [[1, [jet(ring, 1)]]], []]
    _, compiled = build_packet_reference(arity=2, data=data, creation_precision=3, jet_length=1)
    aware = compare_support_aware_resummation(
        compiled, (0, 0), (jet(ring, 1),), precision=None
    )
    assert aware.precision >= 1
