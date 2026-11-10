"""Three-way distinction: target coefficient vs aggregate vs P(s)."""
import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r913.algebraic_resummation import (
    RowFactor,
    _jet_ring_and_arithmetic,
    substitution_resummation,
    build_packet_reference,
)
from veritas.research.tapered_v4.source_recipes import EntryBudget, EntryLimits
from veritas.research.parent_child_r913.coefficient_extraction import (
    target_coefficient_by_expansion,
)
from veritas.research.parent_child_r913.research_spec import (
    PacketQuantityKind,
    obligations_record,
)
from veritas.research.parent_child_r913.truncated_weighted_resummation import (
    truncated_weighted_resummation,
    truncated_weighted_resummation_int,
)


def jet(ring, x):
    return ring.elem([[x % ring.base.modulus]])


def test_two_problem_distinction_separable_example():
    """(1+z1)(1+z2): coefficient (1,1) != aggregate P=2 != P(s)."""
    c = (1, 1)
    coef = ((1, 0), (0, 1))
    subs = (1, 1)
    w = (1, 1)
    assert truncated_weighted_resummation_int(c, coef, subs, w, 2, 97) == 3
    ring = JetRing(ExtensionRing(8, 19), 1)
    data = [
        [0],
        [1],
        [[jet(ring, 1)]],
        [[1, [jet(ring, 1), jet(ring, 0)]], [1, [jet(ring, 0), jet(ring, 1)]]],
        [],
    ]
    _, compiled = build_packet_reference(
        arity=2, data=data, creation_precision=8, jet_length=1, defining_polynomial=19
    )
    _, ar = _jet_ring_and_arithmetic(compiled, EntryBudget(EntryLimits()))
    factors = (
        RowFactor(jet(ring, 1), (jet(ring, 1), jet(ring, 0))),
        RowFactor(jet(ring, 1), (jet(ring, 0), jet(ring, 1))),
    )
    beta = (1, 1)
    coeff = target_coefficient_by_expansion(factors, beta, ar)
    assert int(coeff[0][0]) == 1
    weights = (jet(ring, 1), jet(ring, 1))
    full = substitution_resummation(factors, weights, ar)
    assert int(full[0][0]) == 4


def test_preservation_spec_flags_aggregate_not_target_proof():
    record = obligations_record()
    kinds = {o["kind"] for o in record["obligations"]}
    assert PacketQuantityKind.TRUNCATED_WEIGHTED_AGGREGATE.value in kinds
    assert PacketQuantityKind.TARGET_COEFFICIENT.value in kinds
    assert not record["source_qualified"]
    assert all(not o["proved_in_this_repo"] for o in record["obligations"])
