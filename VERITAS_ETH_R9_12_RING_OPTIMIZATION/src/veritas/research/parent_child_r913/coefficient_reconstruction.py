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
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, ModeSet, PacketLayout, ParentCall
from veritas.research.parent_child_r98.shrinking_oracle import tuple_coefficient


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
