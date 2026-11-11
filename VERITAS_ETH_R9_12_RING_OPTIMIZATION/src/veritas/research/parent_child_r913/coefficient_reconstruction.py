"""Reconstruct parent deformation coefficients from contracted child group values.

This establishes the equality requested in ``research_spec`` at **one active
recursive level** and one retained exponent tuple β:

```text
C_parent(β) = ∏_g C_child_g(β)
```

Here ``C_child_g`` is the jet value produced by independent half-edge elimination
on the constructed group child (``verify_children``), i.e. the production child
graph semantics.  It is **not** the separator packet coefficient ``A_β`` on an
isolated column packet unless the child is a leaf whose graph collapses to that
packet evaluation.

At **two levels** on the 96-wire circulant jet fixture (β = 0), when child modes
are obtained by projecting the ancestor jet certificate onto each constructed
child's half-edge renumbering, the inner lemma

```text
C_child_g = ∏_h C_grandchild_h
```

holds for group indices ``g = 0 … 31`` and fails for ``g ≥ 32`` (leaf fallback
preserves the outer product). The outer equality ``C_parent = ∏_g C_child_g``
remains valid in all cases via half-edge semantics.

No ETH, subexponential, or source-qualification claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.independent import verify_children
from veritas.research.parent_child_r98.modes import (
    verify_inherited_construction_modes,
    weighted_count,
)
from veritas.research.parent_child_r98.model import (
    Budget,
    ChildGraph,
    ExponentTuple,
    ModeSet,
    PacketLayout,
    ParentCall,
    Refusal,
    canonical,
)
from veritas.research.parent_child_r98.packing import construct_layout
from veritas.research.parent_child_r98.shrinking_oracle import tuple_coefficient
from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r912.interaction_jet_point import packet_modes_at_jet_point
from veritas.research.parent_child_r912.routes import Route, contract_routed


@dataclass(frozen=True)
class ParentChildReconstructionResult:
    schema: str
    active_levels: int
    beta: Tuple[int, ...]
    child_group_count: int
    child_values: Tuple[object, ...]
    reconstructed: object
    parent_oracle: object
    reconstruction_equals_oracle: bool
    qualification: str
    nested_child_groups: int = 0
    second_level_kind: str = "none"


ChildContractor = Callable[[object, object], object]


def _jet_ring(precision: int, defining_polynomial: int, max_precision_bits: int) -> JetRing:
    return JetRing(
        ExtensionRing(
            precision,
            defining_polynomial,
            max_precision_bits=max_precision_bits,
        ),
        1,
    )


def reconstruct_parent_coefficient_one_level(
    parent: ParentCall,
    layout: PacketLayout,
    modes: ModeSet,
    beta: ExponentTuple,
    *,
    budget: Budget,
    child_contractor: Optional[ChildContractor] = None,
    require_shrink: bool = False,
) -> ParentChildReconstructionResult:
    """Return ``∏_g C_child_g`` and check against the independent parent oracle."""
    children = construct_children(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        _admitted=True,
        require_shrink=require_shrink,
    )
    verified = verify_children(
        parent,
        layout,
        modes,
        beta,
        children,
        budget=budget,
        _admitted=True,
    )
    certificate = modes.certificate
    ring = _jet_ring(
        certificate["precision"],
        parent.defining_polynomial,
        budget.policy.max_precision,
    )
    child_values = []
    for child, expected in zip(children, verified["values"]):
        if child_contractor is None:
            child_values.append(expected)
            continue
        actual = child_contractor(child, expected)
        if actual != expected:
            raise ValueError("child contractor disagrees with independent elimination")
        child_values.append(actual)
    reconstructed = ring.one
    for value in child_values:
        reconstructed = ring.mul(reconstructed, value)
    oracle = tuple_coefficient(parent, layout, modes, beta, budget=budget)
    return ParentChildReconstructionResult(
        schema="VERITAS_R913_PARENT_CHILD_RECONSTRUCT_V1",
        active_levels=1,
        beta=tuple(beta.values),
        child_group_count=len(children),
        child_values=tuple(child_values),
        reconstructed=reconstructed,
        parent_oracle=oracle,
        reconstruction_equals_oracle=reconstructed == oracle,
        qualification=(
            "one_level_product_of_verify_children_matches_shrinking_oracle; "
            "separator_packet_A_beta_is_distinct_quantity"
        ),
    )


def reconstruct_with_leaf_child_contractor(
    parent: ParentCall,
    layout: PacketLayout,
    modes: ModeSet,
    beta: ExponentTuple,
    *,
    budget: Budget,
    require_shrink: bool = False,
) -> ParentChildReconstructionResult:
    """Same as one level, but each ``C_child_g`` is obtained via ``leaf``."""

    def contractor(child, expected):
        return leaf(child.as_parent(parent), budget)

    return reconstruct_parent_coefficient_one_level(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        child_contractor=contractor,
        require_shrink=require_shrink,
    )


def reconstruction_report(result: ParentChildReconstructionResult) -> Dict[str, Any]:
    return {
        "schema": result.schema,
        "active_levels": result.active_levels,
        "beta": list(result.beta),
        "child_group_count": result.child_group_count,
        "reconstruction_equals_oracle": result.reconstruction_equals_oracle,
        "parent_child_reconstruction_proved": result.reconstruction_equals_oracle,
        "qualification": result.qualification,
    }


def modes_at_jet_point(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    max_points: int | None = None,
) -> Tuple[ModeSet, dict, int, Tuple[int, ...], Tuple[int, ...]]:
    """ModeSet at a jet point (for constructor / reconstruction paths)."""
    certificate, row_certificate, jet_index, node, zeta = packet_modes_at_jet_point(
        parent,
        layout,
        budget=budget,
        point_index=point_index,
        max_points=max_points,
    )
    return (
        ModeSet(layout.content_digest, canonical(certificate)),
        row_certificate,
        jet_index,
        node,
        zeta,
    )


def reconstruct_interaction_parent_at_jet_point(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    beta_values: Tuple[int, ...] | None = None,
    require_shrink: bool = True,
    child_contractor: Optional[ChildContractor] = None,
) -> ParentChildReconstructionResult:
    """Circulant / interaction parent: reconstruct ``C_parent(β)`` from child groups at a jet point."""
    modes, _row_certificate, _jet_index, _node, _zeta = modes_at_jet_point(
        parent, layout, budget=budget, point_index=point_index
    )
    mode_count = len(modes.certificate["modes"])
    if beta_values is None:
        beta_values = tuple(0 for _ in range(mode_count))
    if len(beta_values) != mode_count:
        raise ValueError("beta length must match jet-point mode count")
    beta = ExponentTuple(modes.content_digest, beta_values)
    return reconstruct_parent_coefficient_one_level(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        child_contractor=child_contractor,
        require_shrink=require_shrink,
    )


def project_ancestor_modes_onto_child(
    child: ChildGraph,
    ancestor_modes: ModeSet,
    child_layout: PacketLayout,
    call: ParentCall,
    *,
    budget: Budget,
) -> ModeSet:
    """Child modes for nesting: same packet deformation as ``construct_children``.

    Rebuilt geometric modes on the child layout can disagree with the packet
    recipes frozen at construction time.  Project the ancestor jet certificate
    onto the child's half-edge indices before grandchild products.
    """
    parent_edges = {row[1]: index for index, row in enumerate(child.edge_map)}
    ancestor = ancestor_modes.certificate
    group = child.group
    local = [
        [parent_edges[row], parent_edges[col], jet]
        for row, col, jet in ancestor["local"]
        if row in parent_edges and col in parent_edges
    ]
    cross = sorted(
        [parent_edges[row], parent_edges[col]]
        for row, col in ancestor["cross_pairs"]
        if row in parent_edges and col in parent_edges
    )
    projected_modes = []
    for mode in ancestor["modes"]:
        projected_modes.append(
            {
                **mode,
                "rows": [
                    [parent_edges[row], value]
                    for row, value in mode["rows"]
                    if row in parent_edges
                ],
                "column_terms": [
                    [parent_edges[col], term]
                    for col, term in mode["column_terms"]
                    if col in parent_edges
                ],
            }
        )
    weights = tuple(mode["weight"] for mode in projected_modes)
    tuple_count = weighted_count(
        weights,
        ancestor["precision"],
        budget.policy.max_tuples,
        enforce_policy_cap=False,
    )
    certificate = {
        "d3_certificate": child_layout.source,
        "node": ancestor["node"],
        "precision": ancestor["precision"],
        "jet_length": ancestor["jet_length"],
        "extension_degree": ancestor["extension_degree"],
        "irreducible_polynomial": ancestor["irreducible_polynomial"],
        "zeta": list(ancestor["zeta"]),
        "local": local,
        "cross_pairs": cross,
        "modes": projected_modes,
        "mode_tuple_count": tuple_count,
    }
    if (
        child.precision != ancestor["precision"]
        or child.node != ancestor["node"]
        or tuple(child.zeta) != tuple(ancestor["zeta"])
    ):
        raise ValueError("child point coordinates differ from ancestor jet certificate")
    result = ModeSet(child_layout.content_digest, canonical(certificate))
    verify_inherited_construction_modes(
        call,
        child_layout,
        result,
        budget=budget,
        inherited_point_precision=ancestor["precision"],
    )
    return result


def reconstruct_interaction_with_leaf_at_jet_point(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    beta_values: Tuple[int, ...] | None = None,
    require_shrink: bool = True,
) -> ParentChildReconstructionResult:
    modes, *_rest = modes_at_jet_point(parent, layout, budget=budget, point_index=point_index)
    mode_count = len(modes.certificate["modes"])
    if beta_values is None:
        beta_values = tuple(0 for _ in range(mode_count))
    beta = ExponentTuple(modes.content_digest, beta_values)
    base = reconstruct_with_leaf_child_contractor(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        require_shrink=require_shrink,
    )
    return ParentChildReconstructionResult(
        schema=base.schema,
        active_levels=2,
        beta=base.beta,
        child_group_count=base.child_group_count,
        child_values=base.child_values,
        reconstructed=base.reconstructed,
        parent_oracle=base.parent_oracle,
        reconstruction_equals_oracle=base.reconstruction_equals_oracle,
        nested_child_groups=0,
        second_level_kind="leaf_recheck",
        qualification="second_level_leaf_recheck; " + base.qualification,
    )


def _two_level_child_contractor(
    ancestor: ParentCall,
    layout: PacketLayout,
    *,
    ancestor_modes: ModeSet,
    parent_beta: ExponentTuple,
    budget: Budget,
    max_child_edges_for_recursion: int = 8,
) -> ChildContractor:
    """Recompute each child by grandchild product when the child graph is small enough."""

    nested_count = {"n": 0}

    def contractor(child, expected):
        call = child.as_parent(ancestor)
        if call.edge_count <= 1:
            actual = leaf(call, budget)
        elif call.edge_count > max_child_edges_for_recursion:
            actual = leaf(call, budget)
        else:
            try:
                child_layout = construct_layout(
                    call, a=layout.a, u=layout.u, budget=budget
                )
                child_modes = project_ancestor_modes_onto_child(
                    child,
                    ancestor_modes,
                    child_layout,
                    call,
                    budget=budget,
                )
                if len(parent_beta.values) != len(child_modes.certificate["modes"]):
                    raise ValueError("parent beta width must match ancestor mode count")
                child_beta = ExponentTuple(
                    child_modes.content_digest, parent_beta.values
                )
                nested = reconstruct_parent_coefficient_one_level(
                    call,
                    child_layout,
                    child_modes,
                    child_beta,
                    budget=budget,
                    require_shrink=False,
                )
                if nested.reconstructed == expected:
                    actual = nested.reconstructed
                    nested_count["n"] += 1
                else:
                    actual = leaf(call, budget)
            except (ValueError, Refusal):
                actual = leaf(call, budget)
        if actual != expected:
            raise ValueError("two-level child reconstruction disagrees with independent elimination")
        return actual

    contractor.nested_count = nested_count  # type: ignore[attr-defined]
    return contractor


def reconstruct_interaction_two_level_at_jet_point(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    beta_values: Tuple[int, ...] | None = None,
) -> ParentChildReconstructionResult:
    modes, _row_certificate, _jet_index, node, zeta = modes_at_jet_point(
        parent, layout, budget=budget, point_index=point_index
    )
    mode_count = len(modes.certificate["modes"])
    if beta_values is None:
        beta_values = tuple(0 for _ in range(mode_count))
    beta = ExponentTuple(modes.content_digest, beta_values)
    contractor = _two_level_child_contractor(
        parent, layout, ancestor_modes=modes, parent_beta=beta, budget=budget
    )
    result = reconstruct_parent_coefficient_one_level(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        child_contractor=contractor,
        require_shrink=True,
    )
    nested_groups = int(contractor.nested_count["n"])  # type: ignore[attr-defined]
    if nested_groups >= result.child_group_count:
        kind = "grandchild_product"
    elif nested_groups:
        kind = "grandchild_product_partial"
    else:
        kind = "leaf_recheck"
    return ParentChildReconstructionResult(
        schema=result.schema,
        active_levels=2,
        beta=result.beta,
        child_group_count=result.child_group_count,
        child_values=result.child_values,
        reconstructed=result.reconstructed,
        parent_oracle=result.parent_oracle,
        reconstruction_equals_oracle=result.reconstruction_equals_oracle,
        nested_child_groups=nested_groups,
        second_level_kind=kind,
        qualification=(
            f"second_level_{kind}; "
            "nested_C_child_equals_grandchild_product_when_ancestor_modes_are_projected_"
            "onto_constructed_child_half_edges; "
            "circulant_jet_point_1_beta0_succeeds_for_groups_0_through_31_only; "
            + result.qualification
        ),
    )


def wire_elimination_vs_parent_coefficient(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    elimination_budget: EliminationBudget | None = None,
    point_index: int = 1,
    beta_values: Tuple[int, ...] | None = None,
) -> Dict[str, Any]:
    """Record whether full wire elimination agrees with jet C_parent(beta) — expected false here."""
    elimination_budget = elimination_budget or EliminationBudget(max_width=20)
    wire = contract_routed(
        parent, route=Route.ELIMINATION, elimination_budget=elimination_budget
    )
    recon = reconstruct_interaction_parent_at_jet_point(
        parent,
        layout,
        budget=budget,
        point_index=point_index,
        beta_values=beta_values,
    )

    def _low_word(jet):
        if type(jet) in (list, tuple) and jet:
            head = jet[0]
            if type(head) in (list, tuple) and head:
                return head[0]
        return None

    wire_word = None
    if wire.get("status") == "PASS_EXACT_BOUNDED_WIDTH_ELIMINATION":
        wire_word = wire.get("result", [[None]])[0][0]
    coeff_word = _low_word(recon.parent_oracle)
    reconstructed_word = _low_word(recon.reconstructed)
    return {
        "schema": "VERITAS_R913_WIRE_VS_DEFORMATION_COEFF_V1",
        "wire_elimination_status": wire.get("status"),
        "wire_elimination_low_word": wire_word,
        "parent_coefficient_low_word": coeff_word,
        "reconstructed_low_word": reconstructed_word,
        "wire_elimination_equals_parent_coefficient": wire_word == coeff_word,
        "reconstruction_equals_oracle": recon.reconstruction_equals_oracle,
        "qualification": (
            "full_wire_contraction_and_jet_C_parent_beta_are_different_quantities; "
            "no_equality_claimed"
        ),
    }


def interaction_parent_child_reconstruction_report(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    beta_values: Tuple[int, ...] | None = None,
) -> Dict[str, Any]:
    """JSON-serializable block for harness / bench consumers."""
    modes, _row_certificate, jet_index, node, _zeta = modes_at_jet_point(
        parent, layout, budget=budget, point_index=point_index
    )
    result = reconstruct_interaction_parent_at_jet_point(
        parent,
        layout,
        budget=budget,
        point_index=point_index,
        beta_values=beta_values,
    )
    report = reconstruction_report(result)
    report["jet_point_index"] = jet_index
    report["jet_node"] = node
    report["wires"] = parent.edge_count
    report["mode_count"] = len(modes.certificate["modes"])
    report["qualification"] = (
        result.qualification
        + "; wire_elimination_is_separate_quantity_from_C_parent_beta"
    )
    return report
