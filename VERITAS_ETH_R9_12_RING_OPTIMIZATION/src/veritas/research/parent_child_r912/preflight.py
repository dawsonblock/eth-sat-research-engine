"""Read-only preflight before exact wire elimination.

Combines the existing symbolic wire-order certificate from
``elimination.plan`` with an optional mode-dependency sketch from
``parent_child_r913.dependency_analyzer``. No elimination tables are
allocated and no child contractions are run.

No ETH theorem, subexponential bound, or source-qualification claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from veritas.research.parent_child_r98.model import Budget, PacketLayout, ParentCall, Refusal, Semantics
from veritas.research.parent_child_r913.dependency_analyzer import (
    analyze_mode_certificate,
    report_to_dict as mode_report_to_dict,
)
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r912.jet_recovery import JetRecovery

from .elimination import EliminationBudget, call_scopes, plan


@dataclass(frozen=True)
class EliminationPreflight:
    """Wire elimination sketch plus optional packet-mode metadata."""

    wire: Dict[str, object]
    mode_dependency: Optional[Dict[str, object]]
    source_qualified: bool = False
    subexponential_bound_evidence: bool = False


def wire_elimination_preflight(
    call: ParentCall,
    budget: EliminationBudget,
) -> Dict[str, object]:
    """Replay-only wire plan; identical certificate to ``plan(call, budget)``."""
    if call.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        return {
            "schema": "VERITAS_R912_WIRE_PREFLIGHT_V1",
            "status": "SKIPPED_NON_FINITE_SEMANTICS",
            "reason": "wire elimination preflight requires finite scaled experiment",
        }
    scopes, variables = call_scopes(call)
    certificate = plan(call, budget)
    return {
        "schema": "VERITAS_R912_WIRE_PREFLIGHT_V1",
        "status": "COMPLETE",
        "factor_count": len(scopes),
        "wire_count": len(variables),
        "scopes": [list(s) for s in scopes],
        "ordering": certificate,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "qualification": certificate.get("width_definition"),
    }


def packet_mode_preflight(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    elimination_budget: EliminationBudget | None = None,
    max_points: int | None = None,
    point_index: int = 0,
) -> Dict[str, object]:
    """Mode dependency and elimination-width sketch at one jet recovery point."""
    row_certificate = certify_row_degree(parent, layout.a, budget=budget)
    if max_points is None:
        degree_cap = int(row_certificate["degree_bound"]) + 1
        max_points = min(4096, max(256, degree_cap))
    recovery = JetRecovery(
        parent,
        layout,
        row_certificate,
        budget=budget,
        max_points=max_points,
    )
    chosen = None
    for index, (node, zeta, _residue) in enumerate(recovery.points()):
        if index < point_index:
            continue
        chosen = (index, node, zeta)
        break
    if chosen is None:
        raise ValueError("jet recovery produced no point at the requested index")
    index, node, zeta = chosen
    modes = build_packet_modes(
        parent,
        layout,
        node,
        zeta,
        budget=budget,
        row_certificate=row_certificate,
    )
    while len(modes.certificate["modes"]) == 0:
        next_index = index + 1
        chosen = None
        for scan, (node, zeta, _residue) in enumerate(recovery.points()):
            if scan < next_index:
                continue
            chosen = (scan, node, zeta)
            break
        if chosen is None:
            break
        index, node, zeta = chosen
        modes = build_packet_modes(
            parent,
            layout,
            node,
            zeta,
            budget=budget,
            row_certificate=row_certificate,
        )
    from veritas.research.parent_child_r98.model import layout_group_count

    group_count = layout_group_count(parent, layout)
    report = analyze_mode_certificate(
        modes.certificate,
        group_count,
        budget=elimination_budget or EliminationBudget(),
        row_certificate=row_certificate,
    )
    summary = mode_report_to_dict(report)
    summary.update(
        {
            "schema": "VERITAS_R912_PACKET_MODE_PREFLIGHT_V1",
            "status": "COMPLETE",
            "jet_node": node,
            "jet_point_index": index,
            "layout_digest": layout.content_digest,
            "modes_digest": modes.content_digest,
            "row_degree_certificate": row_certificate,
        }
    )
    return summary


def elimination_preflight(
    parent: ParentCall,
    budget: EliminationBudget,
    *,
    layout: PacketLayout | None = None,
    shrink_budget: Budget | None = None,
) -> EliminationPreflight:
    """Unified read-only report used before ``eliminate`` or route selection."""
    wire = wire_elimination_preflight(parent, budget)
    mode_block: Optional[Dict[str, object]] = None
    if layout is not None:
        if shrink_budget is None:
            from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY

            shrink_budget = Budget(DEFAULT_SHRINKING_POLICY)
        try:
            mode_block = packet_mode_preflight(
                parent,
                layout,
                budget=shrink_budget,
                elimination_budget=budget,
            )
        except (ValueError, TypeError, KeyError, Refusal, RuntimeError, MemoryError) as exc:
            mode_block = {
                "schema": "VERITAS_R912_PACKET_MODE_PREFLIGHT_V1",
                "status": "INCONCLUSIVE",
                "reason": str(exc),
            }
    return EliminationPreflight(wire=wire, mode_dependency=mode_block)


def preflight_to_dict(report: EliminationPreflight) -> Dict[str, object]:
    """JSON-friendly envelope for route reports and tests."""
    return {
        "schema": "VERITAS_R912_ELIMINATION_PREFLIGHT_V1",
        "wire": report.wire,
        "mode_dependency": report.mode_dependency,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
    }
