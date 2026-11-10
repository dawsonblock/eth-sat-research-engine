"""Certified mode-dependency and elimination-width sketches (constructor path).

Mode incidence and per-child mode sets are derived from the same rules as
``construct_children`` and ``affine_incidence`` — no random sampling.

Elimination-width estimates use the ordinary min-fill / min-degree heuristic
on the mode interaction graph (each affine row is one factor). Computing an
optimal elimination order is NP-hard; results are **not** treewidth certificates.

No ETH theorem, subexponential bound, or factorized child-sum proof is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from veritas.research.parent_child_r912.elimination import (
    EliminationBudget,
    plan_order,
    verify_order,
)
from veritas.research.parent_child_r99.support_circuit import affine_incidence


@dataclass(frozen=True)
class ChildModeDependency:
    """Modes that appear in one child group's packet recipe (target/source)."""

    group: int
    target_modes: Tuple[int, ...]
    source_modes: Tuple[int, ...]
    packets: Tuple[int, ...]


@dataclass(frozen=True)
class ModeFactorGraph:
    """Row-incidence factors over mode-index variables."""

    scopes: Tuple[Tuple[int, ...], ...]
    variables: Tuple[int, ...]
    row_keys: Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class EliminationWidthEstimate:
    order: Tuple[int, ...]
    width: int
    max_table_entries: int
    peak_live_entries: int
    predicted_work: int
    fits: bool
    reason: str | None
    heuristic: str
    budget: Dict[str, object]
    qualification: str = "heuristic_elimination_width_not_treewidth"


@dataclass(frozen=True)
class DependencyAnalysisReport:
    children: Tuple[ChildModeDependency, ...]
    factor_graph: ModeFactorGraph
    elimination: EliminationWidthEstimate
    mode_count: int
    notes: Tuple[str, ...] = field(default_factory=tuple)


def child_mode_dependencies(
    modes_certificate: dict,
    group_count: int,
) -> Tuple[ChildModeDependency, ...]:
    """Mirror ``construct_children`` target/source group selection exactly."""
    modes = modes_certificate["modes"]
    if type(group_count) is not int or group_count < 1:
        raise ValueError("positive group_count required")
    children: List[ChildModeDependency] = []
    for group in range(group_count):
        targets = tuple(
            mid
            for mid, mode in enumerate(modes)
            if mode.get("target_group", 0) == group
        )
        sources = tuple(
            mid
            for mid, mode in enumerate(modes)
            if mode.get("source_group", 0) == group
        )
        packets = tuple(
            sorted(
                {
                    mode["packet"]
                    for mid in (*targets, *sources)
                    for mode in [modes[mid]]
                }
            )
        )
        children.append(
            ChildModeDependency(
                group=group,
                target_modes=targets,
                source_modes=sources,
                packets=packets,
            )
        )
    return tuple(children)


def mode_factor_graph_from_modes(
    modes: Sequence[dict],
    *,
    row_certificate: dict | None = None,
) -> ModeFactorGraph:
    """Build scopes = one affine row per factor, variables = mode indices."""
    incidence = affine_incidence(modes, row_certificate)
    row_keys = tuple(sorted(incidence))
    scopes = tuple(tuple(sorted(incidence[key])) for key in row_keys)
    variables = tuple(range(len(modes)))
    return ModeFactorGraph(scopes=scopes, variables=variables, row_keys=row_keys)


def estimate_mode_elimination_width(
    graph: ModeFactorGraph,
    *,
    budget: EliminationBudget | None = None,
    heuristic: str = "min_fill",
) -> EliminationWidthEstimate:
    """Symbolic width replay for a fixed heuristic (NP-hard optimum not sought)."""
    budget = EliminationBudget() if budget is None else budget
    order = plan_order(graph.scopes, graph.variables, heuristic)
    certificate = verify_order(graph.scopes, graph.variables, order, budget)
    return EliminationWidthEstimate(
        order=order,
        width=int(certificate["width"]),
        max_table_entries=int(certificate["max_table_entries"]),
        peak_live_entries=int(certificate["peak_live_entries"]),
        predicted_work=int(certificate["predicted_work"]),
        fits=bool(certificate["fits"]),
        reason=certificate.get("reason"),
        heuristic=heuristic,
        budget=certificate["budget"],
    )


def analyze_mode_certificate(
    modes_certificate: dict,
    group_count: int,
    *,
    budget: EliminationBudget | None = None,
    row_certificate: dict | None = None,
    heuristic: str = "min_fill",
) -> DependencyAnalysisReport:
    """Full report: child deps, factor graph, elimination-width estimate."""
    modes = modes_certificate["modes"]
    children = child_mode_dependencies(modes_certificate, group_count)
    graph = mode_factor_graph_from_modes(modes, row_certificate=row_certificate)
    elimination = estimate_mode_elimination_width(
        graph, budget=budget, heuristic=heuristic
    )
    notes = (
        "Child mode sets follow construct_children packet filtering.",
        "Elimination order is greedy min-fill/min-degree only.",
        "Width is max frontier after row elimination, not treewidth.",
    )
    return DependencyAnalysisReport(
        children=children,
        factor_graph=graph,
        elimination=elimination,
        mode_count=len(modes),
        notes=notes,
    )


def report_to_dict(report: DependencyAnalysisReport) -> Dict[str, object]:
    """JSON-friendly summary for tests."""
    return {
        "schema": "VERITAS_R913_DEPENDENCY_ANALYSIS_V1",
        "mode_count": report.mode_count,
        "children": [
            {
                "group": c.group,
                "target_modes": list(c.target_modes),
                "source_modes": list(c.source_modes),
                "packets": list(c.packets),
            }
            for c in report.children
        ],
        "factor_rows": len(report.factor_graph.scopes),
        "elimination_width": report.elimination.width,
        "elimination_fits": report.elimination.fits,
        "elimination_heuristic": report.elimination.heuristic,
        "predicted_work": report.elimination.predicted_work,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "qualification": report.elimination.qualification,
        "notes": list(report.notes),
    }
