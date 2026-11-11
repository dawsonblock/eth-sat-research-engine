"""Adversarial regressions for coefficient extraction resource and correctness fixes."""
import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r913.algebraic_resummation import (
    RowFactor,
    _jet_ring_and_arithmetic,
    _packet_row_factors,
    build_packet_reference,
    production_packet_value,
)
from veritas.research.parent_child_r913.coefficient_extraction import (
    estimate_extraction_state,
    target_coefficient_by_separator_elimination,
    target_coefficient_with_sources,
)
from veritas.research.parent_child_r913.support_resummation import (
    compare_support_aware_resummation,
)
from veritas.research.parent_child_r98.model import Refusal
from veritas.research.tapered_v4.source_recipes import Arithmetic, EntryBudget, EntryLimits


def jet(ring, x):
    return ring.elem([[x % ring.base.modulus]])


def test_separator_refuses_nonfitting_elimination_plan():
    ring = JetRing(ExtensionRing(5, 7), 1)
    ar = Arithmetic(ring, EntryBudget(EntryLimits()))
    factors = (
        RowFactor(jet(ring, 1), (jet(ring, 1), jet(ring, 2), jet(ring, 3))),
        RowFactor(jet(ring, 1), (jet(ring, 2), jet(ring, 1), jet(ring, 3))),
        RowFactor(jet(ring, 1), (jet(ring, 3), jet(ring, 2), jet(ring, 1))),
    )
    with pytest.raises(Refusal, match="width budget"):
        target_coefficient_by_separator_elimination(
            factors, (1, 1, 1), ar, budget=EliminationBudget(max_width=1)
        )


def test_separator_refuses_oversized_intermediate_table():
    ring = JetRing(ExtensionRing(5, 7), 1)
    ar = Arithmetic(ring, EntryBudget(EntryLimits()))
    factors = (
        RowFactor(jet(ring, 1), (jet(ring, 1), jet(ring, 2))),
        RowFactor(jet(ring, 1), (jet(ring, 2), jet(ring, 1))),
    )
    with pytest.raises(Refusal, match="table budget"):
        target_coefficient_by_separator_elimination(
            factors,
            (1, 1),
            ar,
            budget=EliminationBudget(max_width=20, max_table_entries=2),
        )


def test_exponent_state_estimate_products_per_mode():
    modes = [
        {"packet": 0, "weight": 1, "rows": [[0, None]], "target_group": 0, "source_group": 0},
        {"packet": 0, "weight": 1, "rows": [[1, None]], "target_group": 0, "source_group": 0},
        {"packet": 0, "weight": 1, "rows": [[2, None]], "target_group": 0, "source_group": 0},
    ]
    estimate = estimate_extraction_state(modes, (3, 3, 3))
    assert estimate.exponent_tracking_multiplier == 64


def test_source_only_row_product_identity_times_source_powers():
    ring = JetRing(ExtensionRing(5, 7), 1)
    data = [
        [0],
        [1],
        [[jet(ring, 1)]],
        [],
        [[2, [4]]],
    ]
    _, compiled = build_packet_reference(arity=2, data=data, creation_precision=5, jet_length=1)
    budget = EntryBudget(EntryLimits())
    _, ar = _jet_ring_and_arithmetic(compiled, budget)
    bits = (1, 0)
    extracted = target_coefficient_with_sources(
        compiled,
        bits,
        (),
        (),
        ar,
        budget=EliminationBudget(),
    )
    production = production_packet_value(compiled, bits, limits=EntryLimits(max_work=500_000))
    assert extracted.value == production
    assert extracted.stats.fits_plan


def test_support_enumeration_matches_truncated_dp_at_precision():
    ring = JetRing(ExtensionRing(5, 7), 1)
    data = [
        [0],
        [1, 2],
        [[jet(ring, 2), jet(ring, 1)]],
        [[1, [jet(ring, 5)]]],
        [[2, [1, 2]]],
    ]
    _, compiled = build_packet_reference(arity=3, data=data, creation_precision=5, jet_length=1)
    aware = compare_support_aware_resummation(
        compiled,
        (1, 0, 1),
        (jet(ring, 3),),
        precision=16,
        limits=EntryLimits(max_work=500_000),
    )
    assert aware.enumerated_supported == aware.hybrid_component
    assert aware.enumerate_agrees_with_hybrid


def test_separator_with_nontrivial_source_powers():
    ring = JetRing(ExtensionRing(5, 7), 1)
    data = [
        [0],
        [1, 2],
        [[jet(ring, 2), jet(ring, 1)]],
        [[1, [jet(ring, 5)]]],
        [[2, [1, 2]]],
    ]
    _, compiled = build_packet_reference(arity=3, data=data, creation_precision=5, jet_length=1)
    budget = EntryBudget(EntryLimits())
    _, ar = _jet_ring_and_arithmetic(compiled, budget)
    bits = (1, 0, 1)
    factors = _packet_row_factors(compiled, bits, ar)
    target_beta = tuple(beta for beta, _ in compiled.data[3] if beta)
    assert compiled.data[4][0][0] == 2
    extracted = target_coefficient_with_sources(
        compiled, bits, factors, target_beta, ar, budget=EliminationBudget()
    )
    production = production_packet_value(compiled, bits, limits=EntryLimits(max_work=500_000))
    assert extracted.value == production
