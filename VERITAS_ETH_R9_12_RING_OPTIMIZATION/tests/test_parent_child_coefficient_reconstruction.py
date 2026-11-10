"""Parent coefficient equals product of contracted children (one active level)."""
from dataclasses import replace

import pytest

from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import contract_scaled, leaf
from veritas.research.parent_child_r98.independent import verify_children
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, Policy
from veritas.research.parent_child_r98.modes import build_modes
from veritas.research.parent_child_r98.packing import construct_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r913.coefficient_reconstruction import (
    reconstruct_parent_coefficient_one_level,
    reconstruct_with_leaf_child_contractor,
    reconstruction_report,
)
from tests.test_cycle_transfer_fixture import three_crossing_matching
from tests.test_r98_parent_child import parent as tensor_parent


def test_two_wire_parent_one_tuple_product_matches_oracle():
    p = tensor_parent(2)
    budget = Budget()
    layout = construct_layout(p, budget=budget)
    modes = build_modes(p, layout, -1, (1, 0, 0, 0), budget=budget)
    beta = ExponentTuple(modes.content_digest, (1,))
    result = reconstruct_parent_coefficient_one_level(
        p, layout, modes, beta, budget=budget
    )
    assert result.reconstruction_equals_oracle
    report = reconstruction_report(result)
    assert report["parent_child_reconstruction_proved"]
    assert report["active_levels"] == 1


def test_three_crossing_zero_beta_reconstruction_with_leaf_contractor():
    parent, layout, modes = three_crossing_matching()
    policy = replace(Policy(), max_work=5_000_000, max_precision=65536)
    budget = Budget(policy)
    beta = ExponentTuple(modes.content_digest, (0, 0, 0))
    result = reconstruct_with_leaf_child_contractor(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        require_shrink=True,
    )
    assert result.reconstruction_equals_oracle
    assert result.child_group_count == 64


def test_scaled_singleton_two_level_engine_preserves_parent_value():
    """Engine-level Hermite recursion: two levels active, independent parent check."""
    report = contract_scaled(
        tensor_parent(),
        levels=1,
        strategy="scaled_singletons",
        policy=Policy(max_seconds=240),
    )
    assert report["status"] == "PASS_FINITE_SCALED_PARENT_CHILD_IDENTITY"
    assert report["parent_child_recursion_performed"]
    assert report["result"] == ((7, 0, 0, 0),)


def test_child_leaf_values_match_verify_children_on_small_crossing():
    parent, layout, modes = three_crossing_matching()
    budget = Budget(replace(DEFAULT_SHRINKING_POLICY, max_precision=65536))
    beta = ExponentTuple(modes.content_digest, (0, 0, 0))
    children = construct_children(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        _admitted=True,
        require_shrink=True,
    )
    verified = verify_children(
        parent, layout, modes, beta, children, budget=budget, _admitted=True
    )
    for child, expected in zip(children[:5], verified["values"][:5]):
        assert leaf(child.as_parent(parent), budget) == expected
