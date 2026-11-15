"""Jet-point mode certificates for circulant interaction fixtures."""
from __future__ import annotations

from typing import Tuple

from veritas.research.parent_child_r912.jet_recovery import JetRecovery
from veritas.research.parent_child_r98.model import Budget, PacketLayout, ParentCall
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.row_degree import certify_row_degree


def packet_modes_at_jet_point(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    max_points: int | None = None,
) -> Tuple[dict, dict, int, Tuple[int, ...], Tuple[int, ...]]:
    """Return modes certificate, row certificate, jet index, node, zeta."""
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
    for index, (node, zeta, _residue) in enumerate(recovery.points()):
        if index != point_index:
            continue
        modes = build_packet_modes(
            parent,
            layout,
            node,
            zeta,
            budget=budget,
            row_certificate=row_certificate,
        )
        return modes.certificate, row_certificate, index, node, tuple(zeta)
    raise ValueError("jet recovery produced no point at the requested index")
