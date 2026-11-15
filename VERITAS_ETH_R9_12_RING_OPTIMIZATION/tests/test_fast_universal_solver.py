"""Fast universal jet-point parent solver."""
from veritas.research.parent_child_r913.fast_universal_solver import (
    UniversalSolveMethod,
    fast_universal_parent_jet_solve,
)


def test_fast_universal_solver_on_shared_fixture(interaction_96_jet_point, circulant_children):
    ctx = interaction_96_jet_point
    _parent, _layout, _modes, _beta, children, verified, budget = circulant_children
    result = fast_universal_parent_jet_solve(
        ctx.parent,
        ctx.layout,
        budget=budget,
        point_index=1,
        children=children,
        verified=verified,
    )
    assert result.method == UniversalSolveMethod.PARENT_CHILD_PRODUCT
    assert result.reconstruction_equals_oracle
    assert result.child_group_count == 64
    assert result.elapsed_seconds < 30
