"""96-wire circulant: C_parent(beta) = product of constructed child contractions."""
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r98.model import Budget, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r912.interaction_layout import circulant_separated_layout
from veritas.research.parent_child_r913.coefficient_reconstruction import (
    modes_at_jet_point,
    reconstruct_interaction_parent_at_jet_point,
    reconstruct_interaction_two_level_at_jet_point,
    reconstruct_interaction_with_leaf_at_jet_point,
    wire_elimination_vs_parent_coefficient,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(
    DEFAULT_SHRINKING_POLICY,
    max_work=40_000_000,
    max_seconds=600,
    max_edges=128,
    max_precision=16384,
)


@pytest.fixture(scope="module")
def interaction_96_parent(tmp_path_factory):
    spec = importlib.util.spec_from_file_location(
        "interaction_probe", ROOT / "scripts/experiment_r912_interaction.py"
    )
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    source = tmp_path_factory.mktemp("interaction") / "input.json"
    source.write_bytes(canonical(probe.graph(32, offset=5)))
    parent = load_input(source, max_extension_degree=12)
    layout = circulant_separated_layout(parent, 1, 1, Budget(POLICY))
    return parent, layout


@pytest.fixture(scope="module")
def interaction_96_jet_point(interaction_96_parent):
    parent, layout = interaction_96_parent
    budget = Budget(POLICY)
    modes, *_ = modes_at_jet_point(parent, layout, budget=budget, point_index=1)
    return parent, layout, modes, budget


def test_circulant_96_wire_one_level_and_diagnostics(interaction_96_jet_point):
    parent, layout, modes, budget = interaction_96_jet_point
    result = reconstruct_interaction_parent_at_jet_point(
        parent,
        layout,
        budget=budget,
        point_index=1,
    )
    assert result.reconstruction_equals_oracle
    assert result.child_group_count == 64
    assert len(result.beta) == 96

    leaf_result = reconstruct_interaction_with_leaf_at_jet_point(
        parent,
        layout,
        budget=budget,
        point_index=1,
    )
    assert leaf_result.reconstruction_equals_oracle

    sparse_beta = tuple(1 if i < 3 else 0 for i in range(len(result.beta)))
    sparse = reconstruct_interaction_parent_at_jet_point(
        parent, layout, budget=budget, point_index=1, beta_values=sparse_beta
    )
    assert sparse.reconstruction_equals_oracle

    vs = wire_elimination_vs_parent_coefficient(parent, layout, budget=budget, point_index=1)
    assert vs["wire_elimination_equals_parent_coefficient"] is False
    assert vs["reconstruction_equals_oracle"] is True


@pytest.mark.slow
def test_circulant_96_wire_two_level_grandchild_product(interaction_96_jet_point):
    parent, layout, _modes, budget = interaction_96_jet_point
    two_level = reconstruct_interaction_two_level_at_jet_point(
        parent, layout, budget=budget, point_index=1
    )
    assert two_level.active_levels == 2
    assert two_level.reconstruction_equals_oracle
    assert two_level.second_level_kind == "grandchild_product"
    assert two_level.nested_child_groups == 64
    assert "column_sourced_star_half_edge_bucket_count=32" in two_level.qualification
