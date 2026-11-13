"""Exact #SAT by residual-function equivalence (research prototype).

Groups partial assignments by the canonical residual CNF R(a) and accumulates
multiplicities. Memoization is exact: identical residuals share one sub-count.

This does not prove small residual-state complexity on hard instances; it
measures how many distinct residuals appear and validates against brute force.
"""
from __future__ import annotations

from dataclasses import dataclass

from veritas.core.cnf import CNF
from veritas.research.cnf_preprocess import count_preserving_preprocess


@dataclass(frozen=True)
class ResidualStats:
    distinct_residual_states: int
    cache_hits: int
    recursive_calls: int
    max_depth: int
    complexity_claim: bool = False


def _simplify_once(cnf: CNF, fixed: dict[int, bool]) -> CNF | None:
    clauses = [list(c) for c in cnf.clauses]
    for var, value in sorted(fixed.items()):
        next_clauses: list[list[int]] = []
        for clause in clauses:
            row: list[int] = []
            sat = False
            for lit in clause:
                v = abs(lit)
                if v in fixed:
                    if (lit > 0) == fixed[v]:
                        sat = True
                        break
                    continue
                row.append(lit)
            if sat:
                continue
            if not row:
                return None
            next_clauses.append(row)
        clauses = next_clauses
    remaining = [v for v in range(1, cnf.n + 1) if v not in fixed]
    mapping = {v: i + 1 for i, v in enumerate(remaining)}
    projected: list[list[int]] = []
    for clause in clauses:
        row = []
        for lit in clause:
            nv = mapping[abs(lit)]
            row.append(nv if lit > 0 else -nv)
        if row:
            projected.append(row)
    return CNF.from_lists(len(remaining), projected)


def residual_after_assignment(cnf: CNF, assignment: dict[int, bool]) -> CNF | None:
    """Residual problem R(a): simplify, unit-propagate, and reindex; None if UNSAT."""
    if any(v < 1 or v > cnf.n for v in assignment):
        raise ValueError('assignment variable out of range')
    once = _simplify_once(cnf, assignment)
    if once is None:
        return None
    canonical, report = count_preserving_preprocess(once)
    if report.empty_clause:
        return None
    return canonical


def _choose_var(cnf: CNF) -> int:
    appeared = {abs(lit) for c in cnf.clauses for lit in c}
    if not appeared:
        return 1
    return min(appeared)


def count_with_residual_memo(
    cnf: CNF,
    *,
    preprocess: bool = True,
) -> tuple[int, ResidualStats, dict]:
    """Exact #SAT via Shannon extension with residual CNF memoization."""
    if preprocess:
        cnf, prep = count_preserving_preprocess(cnf)
        if prep.empty_clause:
            return 0, ResidualStats(0, 0, 1, 0), {}
    else:
        prep = None
    memo: dict[str, int] = {}
    classifiers: dict[str, int] = {}
    cache_hits = 0
    calls = 0
    max_depth = 0

    def count(state: CNF, depth: int) -> int:
        nonlocal cache_hits, calls, max_depth
        calls += 1
        max_depth = max(max_depth, depth)
        fp = state.digest()
        classifiers[fp] = classifiers.get(fp, 0) + 1
        if fp in memo:
            cache_hits += 1
            return memo[fp]
        if not state.clauses:
            out = 1 << state.n
        else:
            v = _choose_var(state)
            total = 0
            for value in (False, True):
                child = residual_after_assignment(state, {v: value})
                if child is None:
                    continue
                total += count(child, depth + 1)
            out = total
        memo[fp] = out
        return out

    total = count(cnf, 0)
    stats = ResidualStats(
        distinct_residual_states=len(memo),
        cache_hits=cache_hits,
        recursive_calls=calls,
        max_depth=max_depth,
    )
    report = {
        'preprocess': prep.__dict__ if prep else None,
        'distinct_fingerprints': len(memo),
        'memo_reuse_ratio': cache_hits / calls if calls else 0.0,
        'contract': 'EXACT_RESIDUAL_MEMO_SHANNON',
        'complexity_claim': False,
    }
    return total, stats, report


def prefix_residual_table(
    cnf: CNF,
    prefix_vars: tuple[int, ...],
) -> list[dict]:
    """Enumerate 2^|prefix| partial assignments and bucket by residual fingerprint."""
    if any(v < 1 or v > cnf.n for v in prefix_vars):
        raise ValueError('prefix variables out of range')
    k = len(prefix_vars)
    buckets: dict[str, dict] = {}
    for mask in range(1 << k):
        assignment = {prefix_vars[i]: bool((mask >> i) & 1) for i in range(k)}
        residual = residual_after_assignment(cnf, assignment)
        if residual is None:
            key = '__UNSAT__'
            fp = key
        else:
            fp = residual.digest()
        row = buckets.setdefault(
            fp,
            {
                'fingerprint': fp,
                'multiplicity': 0,
                'example_assignment': assignment,
                'residual_n': 0 if residual is None else residual.n,
                'residual_clauses': 0 if residual is None else len(residual.clauses),
            },
        )
        row['multiplicity'] += 1
    return list(buckets.values())
