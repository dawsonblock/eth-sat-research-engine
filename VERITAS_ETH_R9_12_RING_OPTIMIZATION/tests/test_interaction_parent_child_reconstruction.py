"""96-wire circulant: C_parent(beta) = product of constructed child contractions."""
import pytest

from veritas.research.parent_child_r913.coefficient_reconstruction import (
    reconstruct_interaction_parent_at_jet_point,
    reconstruct_interaction_two_level_at_jet_point,
    reconstruct_interaction_with_leaf_at_jet_point,
    wire_elimination_vs_parent_coefficient,
)


def test_circulant_96_wire_one_level_reconstruction(interaction_96_one_level_reconstruction):
    _ctx, result = interaction_96_one_level_reconstruction
    assert result.reconstruction_equals_oracle
    assert result.child_group_count == 64
    assert len(result.beta) == 96


@pytest.mark.slow
def test_circulant_96_wire_leaf_recheck_at_jet_point(
    interaction_96_jet_point, circulant_children
):
    ctx = interaction_96_jet_point
    _parent, _layout, _modes, _beta, children, verified, budget = circulant_children
    leaf_result = reconstruct_interaction_with_leaf_at_jet_point(
        ctx.parent,
        ctx.layout,
        budget=budget,
        point_index=1,
        children=children,
        verified=verified,
    )
    assert leaf_result.reconstruction_equals_oracle
    assert leaf_result.second_level_kind == "leaf_recheck"


@pytest.mark.slow
def test_circulant_96_wire_sparse_beta_reconstruction(interaction_96_jet_point):
    ctx = interaction_96_jet_point
    dense = reconstruct_interaction_parent_at_jet_point(
        ctx.parent, ctx.layout, budget=ctx.budget, point_index=1
    )
    sparse_beta = tuple(1 if i < 3 else 0 for i in range(len(dense.beta)))
    sparse = reconstruct_interaction_parent_at_jet_point(
        ctx.parent,
        ctx.layout,
        budget=ctx.budget,
        point_index=1,
        beta_values=sparse_beta,
    )
    assert sparse.reconstruction_equals_oracle


@pytest.mark.slow
def test_circulant_96_wire_wire_elimination_vs_coefficient(
    interaction_96_one_level_reconstruction,
):
    ctx, result = interaction_96_one_level_reconstruction
    vs = wire_elimination_vs_parent_coefficient(
        ctx.parent,
        ctx.layout,
        budget=ctx.budget,
        point_index=1,
        reconstruction=result,
    )
    assert vs["wire_elimination_equals_parent_coefficient"] is False
    assert vs["reconstruction_equals_oracle"] is True


@pytest.mark.slow
def test_circulant_96_wire_two_level_grandchild_product(interaction_96_jet_point):
    ctx = interaction_96_jet_point
    two_level = reconstruct_interaction_two_level_at_jet_point(
        ctx.parent, ctx.layout, budget=ctx.budget, point_index=1
    )
    assert two_level.active_levels == 2
    assert two_level.reconstruction_equals_oracle
    assert two_level.second_level_kind == "grandchild_product"
    assert two_level.nested_child_groups == 64
    assert two_level.column_sourced_star_half_edge_bucket_count == 32
