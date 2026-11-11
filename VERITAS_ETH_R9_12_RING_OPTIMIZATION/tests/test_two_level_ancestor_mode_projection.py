"""Two-level lemma: ancestor mode projection vs half-edge child values."""
import importlib.util
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r98.model import Budget, ExponentTuple, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.independent import verify_children
from veritas.research.parent_child_r912.interaction_layout import (
    child_layout_for_nesting,
    circulant_separated_layout,
)
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r913.coefficient_reconstruction import (
    modes_at_jet_point,
    project_ancestor_modes_onto_child,
    reconstruct_parent_coefficient_one_level,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(
    DEFAULT_SHRINKING_POLICY,
    max_work=40_000_000,
    max_edges=128,
    max_precision=65536,
)


@pytest.fixture(scope="module")
def circulant_children():
    spec = importlib.util.spec_from_file_location(
        "interaction_probe", ROOT / "scripts/experiment_r912_interaction.py"
    )
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as handle:
        handle.write(canonical(probe.graph(32, offset=5)))
        path = Path(handle.name)
    parent = load_input(path, max_extension_degree=12)
    layout = circulant_separated_layout(parent, 1, 1, Budget(POLICY))
    modes, *_ = modes_at_jet_point(parent, layout, budget=Budget(POLICY), point_index=1)
    beta = ExponentTuple(
        modes.content_digest, tuple(0 for _ in modes.certificate["modes"])
    )
    budget = Budget(POLICY)
    children = construct_children(
        parent, layout, modes, beta, budget=budget, _admitted=True, require_shrink=True
    )
    verified = verify_children(
        parent, layout, modes, beta, children, budget=budget, _admitted=True
    )
    return parent, layout, modes, beta, children, verified, budget


def _grandchild_product_matches_half_edge(child, ancestor, layout, modes, beta, verified, budget):
    call = child.as_parent(ancestor)
    child_layout = child_layout_for_nesting(child, call, layout, budget=budget)
    child_modes = project_ancestor_modes_onto_child(
        child, modes, child_layout, call, budget=budget
    )
    child_beta = ExponentTuple(child_modes.content_digest, beta.values)
    nested = reconstruct_parent_coefficient_one_level(
        call,
        child_layout,
        child_modes,
        child_beta,
        budget=budget,
        require_shrink=False,
    )
    return nested.reconstructed == verified["values"][child.group]


@pytest.mark.parametrize("group", [0, 15, 31])
def test_two_level_lemma_holds_for_low_circulant_groups(circulant_children, group):
    parent, layout, modes, beta, children, verified, budget = circulant_children
    child = children[group]
    assert _grandchild_product_matches_half_edge(
        child, parent, layout, modes, beta, verified, budget
    )


@pytest.mark.parametrize("group", [32, 47, 63])
def test_two_level_lemma_blocked_for_column_sourced_star_children(circulant_children, group):
    """Groups ≥32 are X-only stars: one row vertex, several parent row groups — no D3 layout."""
    parent, layout, modes, beta, children, verified, budget = circulant_children
    child = children[group]
    assert not _grandchild_product_matches_half_edge(
        child, parent, layout, modes, beta, verified, budget
    )
