"""Phase C outer-reduction scaffold (research, not R9.4 theorem).

Bounded 3-CNF class + primal component split on variables. Registers ``q``
child work proxies in ``DecompositionWorkLedger`` for honest accounting; does
not prove count preservation or uniform (q, ρ) for arbitrary density.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from veritas.core.cnf import CNF
from veritas.research.graph_decomposition import components
from veritas.research.sat_work_accounting import DecompositionWorkLedger, exponential_width_proxy
from veritas.research.source_cnf import SourceCNFNetwork


@dataclass(frozen=True)
class PhaseCBounds:
    """Explicit caps for the scaffold reduction lane (not a complexity theorem)."""

    max_vars: int = 64
    max_clauses: int = 256
    max_encoded_edges: int = 50_000
    max_encoded_factors: int = 100_000
    max_components: int = 32

    def to_dict(self) -> dict:
        return {
            "max_vars": self.max_vars,
            "max_clauses": self.max_clauses,
            "max_encoded_edges": self.max_encoded_edges,
            "max_encoded_factors": self.max_encoded_factors,
            "max_components": self.max_components,
        }


DEFAULT_PHASE_C_BOUNDS = PhaseCBounds()


def admit_phase_c_class(cnf: CNF, bounds: PhaseCBounds = DEFAULT_PHASE_C_BOUNDS) -> None:
    if cnf.n > bounds.max_vars:
        raise ValueError(f"Phase C scaffold: n={cnf.n} exceeds max_vars={bounds.max_vars}")
    if len(cnf.clauses) > bounds.max_clauses:
        raise ValueError(
            f"Phase C scaffold: m={len(cnf.clauses)} exceeds max_clauses={bounds.max_clauses}"
        )


def _cnf_primal_graph(cnf: CNF) -> dict[int, set[int]]:
    graph = {v: set() for v in range(1, cnf.n + 1)}
    for clause in cnf.clauses:
        verts = {abs(lit) for lit in clause}
        for v in verts:
            graph[v].update(verts - {v})
    return graph


def _clauses_in_variable_set(cnf: CNF, variables: frozenset[int]) -> tuple[tuple[int, ...], ...]:
    out = []
    for clause in cnf.clauses:
        if {abs(lit) for lit in clause} <= variables:
            out.append(clause)
    return tuple(out)


def plan_primal_component_split(
    cnf: CNF,
    encoded: Optional[SourceCNFNetwork],
    *,
    bounds: PhaseCBounds = DEFAULT_PHASE_C_BOUNDS,
    w_old: int,
) -> tuple[dict, Optional[DecompositionWorkLedger]]:
    """Split disconnected CNF components; ledger child works are width proxies only."""
    admit_phase_c_class(cnf, bounds)
    if encoded is not None:
        net = encoded.network
        if net.edges > bounds.max_encoded_edges:
            raise ValueError("encoded edges exceed Phase C cap")
        if len(net.factors) > bounds.max_encoded_factors:
            raise ValueError("encoded factors exceed Phase C cap")

    graph = _cnf_primal_graph(cnf)
    comps = components(graph)
    if len(comps) > bounds.max_components:
        raise ValueError(f"component count {len(comps)} exceeds max_components")

    child_works: list[int] = []
    child_specs = []
    for comp in comps:
        var_set = frozenset(comp)
        sub_clauses = _clauses_in_variable_set(cnf, var_set)
        # Work proxy: exponential in |comp|, capped like global ledger convention.
        w_child = exponential_width_proxy(min(len(comp), 24))
        child_works.append(w_child)
        child_specs.append(
            {
                "variables": list(comp),
                "clause_count": len(sub_clauses),
                "w_child_proxy": w_child,
                "count_preserving_reduction_proved": False,
            }
        )

    w_transform = len(comps)  # bookkeeping split overhead proxy
    w_reconstruct = len(comps)  # recombine / multiply counts proxy (not implemented)
    w_check = len(comps)

    ledger = DecompositionWorkLedger(
        name="phase_c_primal_component_split",
        w_old=w_old,
        w_transform=w_transform,
        child_works=tuple(child_works),
        w_reconstruct=w_reconstruct,
        w_check=w_check,
        metadata={
            "phase": "phase_c_scaffold",
            "q": len(comps),
            "bounds": bounds.to_dict(),
            "children": child_specs,
            "outer_reduction_r94": "NOT_IMPLEMENTED",
            "qualification": "primal_split_work_proxy_only",
        },
    )
    summary = {
        "schema": "VERITAS_PHASE_C_SPLIT_V1",
        "status": "SCAFFOLD_COMPONENT_SPLIT",
        "q": len(comps),
        "components": child_specs,
        "w_new_proxy": ledger.w_new,
        "speedup_ratio_proxy": ledger.speedup_ratio(),
        "bounds": bounds.to_dict(),
        "theorem_backed": False,
    }
    return summary, ledger


def phase_c_refusal_if_out_of_bounds(cnf: CNF, bounds: PhaseCBounds) -> Optional[dict]:
    try:
        admit_phase_c_class(cnf, bounds)
    except ValueError as exc:
        return {"status": "REFUSED_PHASE_C_BOUNDS", "reason": str(exc), "bounds": bounds.to_dict()}
    return None
