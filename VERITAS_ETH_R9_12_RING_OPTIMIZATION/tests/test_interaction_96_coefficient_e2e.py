"""Parallel diagnostics on circulant 96-wire: parent elimination + independent-row child A_beta."""
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r912.interaction_coefficient_harness import (
    interaction_coefficient_end_to_end,
)
from veritas.research.parent_child_r98.model import Budget, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(
    DEFAULT_SHRINKING_POLICY,
    max_work=8_000_000,
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
    layout = probe.separated_layout(parent, 1, 1, Budget(POLICY))
    return parent, layout, probe


def test_circulant_96_wire_child_coefficient_vs_elimination_baseline(interaction_96_parent):
    parent, layout, _probe = interaction_96_parent
    assert parent.edge_count == 96
    budget = EliminationBudget(max_width=20)
    report = interaction_coefficient_end_to_end(
        parent,
        layout,
        shrink_budget=Budget(POLICY),
        elimination_budget=budget,
        point_index=1,
    )
    parent_block = report["parent_wire_elimination"]
    child_block = report["child_target_coefficient"]
    assert parent_block["status"] == "PASS_EXACT_BOUNDED_WIDTH_ELIMINATION"
    assert parent_block["elimination_width"] == 17
    assert report["mode_count"] == 96
    assert child_block["independent_row_shape"] is True
    assert child_block["separator_agrees_with_independent_reference"] is True
    assert child_block["separator_max_monomial_table"] <= 8
    assert child_block["separator_join_count"] == 96
    assert child_block["largest_local_support"] == 2
    assert not report["source_qualified"]
    assert child_block["elapsed_seconds"] < 120
