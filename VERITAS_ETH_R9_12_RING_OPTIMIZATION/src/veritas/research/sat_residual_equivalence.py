"""Residual-function equivalence counting (research scaffold).

Partial assignments ``a`` and ``b`` are equivalent when the residual CNF ``R(a)``
equals ``R(b)`` on the remaining scope. Count by summing

    multiplicity(R) * #SAT(R)

instead of enumerating full assignments. This generalizes the idea behind
``veritas.solvers.count_dag`` (canonical residual states) with explicit branch
multiplicities for pedagogy and R9.13 junction experiments.

No universal speedup or polynomial bound is claimed.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from veritas.core.cnf import CNF
from veritas.solvers.count_dag import _components, _norm, _restrict, _root_state
from veritas.solvers.reference import exhaustive_count

State = tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]


def state_to_local_cnf(state: State) -> CNF:
    scope, clauses = state
    if not scope:
        return CNF(0, clauses)
    order = tuple(sorted(scope))
    remap = {v: i + 1 for i, v in enumerate(order)}
    local = tuple(
        tuple(remap[abs(lit)] if lit > 0 else -remap[abs(lit)] for lit in clause)
        for clause in clauses
    )
    return CNF(len(order), local)


def residual_state_key(state: State) -> tuple[Any, ...]:
    """Canonical key for ``R(partial assignment)``."""
    scope, clauses = state
    return (scope, _norm(clauses))


def restrict_partial(state: State, variable: int, value: bool) -> State:
    return _restrict(state, variable, value)


def count_residual_state(state: State, *, memo: dict[tuple[Any, ...], int] | None = None) -> int:
    """Exact #SAT on declared scope of ``state`` (exponential reference)."""
    memo = memo if memo is not None else {}
    key = residual_state_key(state)
    if key in memo:
        return memo[key]
    scope, clauses = state
    if any(not c for c in clauses):
        memo[key] = 0
        return 0
    if not clauses:
        memo[key] = 1 << len(scope)
        return memo[key]
    used = {abs(lit) for c in clauses for lit in c}
    free = len(scope) - len({v for v in scope if v in used})
    if free:
        child = (tuple(v for v in scope if v in used), clauses)
        count = count_residual_state(child, memo=memo)
        memo[key] = count * (1 << free)
        return memo[key]
    comps = _components(clauses)
    if len(comps) > 1:
        prod = 1
        for comp in comps:
            prod *= count_residual_state(comp, memo=memo)
        memo[key] = prod
        return prod
    local = state_to_local_cnf(state)
    memo[key] = exhaustive_count(local, max_vars=local.n)
    return memo[key]


def compression_metrics_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Subset of fields for universal JSON and micro-benchmarks."""
    return {
        "schema": "VERITAS_RESIDUAL_COMPRESSION_METRICS_V1",
        "status": report.get("status"),
        "distinct_residual_classes": report.get("distinct_residual_classes"),
        "full_assignment_branches": report.get("full_assignment_branches"),
        "compression_ratio_branches_over_classes": report.get(
            "compression_ratio_branches_over_classes"
        ),
        "agreement_with_exhaustive": report.get("agreement"),
        "reason": report.get("reason"),
    }


def admit_residual_equivalence_count(
    cnf: CNF,
    *,
    max_vars: int = 16,
    max_clauses: int = 128,
) -> dict[str, Any] | None:
    """Return refusal dict when unsafe to run; else None."""
    if cnf.n > max_vars:
        return {
            "status": "REFUSED_UNSAFE",
            "reason": f"n={cnf.n} exceeds max_vars={max_vars}",
        }
    if len(cnf.clauses) > max_clauses:
        return {
            "status": "REFUSED_UNSAFE",
            "reason": f"m={len(cnf.clauses)} exceeds max_clauses={max_clauses}",
        }
    return None


def try_residual_equivalence_exact_count(
    cnf: CNF,
    *,
    max_vars: int = 16,
    max_clauses: int = 128,
) -> dict[str, Any] | None:
    """Fail-closed: return child-style solve dict only when oracle agrees."""
    refusal = admit_residual_equivalence_count(
        cnf, max_vars=max_vars, max_clauses=max_clauses
    )
    if refusal:
        return None
    report = count_by_residual_equivalence(cnf)
    if report.get("status") != "EXACT_COUNT" or not report.get("agreement"):
        return None
    classes = int(report.get("distinct_residual_classes") or 1)
    branches = int(report.get("full_assignment_branches") or (1 << cnf.n))
    return {
        "task": "count",
        "status": "EXACT_COUNT",
        "count": report["count"],
        "w_child_actual": max(classes, 1),
        "engine": "residual_equivalence",
        "residual_compression": compression_metrics_from_report(report),
        "w_proxy_branches_skipped": branches,
    }


def probe_residual_compression(
    cnf: CNF,
    *,
    max_vars: int = 16,
    max_clauses: int = 128,
) -> dict[str, Any]:
    """Universal count-mode probe; never claims speedup."""
    refusal = admit_residual_equivalence_count(
        cnf, max_vars=max_vars, max_clauses=max_clauses
    )
    if refusal:
        return {
            "schema": "VERITAS_RESIDUAL_COMPRESSION_PROBE_V1",
            "status": "REFUSED",
            "reason": refusal.get("reason"),
            "distinct_residual_classes": None,
            "full_assignment_branches": None,
            "compression_ratio_branches_over_classes": None,
            "agreement_with_exhaustive": None,
            "universal_speedup_claimed": False,
            "theorem_backed": False,
            "qualification": "research_probe_not_primary_solver",
        }
    report = count_by_residual_equivalence(cnf)
    metrics = compression_metrics_from_report(report)
    return {
        "schema": "VERITAS_RESIDUAL_COMPRESSION_PROBE_V1",
        "status": report.get("status", "UNKNOWN"),
        "count": report.get("count"),
        "oracle_exhaustive_count": report.get("oracle_exhaustive_count"),
        "distinct_residual_classes": metrics.get("distinct_residual_classes"),
        "full_assignment_branches": metrics.get("full_assignment_branches"),
        "compression_ratio_branches_over_classes": metrics.get(
            "compression_ratio_branches_over_classes"
        ),
        "agreement_with_exhaustive": metrics.get("agreement_with_exhaustive"),
        "universal_speedup_claimed": False,
        "theorem_backed": False,
        "qualification": "research_probe_not_primary_solver",
    }


def count_by_residual_equivalence(
    cnf: CNF,
    *,
    branch_order: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    """Count via equivalence classes of residuals after fixing ``branch_order`` prefix.

    For each prefix depth ``d``, buckets partial assignments by ``R`` and records
  multiplicity. Final count = sum multiplicity * count_residual(R).
    """
    if cnf.n > 16:
        return {
            "schema": "VERITAS_RESIDUAL_EQUIVALENCE_COUNT_V1",
            "status": "REFUSED",
            "reason": "n > 16 cap for research scaffold",
        }
    root = _root_state(cnf)
    order = (
        tuple(range(1, cnf.n + 1))
        if branch_order is None
        else tuple(branch_order)
    )
    full = 1 << len(order) if order else 1

    # Leaf bucket after fixing all variables in order (may have extra free vars)
    classes: dict[tuple[Any, ...], int] = defaultdict(int)

    def recurse(state: State, depth: int, multiplicity: int) -> None:
        if depth >= len(order):
            key = residual_state_key(state)
            classes[key] += multiplicity
            return
        var = order[depth]
        scope = state[0]
        if var not in scope:
            recurse(state, depth + 1, multiplicity)
            return
        for value in (False, True):
            child = restrict_partial(state, var, value)
            recurse(child, depth + 1, multiplicity)

    recurse(root, 0, 1)

    memo: dict[tuple[Any, ...], int] = {}
    total = 0
    class_rows: list[dict[str, Any]] = []
    for key, mult in sorted(classes.items(), key=lambda x: (-x[1], str(x[0]))):
        scope, clauses = key
        state = (scope, clauses)
        sub = count_residual_state(state, memo=memo)
        total += mult * sub
        class_rows.append(
            {
                "multiplicity": mult,
                "residual_scope": list(scope),
                "residual_clause_count": len(clauses),
                "residual_count": sub,
                "contribution": mult * sub,
            }
        )

    oracle = exhaustive_count(cnf, max_vars=cnf.n)
    agreement = total == oracle
    return {
        "schema": "VERITAS_RESIDUAL_EQUIVALENCE_COUNT_V1",
        "status": "EXACT_COUNT" if agreement else "INCONCLUSIVE_INVARIANT_FAILURE",
        "count": total if agreement else None,
        "count_computed": total,
        "oracle_exhaustive_count": oracle,
        "agreement": agreement,
        "branch_order": list(order),
        "distinct_residual_classes": len(classes),
        "full_assignment_branches": full,
        "compression_ratio_branches_over_classes": (
            full / len(classes) if classes else None
        ),
        "classes": class_rows,
        "theorem_backed": False,
        "universal_speedup_claimed": False,
        "qualification": "state_merge_by_residual_key_not_complexity_theorem",
    }


def xor_system_solution_count(n: int, rank: int, *, consistent: bool = True) -> int:
    """Demonstration: #solutions = 2^{n-rank} when consistent (GF(2) linear systems)."""
    if not consistent:
        return 0
    return 1 << max(0, n - rank)
