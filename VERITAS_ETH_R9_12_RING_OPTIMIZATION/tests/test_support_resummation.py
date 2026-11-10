"""Support-aware resummation experiments on bounded packet fixtures."""
from itertools import product

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r913.algebraic_resummation import (
    build_packet_reference,
    compare_resummation_methods,
)
from veritas.research.parent_child_r913.support_resummation import (
    compare_support_aware_resummation,
    filter_polynomial_by_support,
    modes_from_packet_rows,
    support_condition_report,
)
from veritas.research.parent_child_r913.algebraic_resummation import (
    _jet_ring_and_arithmetic,
    _packet_row_factors,
    expand_packet_polynomial,
)
from veritas.research.parent_child_r99.support_circuit import SupportCircuit
from veritas.research.parent_child_r98.model import Budget
from veritas.research.tapered_v4.source_recipes import EntryBudget, EntryLimits


def jet(ring, scalar):
    return ring.elem([[scalar % ring.base.modulus]])


@pytest.fixture
def small_ring():
    return JetRing(ExtensionRing(3, 7), 2)


def test_full_support_matches_algebraic_resummation(small_ring):
    ring = small_ring
    data = [
        [0],
        [1, 2],
        [[jet(ring, 2), jet(ring, 1)]],
        [[1, [jet(ring, 5)]]],
        [[2, [1, 2]]],
    ]
    _, compiled = build_packet_reference(arity=3, data=data, creation_precision=3, jet_length=2)
    bits = (1, 0, 1)
    weights = (jet(ring, 3),)
    base = compare_resummation_methods(compiled, bits, weights)
    assert base.agree
    # High precision keeps every multilinear monomial in support.
    aware = compare_support_aware_resummation(
        compiled, bits, weights, precision=16, limits=EntryLimits(max_work=500_000)
    )
    assert aware.enumerate_agrees_with_hybrid
    if aware.supported_monomial_count == aware.total_monomial_count:
        assert aware.full_agrees_with_enumerated
    assert aware.enumerated_supported == base.explicit_sum


def test_precision_truncation_identity_when_support_is_full(small_ring):
    """High precision keeps all monomials; substitution identity still holds."""
    ring = small_ring
    data = [
        [0],
        [1],
        [[jet(ring, 2)]],
        [[1, [jet(ring, 3)]], [1, [jet(ring, 4)]]],
        [],
    ]
    _, compiled = build_packet_reference(arity=2, data=data, creation_precision=3, jet_length=2)
    bits = (1, 0)
    weights = (jet(ring, 2), jet(ring, 5))
    for precision in (3, 8, 32):
        aware = compare_support_aware_resummation(
            compiled, bits, weights, precision=precision, limits=EntryLimits(max_work=500_000)
        )
        assert aware.enumerate_agrees_with_hybrid
        if aware.supported_monomial_count == aware.total_monomial_count:
            assert aware.full_agrees_with_enumerated


def test_weight_cutoff_distinguishes_full_and_supported(small_ring):
    ring = small_ring
    data = [
        [0, 1],
        [2, 3],
        [[jet(ring, 1), jet(ring, 0)], [jet(ring, 2), jet(ring, 3)]],
        [[2, [jet(ring, 4), jet(ring, 5)]]],
        [],
    ]
    _, compiled = build_packet_reference(arity=4, data=data, creation_precision=3, jet_length=2)
    bits = (1, 0, 1, 0)
    weights = (jet(ring, 2),)
    aware = compare_support_aware_resummation(compiled, bits, weights, precision=3)
    assert aware.supported_monomial_count <= aware.total_monomial_count
    report = support_condition_report(aware)
    assert report["qualification"] == "experimental_support_filter_only"
    if aware.supported_monomial_count < aware.total_monomial_count:
        assert not aware.full_agrees_with_enumerated or aware.enumerated_supported == aware.full_substitution


def test_modes_from_rows_matches_support_circuit_random():
    modes = [
        {"packet": 0, "weight": 2, "rows": [[0, None]]},
        {"packet": 0, "weight": 2, "rows": [[1, None]]},
        {"packet": 1, "weight": 2, "rows": [[0, None]]},
    ]
    circuit = SupportCircuit(modes, 4, budget=Budget())
    assert circuit.count() == 4
    assert circuit.tuples(limit=16) == [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)]


def test_support_filter_on_expanded_packet(small_ring):
    ring = small_ring
    data = [
        [0],
        [1],
        [[jet(ring, 2)]],
        [[1, [jet(ring, 3)]], [1, [jet(ring, 4)]]],
        [],
    ]
    _, compiled = build_packet_reference(arity=2, data=data, creation_precision=3, jet_length=2)
    budget = EntryBudget(EntryLimits())
    _, ar = _jet_ring_and_arithmetic(compiled, budget)
    factors = _packet_row_factors(compiled, (1, 0), ar)
    poly = expand_packet_polynomial(factors, ar)
    modes = modes_from_packet_rows(factors, (1, 1), zero=ring.zero)
    circuit = SupportCircuit(modes, 3, budget=Budget())
    filtered = filter_polynomial_by_support(poly, circuit)
    assert len(filtered) <= len(poly)
    for bits in product((0, 1), repeat=2):
        aware = compare_support_aware_resummation(compiled, bits, (jet(ring, 2), jet(ring, 5)), precision=3)
        if aware.component_count == len(modes):
            assert aware.enumerate_agrees_with_hybrid
