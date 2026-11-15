"""Two-level lemma: ancestor mode projection vs half-edge child values."""
import pytest

from veritas.research.parent_child_r913.coefficient_reconstruction import (
    reconstruct_child_two_level_inner_lemma,
)


def _grandchild_product_matches_half_edge(child, ancestor, layout, modes, beta, verified, budget):
    reconstructed = reconstruct_child_two_level_inner_lemma(
        child, ancestor, layout, modes, beta, budget=budget
    )
    return reconstructed == verified["values"][child.group]


@pytest.mark.parametrize("group", [0, 15, 31])
def test_two_level_lemma_holds_for_low_circulant_groups(circulant_children, group):
    parent, layout, modes, beta, children, verified, budget = circulant_children
    child = children[group]
    assert _grandchild_product_matches_half_edge(
        child, parent, layout, modes, beta, verified, budget
    )


@pytest.mark.parametrize("group", [32, 47, 63])
def test_two_level_lemma_holds_for_column_sourced_star_children(circulant_children, group):
    """Groups ≥32 use shared-inherited half-edge bucket grandchild products."""
    parent, layout, modes, beta, children, verified, budget = circulant_children
    child = children[group]
    assert _grandchild_product_matches_half_edge(
        child, parent, layout, modes, beta, verified, budget
    )
