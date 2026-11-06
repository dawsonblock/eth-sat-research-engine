"""Explicit high precision for shrinking children, preserving creation residues."""

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.independent_r95.recipe_oracle import (
    ReferenceArithmetic,
    _entry,
)
from veritas.research.tapered_v4.source_recipes import (
    EntryLimits,
    evaluate_source_entry,
    make_reference,
)


def test_high_precision_requires_explicit_arithmetic_opt_in():
    with pytest.raises(ValueError, match="1024"):
        ExtensionRing(1025, 7)
    with pytest.raises(ValueError):
        ExtensionRing(65537, 7, max_precision_bits=65536)
    with pytest.raises(ValueError):
        ExtensionRing(1, 7, max_precision_bits=True)
    ring = ExtensionRing(40000, 7, max_precision_bits=65536)
    # (1+U)^2 = U in the quotient U^2+U+1, at every modulus.
    assert ring.mul(ring.elem((1, 1)), ring.elem((1, 1))) == ring.elem((0, 1))


def test_large_creation_residue_is_lifted_without_reevaluation():
    limits = EntryLimits(max_precision_bits=65536)
    ref = make_reference(
        kind="packet",
        arity=2,
        creation_precision=40000,
        defining_polynomial=7,
        jet_length=1,
        data=[[0], [1], [[[[3, 0]]]], [], []],
        limits=limits,
    )
    # The creation expression 1-3 is canonicalized modulo 2^40000 first.
    value = evaluate_source_entry(ref, (0, 1), precision=45000, limits=limits)["result"]
    assert value == (((1 << 40000) - 2, 0),)
    assert value != (((1 << 45000) - 2, 0),)
    oracle = ReferenceArithmetic(45000, 7, 1, 100000, max_precision_bits=65536)
    assert _entry(ref, (0, 1), oracle) == value
    with pytest.raises(ValueError):
        ReferenceArithmetic(45000, 7, 1, 100000)
    with pytest.raises(ValueError):
        evaluate_source_entry(ref, (0, 1), precision=45000)


def test_shared_constructor_refuses_the_old_growing_children():
    from veritas.research.parent_child_r98 import Budget, ExponentTuple, ParentCall
    from veritas.research.parent_child_r98.constructor import construct_children
    from veritas.research.parent_child_r98.model import Refusal
    from veritas.research.parent_child_r98.modes import build_modes
    from veritas.research.parent_child_r98.packing import construct_layout
    from veritas.research.tapered_v4.source_state import SourceVertex

    ref = make_reference(
        kind="dense",
        arity=1,
        creation_precision=5,
        defining_polynomial=7,
        jet_length=1,
        data=[[[1, 0]], [[1, 0]]],
    )
    parent = ParentCall(
        16,
        0,
        5,
        7,
        1,
        (SourceVertex("row", 0, (0,), ref), SourceVertex("column", 0, (0,), ref)),
    )
    budget = Budget()
    layout = construct_layout(parent, budget=budget)
    modes = build_modes(parent, layout, -1, (0, 0), budget=budget)
    beta = ExponentTuple(modes.content_digest, ())
    with pytest.raises(Refusal, match="constructed child violates"):
        construct_children(
            parent, layout, modes, beta, budget=budget, require_shrink=True
        )
    assert budget.calls == 0
