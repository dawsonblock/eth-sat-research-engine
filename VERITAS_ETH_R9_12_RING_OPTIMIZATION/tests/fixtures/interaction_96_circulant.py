"""Shared 96-wire circulant parent at jet point 1 (β=0) for interaction proofs."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, replace
from pathlib import Path
from veritas.research.parent_child_r98.model import (
    Budget,
    ExponentTuple,
    ModeSet,
    PacketLayout,
    ParentCall,
    canonical,
)
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r912.interaction_layout import circulant_separated_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r913.coefficient_reconstruction import modes_at_jet_point

ROOT = Path(__file__).resolve().parents[2]

INTERACTION_96_POLICY = replace(
    DEFAULT_SHRINKING_POLICY,
    max_work=40_000_000,
    max_seconds=600,
    max_edges=128,
    max_precision=16384,
)


@dataclass(frozen=True)
class Interaction96JetPoint:
    parent: ParentCall
    layout: PacketLayout
    modes: ModeSet
    beta: ExponentTuple
    budget: Budget


def load_interaction_96_graph(tmp_path_factory) -> Path:
    spec = importlib.util.spec_from_file_location(
        "interaction_probe", ROOT / "scripts/experiment_r912_interaction.py"
    )
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    source = tmp_path_factory.mktemp("interaction96") / "input.json"
    source.write_bytes(canonical(probe.graph(32, offset=5)))
    return source


def build_interaction_96_at_jet_point(
    source: Path,
    *,
    point_index: int = 1,
    policy=INTERACTION_96_POLICY,
) -> Interaction96JetPoint:
    parent = load_input(source, max_extension_degree=12)
    budget = Budget(policy)
    layout = circulant_separated_layout(parent, 1, 1, budget)
    modes, *_ = modes_at_jet_point(parent, layout, budget=budget, point_index=point_index)
    mode_count = len(modes.certificate["modes"])
    beta = ExponentTuple(modes.content_digest, tuple(0 for _ in range(mode_count)))
    return Interaction96JetPoint(parent, layout, modes, beta, budget)


def interaction_96_from_tmp_path_factory(tmp_path_factory, point_index: int = 1) -> Interaction96JetPoint:
    return build_interaction_96_at_jet_point(
        load_interaction_96_graph(tmp_path_factory), point_index=point_index
    )
