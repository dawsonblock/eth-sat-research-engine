"""Tests for R9.13 packet generating-function resummation experiments."""
import random
from itertools import product

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.independent_r95.recipe_oracle import evaluate_reference
from veritas.research.parent_child_r913.algebraic_resummation import (
    build_packet_reference,
    compare_resummation_methods,
    expand_packet_polynomial,
    polynomial_target_value,
    production_packet_value,
    sketch_child_mode_dependencies,
    _jet_ring_and_arithmetic,
    _packet_row_factors,
)
from veritas.research.tapered_v4.source_recipes import EntryBudget, EntryLimits, evaluate_source_entry


def jet(ring, scalar):
    return ring.elem([[scalar % ring.base.modulus]])


@pytest.fixture
def small_ring():
    return JetRing(ExtensionRing(3, 7), 2)


def test_resummation_identity_toy_packet(small_ring):
    """Explicit monomial sum matches substitution on a hand-built packet."""
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
    result = compare_resummation_methods(compiled, bits, weights)
    assert result.agree
    assert result.monomial_count == 2


def test_polynomial_target_matches_production(small_ring):
    ring = small_ring
    data = [
        [0],
        [1, 2],
        [[jet(ring, 2), jet(ring, 1)]],
        [[1, [jet(ring, 5)]]],
        [[2, [1, 2]]],
    ]
    ref, compiled = build_packet_reference(arity=3, data=data, creation_precision=3, jet_length=2)
    for bits in product((0, 1), repeat=3):
        expanded = polynomial_target_value(compiled, bits)
        streamed = production_packet_value(compiled, bits)
        assert expanded == streamed
        entry = evaluate_source_entry(ref, bits, precision=3)["result"]
        assert entry == streamed


def test_resummation_random_packets(small_ring):
    rng = random.Random(913)
    ring = small_ring
    for seed in range(12):
        nr = 1 + seed % 3
        nc = 1 + (seed // 3) % 3
        arity = nr + nc
        mkjet = lambda: jet(ring, rng.randrange(8))
        local = [[mkjet() for _ in range(nc)] for _ in range(nr)]
        targets = [
            [1 + seed % 2, [mkjet() for _ in range(nr)]],
        ]
        if seed % 3:
            targets.append([1, [mkjet() for _ in range(nr)]])
        sources = [[rng.randrange(3), [rng.randrange(8) for _ in range(nc)]]]
        data = [list(range(nr)), list(range(nr, arity)), local, targets, sources]
        _, compiled = build_packet_reference(
            arity=arity,
            data=data,
            creation_precision=3,
            jet_length=2,
            limits=EntryLimits(max_modes=8, max_exponent=8),
        )
        weights = tuple(mkjet() for _ in targets)
        for bits in product((0, 1), repeat=arity):
            assert compare_resummation_methods(
                compiled,
                bits,
                weights,
                limits=EntryLimits(max_work=500_000),
            ).agree
            assert polynomial_target_value(compiled, bits) == production_packet_value(
                compiled, bits
            )


def test_independent_oracle_coefficient_when_dimensions_match(small_ring):
    """Oracle uses every target slot; only compare on single-mode recipes."""
    ring = small_ring
    data = [
        [0],
        [1],
        [[jet(ring, 2)]],
        [[2, [jet(ring, 3)]]],
        [],
    ]
    ref, compiled = build_packet_reference(arity=2, data=data, creation_precision=3, jet_length=2)
    bits = (1, 0)
    expanded = polynomial_target_value(compiled, bits)
    streamed = production_packet_value(compiled, bits)
    oracle = evaluate_reference(ref, bits, precision=3)
    assert expanded == streamed == oracle


def test_overlapping_ports_still_rejected_at_compile():
    with pytest.raises(ValueError):
        build_packet_reference(
            arity=2,
            data=[[0], [0], [[[jet(JetRing(ExtensionRing(3, 7), 1), 1)]]], [], []],
        )


def test_dependency_sketch_stub(small_ring):
    ring = small_ring
    data = [
        [0, 1],
        [2, 3],
        [[jet(ring, 1), jet(ring, 0)], [jet(ring, 2), jet(ring, 3)]],
        [[1, [jet(ring, 4), jet(ring, 5)]]],
        [],
    ]
    _, compiled = build_packet_reference(arity=4, data=data, creation_precision=3, jet_length=2)
    budget = EntryBudget(EntryLimits())
    _, ar = _jet_ring_and_arithmetic(compiled, budget)
    factors = _packet_row_factors(compiled, (1, 0, 1, 0), ar)
    sketch = sketch_child_mode_dependencies(factors, (1,), zero=ring.zero)
    assert sketch["status"] == "STUB_ONLY"
    assert sketch["rows"] == 2
    assert sketch["positive_degree_rows_needed"] == 1


def test_monomial_expansion_matches_single_coefficient(small_ring):
    ring = small_ring
    data = [
        [0],
        [1],
        [[jet(ring, 2)]],
        [[1, [jet(ring, 3)]]],
        [],
    ]
    _, compiled = build_packet_reference(arity=2, data=data, creation_precision=3, jet_length=2)
    budget = EntryBudget(EntryLimits())
    _, ar = _jet_ring_and_arithmetic(compiled, budget)
    bits = (0, 1)
    factors = _packet_row_factors(compiled, bits, ar)
    poly = expand_packet_polynomial(factors, ar)
    assert poly[(1,)] == production_packet_value(compiled, bits)
