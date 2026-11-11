"""Certified dependency and elimination-width analyzer (bounded fixtures)."""
from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r913.dependency_analyzer import (
    analyze_mode_certificate,
    child_mode_dependencies,
    mode_factor_graph_from_modes,
    report_to_dict,
)
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r99.support_circuit import SupportCircuit

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=2_000_000)


def test_child_dependencies_hand_modes():
    certificate = {
        "modes": [
            {
                "packet": 0,
                "target_group": 0,
                "source_group": 1,
                "weight": 1,
                "rows": [[0, []]],
                "column_terms": [],
            },
            {
                "packet": 0,
                "target_group": 1,
                "source_group": 0,
                "weight": 1,
                "rows": [[1, []]],
                "column_terms": [],
            },
        ],
        "precision": 5,
    }
    deps = child_mode_dependencies(certificate, 2)
    assert deps[0].target_modes == (0,)
    assert deps[0].source_modes == (1,)
    assert deps[1].target_modes == (1,)
    assert deps[1].source_modes == (0,)


def test_elimination_width_toy_incidence():
    modes = [
        {
            "packet": 0,
            "weight": 1,
            "rows": [[0, None], [1, None]],
            "target_group": 0,
            "source_group": 0,
        },
        {
            "packet": 0,
            "weight": 1,
            "rows": [[0, None]],
            "target_group": 0,
            "source_group": 0,
        },
        {
            "packet": 1,
            "weight": 1,
            "rows": [[2, None]],
            "target_group": 0,
            "source_group": 0,
        },
    ]
    graph = mode_factor_graph_from_modes(modes)
    assert len(graph.scopes) == 3
    report = analyze_mode_certificate(
        {"modes": modes, "precision": 4},
        group_count=1,
        budget=EliminationBudget(max_width=8),
    )
    summary = report_to_dict(report)
    assert summary["elimination_width"] >= 0
    assert summary["factor_rows"] == 3
    assert not summary["subexponential_bound_evidence"]


def _packet_point_modes(parent, layout):
    from veritas.research.parent_child_r912.jet_recovery import JetRecovery

    certificate = certify_row_degree(parent, 1, budget=Budget(POLICY))
    recovery = JetRecovery(parent, layout, certificate, budget=Budget(POLICY), max_points=4096)
    for t, zeta, _ in recovery.points():
        return build_packet_modes(
            parent,
            layout,
            t,
            zeta,
            budget=Budget(POLICY),
            row_certificate=certificate,
        ), certificate
    raise RuntimeError("no jet recovery point")


def test_matching22_point_dependencies():
    parent = load_input(ROOT / "examples/r98_general_matching22.json")
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(POLICY))
    original, certificate = _packet_point_modes(parent, layout)
    record = original.certificate
    group_count = layout.a * layout.u
    report = analyze_mode_certificate(record, group_count, row_certificate=certificate)
    assert report.mode_count == len(record["modes"])
    assert all(c.group < group_count for c in report.children)
    circuit = SupportCircuit(
        record["modes"], record["precision"], budget=Budget(POLICY), row_certificate=certificate
    )
    assert circuit.count() >= 1
    summary = report_to_dict(report)
    assert summary["elimination_fits"] is True


def test_96_wire_metadata_elimination_width_without_full_cube():
    """Metadata-only: one mode per wire, no 2**96 enumeration."""
    modes = [
        {
            "packet": index,
            "weight": 1,
            "rows": [[index, None]],
            "target_group": 0,
            "source_group": 0,
        }
        for index in range(96)
    ]
    certificate = {"nonconstant_row_ports": list(range(96))}
    circuit = SupportCircuit(modes, 512, budget=Budget(POLICY), row_certificate=certificate)
    assert circuit.summary()["components"] == 96
    report = analyze_mode_certificate(
        {"modes": modes, "precision": 512},
        1,
        row_certificate=certificate,
        budget=EliminationBudget(max_width=20),
    )
    assert report.elimination.width == 0
    assert report.factor_graph.scopes and max(map(len, report.factor_graph.scopes)) == 1
