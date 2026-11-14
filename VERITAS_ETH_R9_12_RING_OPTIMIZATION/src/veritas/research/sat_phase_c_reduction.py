"""Phase C outer-reduction scaffold (research, not R9.4 theorem).

Bounded 3-CNF class + primal component split on variables. Registers ``q``
child work proxies in ``DecompositionWorkLedger`` for honest accounting; does
not prove count preservation or uniform (q, ρ) for arbitrary density.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from veritas.core.cnf import CNF
from veritas.research.adaptive_contract import adaptive_count
from veritas.research.sat_residual_equivalence import try_residual_equivalence_exact_count
from veritas.research.graph_decomposition import components
from veritas.research.sat_work_accounting import DecompositionWorkLedger, exponential_width_proxy
from veritas.research.source_cnf import SourceCNFNetwork
from veritas.solvers.count_dag import check_dag_count_certificate, make_dag_count_certificate
from veritas.solvers.reference import exhaustive_count, solve


@dataclass(frozen=True)
class PhaseCBounds:
    """Explicit caps for the scaffold reduction lane (not a complexity theorem)."""

    max_vars: int = 64
    max_clauses: int = 256
    max_encoded_edges: int = 50_000
    max_encoded_factors: int = 100_000
    max_components: int = 32
    max_exhaustive_vars_per_component: int = 16
    component_timeout_s: float = 4.0
    component_max_nodes: int = 80_000
    prefer_count_dag: bool = True
    max_count_dag_vars: int = 24
    count_dag_timeout_s: float = 3.0
    prefer_residual_equivalence: bool = True
    max_residual_equivalence_vars: int = 16
    max_residual_equivalence_clauses: int = 128

    def to_dict(self) -> dict:
        return {
            "max_vars": self.max_vars,
            "max_clauses": self.max_clauses,
            "max_encoded_edges": self.max_encoded_edges,
            "max_encoded_factors": self.max_encoded_factors,
            "max_components": self.max_components,
            "max_exhaustive_vars_per_component": self.max_exhaustive_vars_per_component,
            "component_timeout_s": self.component_timeout_s,
            "component_max_nodes": self.component_max_nodes,
            "prefer_count_dag": self.prefer_count_dag,
            "max_count_dag_vars": self.max_count_dag_vars,
            "count_dag_timeout_s": self.count_dag_timeout_s,
            "prefer_residual_equivalence": self.prefer_residual_equivalence,
            "max_residual_equivalence_vars": self.max_residual_equivalence_vars,
            "max_residual_equivalence_clauses": self.max_residual_equivalence_clauses,
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


def _component_local_cnf(cnf: CNF, comp: tuple[int, ...]) -> CNF:
    var_set = frozenset(comp)
    sub_clauses = _clauses_in_variable_set(cnf, var_set)
    if not comp:
        return CNF(0, ())
    order = tuple(sorted(comp))
    remap = {v: i + 1 for i, v in enumerate(order)}
    local = tuple(
        tuple(remap[abs(lit)] if lit > 0 else -remap[abs(lit)] for lit in clause)
        for clause in sub_clauses
    )
    return CNF(len(order), local)


def _count_component(
    sub: CNF,
    bounds: PhaseCBounds,
    *,
    task: Literal["count", "decision"],
) -> dict:
    """Exact child solve on a local sub-CNF (scaffold; not R9.4)."""
    if task == "decision":
        result = solve(
            sub,
            count=False,
            timeout_s=min(bounds.component_timeout_s, 30.0),
            max_nodes=bounds.component_max_nodes,
        )
        w_actual = result.nodes
        return {
            "task": "decision",
            "status": result.status,
            "model": result.model,
            "count": None,
            "w_child_actual": w_actual,
            "engine": "veritas_reference",
        }
    if (
        bounds.prefer_count_dag
        and sub.n <= bounds.max_count_dag_vars
    ):
        dag = make_dag_count_certificate(
            sub,
            timeout_s=min(bounds.count_dag_timeout_s, bounds.component_timeout_s),
        )
        if dag.status == "COUNT" and dag.certificate is not None and dag.count is not None:
            ok, _msg, verified, _n = check_dag_count_certificate(sub, dag.certificate)
            if ok and verified == dag.count:
                return {
                    "task": "count",
                    "status": "EXACT_COUNT",
                    "count": dag.count,
                    "w_child_actual": max(dag.nodes, 1),
                    "engine": "count_dag_certificate",
                    "dag_nodes": dag.nodes,
                    "dag_cache_hits": dag.cache_hits,
                }
    if bounds.prefer_residual_equivalence:
        residual = try_residual_equivalence_exact_count(
            sub,
            max_vars=bounds.max_residual_equivalence_vars,
            max_clauses=bounds.max_residual_equivalence_clauses,
        )
        if residual is not None:
            return residual
    if sub.n <= bounds.max_exhaustive_vars_per_component:
        count = exhaustive_count(sub)
        w_actual = 1 << sub.n
        return {
            "task": "count",
            "status": "EXACT_COUNT",
            "count": count,
            "w_child_actual": w_actual,
            "engine": "exhaustive_oracle",
        }
    out = adaptive_count(sub, timeout_s=min(bounds.component_timeout_s, 60.0))
    exec_stats = out.get("execution") or {}
    w_actual = int(
        exec_stats.get("work_assignments", 0) or exec_stats.get("nodes", 0) or 1
    )
    return {
        "task": "count",
        "status": out.get("status"),
        "count": int(out["count"]) if out.get("count") is not None else None,
        "w_child_actual": w_actual,
        "engine": out.get("engine"),
    }


def _recombine_count(child_results: list[dict]) -> tuple[Optional[int], str]:
    product = 1
    for row in child_results:
        if row.get("status") not in ("EXACT_COUNT", "COUNT_RESIDUE"):
            return None, "incomplete_child_counts"
        c = row.get("count")
        if c is None:
            return None, "missing_child_count"
        product *= int(c)
    return product, "product_of_independent_components_scaffold"


def _recombine_decision(child_results: list[dict]) -> tuple[str, str]:
    if any(row.get("status") == "UNSAT" for row in child_results):
        return "UNSAT", "component_unsat"
    if all(row.get("status") == "SAT" for row in child_results):
        return "SAT", "all_components_sat"
    return "UNKNOWN", "incomplete_child_decision"


def plan_primal_component_split(
    cnf: CNF,
    encoded: Optional[SourceCNFNetwork],
    *,
    bounds: PhaseCBounds = DEFAULT_PHASE_C_BOUNDS,
    w_old: int,
    task: Literal["count", "decision"] = "count",
    partition_certificate: Optional[dict[str, Any]] = None,
) -> tuple[dict, Optional[DecompositionWorkLedger]]:
    """Split disconnected CNF components; solve each child and log actual work."""
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

    if partition_certificate is None:
        partition_certificate = {"valid": False, "reason": "certificate_not_supplied"}
    partition_proved = bool(partition_certificate.get("valid"))

    child_works: list[int] = []
    child_specs = []
    child_results: list[dict] = []
    for comp in comps:
        var_set = frozenset(comp)
        sub_clauses = _clauses_in_variable_set(cnf, var_set)
        sub = _component_local_cnf(cnf, comp)
        w_proxy = exponential_width_proxy(min(len(comp), 24))
        solved = _count_component(sub, bounds, task=task)
        w_actual = int(solved.get("w_child_actual") or w_proxy)
        child_works.append(w_actual)
        child_results.append(solved)
        child_specs.append(
            {
                "variables": list(comp),
                "clause_count": len(sub_clauses),
                "local_n": sub.n,
                "w_child_proxy": w_proxy,
                "w_child_actual": w_actual,
                "child_solve": solved,
                "count_preserving_reduction_proved": False,
                "partition_certificate_valid": partition_proved,
                "count_invariant": (
                    "PRODUCT_OVER_PRIMAL_COMPONENTS"
                    if partition_proved and task == "count"
                    else None
                ),
            }
        )

    if task == "count":
        recombined_value, recombined_rule = _recombine_count(child_results)
    else:
        status, recombined_rule = _recombine_decision(child_results)
        recombined_value = None
        recombined_status = status

    w_transform = len(comps)
    w_reconstruct = sum(child_works)
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
            "outer_reduction_r94": (
                "PARTIAL_PRIMAL_PRODUCT" if partition_proved else "NOT_IMPLEMENTED"
            ),
            "partition_certificate_valid": partition_proved,
            "task": task,
            "recombined_rule": recombined_rule,
            "qualification": "primal_split_with_component_exact_solves_scaffold",
        },
    )
    summary = {
        "schema": "VERITAS_PHASE_C_SPLIT_V1",
        "status": "SCAFFOLD_COMPONENT_SPLIT",
        "task": task,
        "q": len(comps),
        "components": child_specs,
        "w_new_proxy": ledger.w_new,
        "speedup_ratio_proxy": ledger.speedup_ratio(),
        "recombined": (
            {"count": recombined_value, "rule": recombined_rule}
            if task == "count"
            else {"status": recombined_status, "rule": recombined_rule}
        ),
        "bounds": bounds.to_dict(),
        "theorem_backed": False,
        "partition_certificate_valid": partition_proved,
    }
    return summary, ledger


def phase_c_refusal_if_out_of_bounds(cnf: CNF, bounds: PhaseCBounds) -> Optional[dict]:
    try:
        admit_phase_c_class(cnf, bounds)
    except ValueError as exc:
        return {"status": "REFUSED_PHASE_C_BOUNDS", "reason": str(exc), "bounds": bounds.to_dict()}
    return None
