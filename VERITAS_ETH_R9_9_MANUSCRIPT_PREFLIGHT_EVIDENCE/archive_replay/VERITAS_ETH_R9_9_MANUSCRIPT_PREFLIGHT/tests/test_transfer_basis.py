"""Transfer may describe a complete basis without enumerating its tuples."""

from math import comb
from pathlib import Path

import pytest

from veritas.research.parent_child_r98.general_modes import build_general_modes
from veritas.research.parent_child_r98.model import Budget, Refusal
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r98.transfer_basis import build_transfer_basis


ROOT = Path(__file__).resolve().parents[1]


def test_admitted_small_basis_matches_unchanged_full_tuple_basis():
    parent = load_input(ROOT / "examples/r98_general_matching22.json")
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    layout = construct_vertex_shrinking_layout(parent, groups=64, budget=budget)
    zeta = (1, 0, 0, 0, 0, 0, 0)
    transfer = build_transfer_basis(parent, layout, 1, zeta, budget=budget)
    general = build_general_modes(parent, layout, 1, zeta, budget=budget)
    assert transfer.certificate_bytes == general.certificate_bytes
    assert transfer.certificate["mode_tuple_count"] == 1


def test_large_cycle_basis_counts_complete_stream_without_enumerating_it():
    parent = load_input(ROOT / "examples/r98_shrinking_cycle484.json")
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    layout = construct_vertex_shrinking_layout(parent, groups=512, budget=budget)
    basis = build_transfer_basis(parent, layout, 1, (1, 0), budget=budget)
    data = basis.certificate
    assert len(data["modes"]) == len(data["cross_pairs"]) == 242
    assert data["precision"] == 31488
    assert data["mode_tuple_count"] == comb(31488 + 242 - 1, 242)
    assert budget.calls == budget.tuples == budget.transitions == 0
    with pytest.raises(Refusal, match="complete general weighted tuple count"):
        build_general_modes(parent, layout, 1, (1, 0), budget=budget)


def test_zero_point_preserves_crossing_ports_and_has_one_empty_tuple():
    parent = load_input(ROOT / "examples/r98_shrinking_cycle484.json")
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    layout = construct_vertex_shrinking_layout(parent, groups=512, budget=budget)
    basis = build_transfer_basis(parent, layout, -1, (0, 0), budget=budget)
    data = basis.certificate
    assert len(data["cross_pairs"]) == 242
    assert data["local"] == data["modes"] == []
    assert data["mode_tuple_count"] == 1
