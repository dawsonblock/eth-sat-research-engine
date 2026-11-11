"""Bridge R9.12 parents to bounded packet resummation experiments."""
from __future__ import annotations

from typing import Tuple

from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, PacketLayout, ParentCall
from veritas.research.parent_child_r98.model import decode
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r912.jet_recovery import JetRecovery
from veritas.research.tapered_v4.source_recipes import EntryBudget, EntryLimits, compile_entry


def compiled_child_packet_at_jet_point(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    group: int = 0,
    point_index: int = 0,
    max_points: int | None = None,
) -> Tuple[object, dict]:
    """Return ``(CompiledEntry, row_certificate)`` for one constructor-built packet."""
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
        beta_values = tuple(0 for _ in modes.certificate["modes"])
        beta = ExponentTuple(modes.content_digest, beta_values)
        children = construct_children(parent, layout, modes, beta, budget=budget)
        if group >= len(children):
            raise ValueError("group index outside constructed child range")
        child = children[group]
        for vertex in child.vertices:
            if vertex.side != "column":
                continue
            if decode(vertex.tensor.description).get("kind") != "packet":
                continue
            limits = EntryLimits(
                max_seconds=min(60, budget.policy.max_seconds),
                max_precision_bits=budget.policy.max_precision,
            )
            compiled = compile_entry(vertex.tensor, EntryBudget(limits))
            return compiled, row_certificate
        raise ValueError("constructed child exposes no packet column vertex")
    raise ValueError("jet recovery produced no point at the requested index")
