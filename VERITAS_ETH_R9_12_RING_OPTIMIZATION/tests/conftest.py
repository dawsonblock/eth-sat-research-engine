"""Shared pytest fixtures for VERITAS interaction proofs."""
import pytest

from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.independent import verify_children
from veritas.research.parent_child_r913.coefficient_reconstruction import (
    reconstruct_parent_coefficient_one_level,
)
from tests.fixtures.interaction_96_circulant import (
    interaction_96_from_tmp_path_factory,
)


@pytest.fixture(scope="module")
def interaction_96_jet_point(tmp_path_factory):
    return interaction_96_from_tmp_path_factory(tmp_path_factory)


@pytest.fixture(scope="module")
def circulant_children(interaction_96_jet_point):
    """Single construct+verify at jet point 1; shared by interaction and two-level tests."""
    ctx = interaction_96_jet_point
    children = construct_children(
        ctx.parent,
        ctx.layout,
        ctx.modes,
        ctx.beta,
        budget=ctx.budget,
        _admitted=True,
        require_shrink=True,
    )
    verified = verify_children(
        ctx.parent,
        ctx.layout,
        ctx.modes,
        ctx.beta,
        children,
        budget=ctx.budget,
        _admitted=True,
    )
    return (
        ctx.parent,
        ctx.layout,
        ctx.modes,
        ctx.beta,
        children,
        verified,
        ctx.budget,
    )


@pytest.fixture(scope="module")
def interaction_96_one_level_reconstruction(interaction_96_jet_point, circulant_children):
    parent, layout, modes, beta, children, verified, budget = circulant_children
    result = reconstruct_parent_coefficient_one_level(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        require_shrink=True,
        children=children,
        verified=verified,
    )
    return interaction_96_jet_point, result
