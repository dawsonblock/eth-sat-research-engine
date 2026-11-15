"""Separator-based exact coefficient extraction (problem B)."""
import importlib.util
import random
from pathlib import Path

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r912.fixture_bridge import compiled_child_packet_at_jet_point
from veritas.research.parent_child_r913.algebraic_resummation import (
    RowFactor,
    _jet_ring_and_arithmetic,
    _packet_row_factors,
    production_packet_value,
)
from veritas.research.parent_child_r913.coefficient_extraction import (
    target_coefficient_by_expansion,
    target_coefficient_by_separator_elimination,
    target_coefficient_by_separator_elimination_int,
    target_coefficient_with_sources,
)
from veritas.research.tapered_v4.source_recipes import Arithmetic, EntryBudget, EntryLimits

ROOT = Path(__file__).resolve().parents[1]


def jet(ring, x):
    return ring.elem([[x % ring.base.modulus]])


@pytest.fixture
def ring_ar():
    ring = JetRing(ExtensionRing(5, 7), 1)
    ar = Arithmetic(ring, EntryBudget(EntryLimits()))
    return ring, ar


def test_separator_matches_expansion_two_mode_counterexample(ring_ar):
    ring, ar = ring_ar
    factors = (
        RowFactor(jet(ring, 1), (jet(ring, 1), jet(ring, 0))),
        RowFactor(jet(ring, 1), (jet(ring, 0), jet(ring, 1))),
    )
    beta = (1, 1)
    extracted = target_coefficient_by_separator_elimination(factors, beta, ar)
    reference = target_coefficient_by_expansion(factors, beta, ar)
    assert extracted.value == reference
    assert int(extracted.value[0][0]) == 1
    assert extracted.stats.join_count == 2


def test_separator_matches_expansion_randomized(ring_ar):
    ring, ar = ring_ar
    rng = random.Random(913913)
    zero = ring.zero
    for _ in range(80):
        modes = rng.randint(1, 5)
        rows = rng.randint(1, 5)
        factors = []
        for _ in range(rows):
            coeffs = tuple(
                jet(ring, rng.randrange(0, 4)) if rng.random() < 0.6 else zero
                for _ in range(modes)
            )
            factors.append(RowFactor(jet(ring, rng.randrange(1, 4)), coeffs))
        beta = tuple(
            rng.randrange(0, min(3, rows + 1)) for _ in range(modes)
        )
        extracted = target_coefficient_by_separator_elimination(
            tuple(factors), beta, ar, budget=EliminationBudget(max_width=10)
        )
        reference = target_coefficient_by_expansion(tuple(factors), beta, ar)
        assert extracted.value == reference


def test_independent_96_rows_without_expansion():
    modulus = 101
    constants = tuple((i + 2) % 7 for i in range(96))
    coefficients = tuple(
        tuple(1 if i == j else 0 for j in range(96)) for i in range(96)
    )
    beta = tuple(1 if i % 2 == 0 else 0 for i in range(96))
    value, stats = target_coefficient_by_separator_elimination_int(
        constants, coefficients, beta, modulus
    )
    expected = 1
    for i in range(96):
        expected = (
            expected * (coefficients[i][i] if beta[i] else constants[i])
        ) % modulus
    assert value == expected
    assert stats.join_count == 96
    assert stats.max_monomial_table == 2
    assert stats.elimination_width == 0


def test_interaction_96_wire_independent_models_match_separator_int():
    """96 noninteracting row factors: separator matches closed form (no 2**96 expansion)."""
    modulus = 1009
    constants = tuple(1 + (i % 5) for i in range(96))
    coefficients = tuple(
        tuple(2 + (i % 3) if i == j else 0 for j in range(96)) for i in range(96)
    )
    target_beta = tuple(1 for _ in range(96))
    value, stats = target_coefficient_by_separator_elimination_int(
        constants, coefficients, target_beta, modulus
    )
    expected = 1
    for i in range(96):
        expected = (expected * coefficients[i][i]) % modulus
    assert value == expected
    assert stats.join_count == 96
    assert stats.max_monomial_table == 2


def test_multislot_child_separator_matches_production():
    from dataclasses import replace
    from pathlib import Path

    from veritas.research.parent_child_r98.model import Budget
    from veritas.research.parent_child_r98.shrinking_cli import load_input
    from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
    from veritas.research.parent_child_r99.cli import load_layout

    root = Path(__file__).resolve().parents[1]
    policy = replace(DEFAULT_SHRINKING_POLICY, max_work=2_000_000, max_seconds=120)
    parent = load_input(root / "examples/r99_multislot_crossing2.json")
    layout = load_layout(
        parent,
        root / "examples/r99_multislot_crossing2_layout.json",
        Budget(policy),
    )
    compiled, _cert = compiled_child_packet_at_jet_point(
        parent, layout, budget=Budget(policy), point_index=0
    )
    bits = (0,) * compiled.reference.arity
    budget = EntryBudget(EntryLimits(max_work=2_000_000))
    _, ar = _jet_ring_and_arithmetic(compiled, budget)
    factors = _packet_row_factors(compiled, bits, ar)
    rows, _c, _l, targets, _s = compiled.data
    target_beta = tuple(beta for beta, _ in targets if beta)
    extracted = target_coefficient_with_sources(
        compiled,
        bits,
        factors,
        target_beta,
        ar,
        budget=EliminationBudget(max_width=12),
    )
    production = production_packet_value(compiled, bits, limits=EntryLimits(max_work=2_000_000))
    assert extracted.value == production
