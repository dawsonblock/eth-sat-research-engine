"""Pinned interaction fixture metadata for digest-gated jet diagnostics."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

from veritas.research.parent_child_r912.interaction_layout import circulant_separated_layout
from veritas.research.parent_child_r98.model import Budget, ParentCall, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY

INTERACTION_96_PARENT_DIGEST = (
    "5c6942f759cf5b6c2d98d88b5617a598afddbcd3904916f7182c86afbc764bbf"
)
INTERACTION_96_GRAPH_N = 32
INTERACTION_96_OFFSET = 5


def load_pinned_interaction_96_parent(*, max_extension_degree: int = 12) -> ParentCall:
    """Build ParentCall for circulant interaction graph (32, offset 5)."""
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "interaction_probe", root / "scripts/experiment_r912_interaction.py"
    )
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "input.json"
        source.write_bytes(canonical(probe.graph(INTERACTION_96_GRAPH_N, offset=INTERACTION_96_OFFSET)))
        return load_input(source, max_extension_degree=max_extension_degree)


def interaction_96_layout_and_budget(parent: ParentCall) -> tuple[object, Budget]:
    from dataclasses import replace

    policy = replace(
        DEFAULT_SHRINKING_POLICY,
        max_work=40_000_000,
        max_seconds=600,
        max_edges=128,
        max_precision=16384,
    )
    budget = Budget(policy)
    layout = circulant_separated_layout(parent, 1, 1, budget)
    return layout, budget
