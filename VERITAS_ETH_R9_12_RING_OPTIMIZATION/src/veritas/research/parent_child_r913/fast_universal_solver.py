"""Fast universal exact solver for bounded interaction parents at a jet point.

On circulant / interaction fixtures this path is the production default:

1. **Parent-child product** — ``∏_g C_child_g(β)`` with construct+verify (cached when possible).
2. **Tuple oracle** — same value via independent parent coefficient (cross-check only).

Full **wire elimination** is a different quantity and is optional (slow). No ETH or
source-qualification claim.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence, Tuple

from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r912.routes import Route, contract_routed
from veritas.research.parent_child_r98.model import (
    Budget,
    ChildGraph,
    ExponentTuple,
    PacketLayout,
    ParentCall,
)
from veritas.research.parent_child_r913.coefficient_reconstruction import (
    ParentChildReconstructionResult,
    modes_at_jet_point,
    reconstruct_parent_coefficient_one_level,
    wire_elimination_vs_parent_coefficient,
)


class UniversalSolveMethod(str, Enum):
    PARENT_CHILD_PRODUCT = "parent_child_product"
    WIRE_ELIMINATION = "wire_elimination"


@dataclass(frozen=True)
class UniversalSolveResult:
    method: UniversalSolveMethod
    reconstructed: object
    parent_oracle: object
    reconstruction_equals_oracle: bool
    child_group_count: int
    beta: Tuple[int, ...]
    elapsed_seconds: float
    qualification: str


def fast_universal_parent_jet_solve(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    beta_values: Tuple[int, ...] | None = None,
    children: Sequence[ChildGraph] | None = None,
    verified: Mapping[str, Any] | None = None,
) -> UniversalSolveResult:
    """Fast exact ``C_parent(β)`` at a jet point on bounded interaction parents."""
    t0 = time.perf_counter()
    modes, *_ = modes_at_jet_point(parent, layout, budget=budget, point_index=point_index)
    mode_count = len(modes.certificate["modes"])
    if beta_values is None:
        beta_values = tuple(0 for _ in range(mode_count))
    if len(beta_values) != mode_count:
        raise ValueError("beta length must match jet-point mode count")
    beta = ExponentTuple(modes.content_digest, beta_values)
    result = reconstruct_parent_coefficient_one_level(
        parent,
        layout,
        modes,
        beta,
        budget=budget,
        require_shrink=True,
        children=children,
        verified=verified,
    )
    elapsed = time.perf_counter() - t0
    return UniversalSolveResult(
        method=UniversalSolveMethod.PARENT_CHILD_PRODUCT,
        reconstructed=result.reconstructed,
        parent_oracle=result.parent_oracle,
        reconstruction_equals_oracle=result.reconstruction_equals_oracle,
        child_group_count=result.child_group_count,
        beta=tuple(result.beta),
        elapsed_seconds=elapsed,
        qualification=result.qualification,
    )


def optional_wire_elimination_diagnostic(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    elimination_budget: EliminationBudget | None = None,
    point_index: int = 1,
    beta_values: Tuple[int, ...] | None = None,
    reconstruction: ParentChildReconstructionResult | None = None,
) -> dict[str, object]:
    """Slow wire elimination vs ``C_parent(β)``; use only when explicitly needed."""
    elimination_budget = elimination_budget or EliminationBudget(max_width=20)
    return wire_elimination_vs_parent_coefficient(
        parent,
        layout,
        budget=budget,
        elimination_budget=elimination_budget,
        point_index=point_index,
        beta_values=beta_values,
        reconstruction=reconstruction,
    )


def contract_universal_auto(
    parent: ParentCall,
    layout: PacketLayout,
    *,
    budget: Budget,
    point_index: int = 1,
    prefer_parent_child: bool = True,
    elimination_budget: EliminationBudget | None = None,
) -> dict[str, object]:
    """Route.AUTO semantics for jet-point coefficient: parent-child first, else elimination."""
    if prefer_parent_child and parent.edge_count <= budget.policy.max_edges:
        try:
            solved = fast_universal_parent_jet_solve(
                parent, layout, budget=budget, point_index=point_index
            )
            if solved.reconstruction_equals_oracle:
                return {
                    "status": "PASS_FAST_UNIVERSAL_PARENT_CHILD",
                    "method": solved.method.value,
                    "result": solved.reconstructed,
                    "reconstruction_equals_oracle": True,
                    "elapsed_seconds": solved.elapsed_seconds,
                    "child_group_count": solved.child_group_count,
                }
        except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError):
            pass
    elimination_budget = elimination_budget or EliminationBudget(max_width=20)
    wire = contract_routed(
        parent,
        route=Route.ELIMINATION,
        elimination_budget=elimination_budget,
    )
    return {
        "status": wire.get("status"),
        "method": UniversalSolveMethod.WIRE_ELIMINATION.value,
        "result": wire.get("result"),
        "reconstruction_equals_oracle": False,
        "elimination_width": wire.get("elimination_width"),
        "route_selection": wire.get("route_selection"),
    }
