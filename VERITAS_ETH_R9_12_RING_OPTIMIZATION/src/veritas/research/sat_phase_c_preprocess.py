"""Count-preserving Phase C preprocessing (engineering scaffold, not R9.4).

Applies **unit propagation only** (pure-literal dropped from this lane because it
is easy to break #SAT without branch accounting). Declared variable count ``n`` is
unchanged. UNSAT (empty clause) is detected explicitly.
"""
from __future__ import annotations

from typing import Any

from veritas.core.cnf import CNF
from veritas.research.sat_count_invariants import CountInvariantKind
from veritas.research.sat_preprocess_options import DEFAULT_PREPROCESS_OPTIONS, PreprocessOptions
from veritas.research.sat_work_accounting import DecompositionWorkLedger

COUNT_INVARIANT_BIJECTION: CountInvariantKind = "BIJECTION_ON_DECLARED_VARIABLES"


def _simplify_clause(clause: tuple[int, ...], assignment: dict[int, bool]) -> tuple[int, ...] | None:
    """Return simplified clause, None if tautology, () if falsified under partial assignment."""
    kept: list[int] = []
    for lit in clause:
        v = abs(lit)
        if v in assignment:
            val = assignment[v]
            if (lit > 0) == val:
                return None
            continue
        kept.append(lit)
    seen: set[int] = set()
    out: list[int] = []
    for lit in kept:
        if -lit in seen:
            return None
        if lit not in seen:
            seen.add(lit)
            out.append(lit)
    return tuple(sorted(out, key=lambda x: (abs(x), x)))


def _clauses_after_assignment(
    clauses: tuple[tuple[int, ...], ...],
    assignment: dict[int, bool],
) -> tuple[tuple[tuple[int, ...], ...], bool]:
    """Simplify all clauses; second return is False if empty clause appears."""
    simplified: list[tuple[int, ...]] = []
    for clause in clauses:
        s = _simplify_clause(clause, assignment)
        if s is None:
            continue
        if not s:
            return (), False
        simplified.append(s)
    dedup = tuple(sorted(set(simplified), key=lambda c: (len(c), c)))
    return dedup, True


def _unsat_detail(
    cnf: CNF,
    *,
    unit_steps: int,
    pure_steps: int,
    assignment: dict[int, bool],
) -> dict[str, Any]:
    return {
        "schema": "VERITAS_PHASE_C_PREPROCESS_V1",
        "status": "UNSAT",
        "count_invariant": COUNT_INVARIANT_BIJECTION,
        "unit_propagation_rounds": unit_steps,
        "pure_literal_eliminations": pure_steps,
        "assignment": dict(assignment),
        "clauses_before": len(cnf.clauses),
        "clauses_after": 0,
        "formula_digest_before": cnf.digest(),
        "formula_digest_after": cnf.digest(),
        "assignment_size": len(assignment),
        "theorem_backed": False,
    }


def _remove_tautology_clauses(
    clauses: tuple[tuple[int, ...], ...],
) -> tuple[tuple[tuple[int, ...], ...], int]:
    kept: list[tuple[int, ...]] = []
    dropped = 0
    for clause in clauses:
        bits = set(clause)
        if any(-lit in bits for lit in bits):
            dropped += 1
            continue
        kept.append(clause)
    return tuple(kept), dropped


def _one_safe_pure_literal(
    clauses: tuple[tuple[int, ...], ...],
    n: int,
    assignment: dict[int, bool],
) -> tuple[int, bool] | None:
    """Pure literal only when variable still appears in remaining clauses."""
    occ_pos = {v: 0 for v in range(1, n + 1)}
    occ_neg = {v: 0 for v in range(1, n + 1)}
    for clause in clauses:
        for lit in clause:
            v = abs(lit)
            if lit > 0:
                occ_pos[v] += 1
            else:
                occ_neg[v] += 1
    for v in range(1, n + 1):
        if v in assignment:
            continue
        active = occ_pos[v] + occ_neg[v]
        if active == 0:
            continue
        if occ_pos[v] > 0 and occ_neg[v] == 0:
            return v, True
        if occ_neg[v] > 0 and occ_pos[v] == 0:
            return v, False
    return None


def apply_phase_c_preprocess(
    cnf: CNF,
    *,
    w_old: int,
    options: PreprocessOptions = DEFAULT_PREPROCESS_OPTIONS,
) -> tuple[CNF, dict[str, Any], DecompositionWorkLedger]:
    """Bounded preprocessing; preserve ``cnf.n`` and #SAT when stages are count-safe."""
    assignment: dict[int, bool] = {}
    clauses = cnf.clauses
    unit_steps = 0
    pure_steps = 0
    tautology_dropped = 0
    if options.remove_tautology_clauses:
        clauses, tautology_dropped = _remove_tautology_clauses(clauses)

    changed = True
    while changed:
        changed = False
        clauses, ok = _clauses_after_assignment(clauses, assignment)
        if not ok:
            detail = _unsat_detail(cnf, unit_steps=unit_steps, pure_steps=pure_steps, assignment=assignment)
            ledger = DecompositionWorkLedger(
                name="phase_c_preprocess",
                w_old=w_old,
                w_transform=max(1, unit_steps + pure_steps),
                child_works=(),
                w_reconstruct=0,
                w_check=1,
                metadata={"phase": "preprocess", **detail},
            )
            return CNF(cnf.n, ()), detail, ledger

        if options.enable_unit_propagation:
            units = [c[0] for c in clauses if len(c) == 1]
        else:
            units = []
        conflict = False
        for lit in sorted(units, key=lambda x: (abs(x), x)):
            v = abs(lit)
            val = lit > 0
            if v in assignment:
                if assignment[v] != val:
                    conflict = True
                    break
                continue
            assignment[v] = val
            unit_steps += 1
            changed = True
        if conflict:
            detail = _unsat_detail(cnf, unit_steps=unit_steps, pure_steps=pure_steps, assignment=assignment)
            ledger = DecompositionWorkLedger(
                name="phase_c_preprocess",
                w_old=w_old,
                w_transform=max(1, unit_steps + pure_steps),
                child_works=(),
                w_reconstruct=0,
                w_check=1,
                metadata={"phase": "preprocess", **detail},
            )
            return CNF(cnf.n, ()), detail, ledger
        if changed:
            continue
        if (
            options.enable_safe_pure_literals
            and pure_steps < options.max_pure_literal_steps
        ):
            pick = _one_safe_pure_literal(clauses, cnf.n, assignment)
            if pick is not None:
                v, val = pick
                assignment[v] = val
                pure_steps += 1
                changed = True
                continue
        break

    clauses, ok = _clauses_after_assignment(clauses, assignment)
    if not ok:
        detail = _unsat_detail(cnf, unit_steps=unit_steps, pure_steps=pure_steps, assignment=assignment)
        out = CNF(cnf.n, ())
        status = "UNSAT"
    else:
        unit_clauses = tuple(
            (v if assignment[v] else -v,) for v in sorted(assignment)
        )
        merged = clauses + unit_clauses
        dedup = tuple(sorted(set(merged), key=lambda c: (len(c), c)))
        out = CNF(cnf.n, dedup)
        status = "REDUCED" if (unit_steps or pure_steps or tautology_dropped) else "UNCHANGED"

    detail = {
        "schema": "VERITAS_PHASE_C_PREPROCESS_V1",
        "status": status,
        "count_invariant": COUNT_INVARIANT_BIJECTION,
        "preprocess_options": options.to_dict(),
        "tautology_clauses_dropped": tautology_dropped,
        "unit_propagation_rounds": unit_steps,
        "pure_literal_eliminations": pure_steps,
        "clauses_before": len(cnf.clauses),
        "clauses_after": len(out.clauses),
        "formula_digest_before": cnf.digest(),
        "formula_digest_after": out.digest(),
        "assignment_size": len(assignment),
        "theorem_backed": False,
        "qualification": "engineering_count_preserving_on_declared_n",
    }
    w_transform = max(1, unit_steps + pure_steps)
    ledger = DecompositionWorkLedger(
        name="phase_c_preprocess",
        w_old=w_old,
        w_transform=w_transform,
        child_works=(),
        w_reconstruct=0,
        w_check=1 if status != "UNCHANGED" else 0,
        metadata={"phase": "preprocess", **detail},
    )
    return out, detail, ledger
