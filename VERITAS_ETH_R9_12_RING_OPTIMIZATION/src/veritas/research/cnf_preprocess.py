"""Count-preserving CNF simplifications for exact model counting."""
from __future__ import annotations

from dataclasses import dataclass

from veritas.core.cnf import CNF


@dataclass(frozen=True)
class PreprocessReport:
    unit_propagations: int
    tautologies_removed: int
    duplicate_clauses_removed: int
    empty_clause: bool
    fixed_assignments: tuple[tuple[int, bool], ...]
    remaining_variables: tuple[int, ...]
    contract: str


def _apply_assignment(clauses: list[list[int]], var: int, value: bool) -> list[list[int]] | None:
    simplified: list[list[int]] = []
    for clause in clauses:
        seen: set[int] = set()
        new_clause: list[int] = []
        satisfied = False
        for lit in clause:
            v = abs(lit)
            if v == var:
                if (lit > 0) == value:
                    satisfied = True
                    break
                continue
            if v in seen:
                continue
            seen.add(v)
            new_clause.append(lit)
        if satisfied:
            continue
        if not new_clause:
            return None
        simplified.append(new_clause)
    return simplified


def _reindex(clauses: list[list[int]], fixed: dict[int, bool], n: int) -> tuple[CNF, tuple[int, ...]]:
    remaining = [v for v in range(1, n + 1) if v not in fixed]
    mapping = {v: i + 1 for i, v in enumerate(remaining)}
    projected: list[list[int]] = []
    for clause in clauses:
        new: list[int] = []
        seen: set[int] = set()
        for lit in clause:
            v = abs(lit)
            if v in fixed:
                if (lit > 0) == fixed[v]:
                    new = []
                    break
                continue
            nv = mapping[v]
            signed = nv if lit > 0 else -nv
            if signed in seen:
                continue
            seen.add(signed)
            new.append(signed)
        if new:
            projected.append(new)
    return CNF.from_lists(len(remaining), projected), tuple(remaining)


def count_preserving_preprocess(cnf: CNF) -> tuple[CNF, PreprocessReport]:
    """Unit propagation, tautology and duplicate removal with variable reindexing."""
    clauses = [list(c) for c in cnf.clauses]
    taut = dup = units = 0
    fixed: dict[int, bool] = {}
    changed = True
    while changed:
        changed = False
        unique: list[list[int]] = []
        keys: set[tuple[int, ...]] = set()
        for clause in clauses:
            lits = set(clause)
            if any(-lit in lits for lit in lits):
                taut += 1
                changed = True
                continue
            ordered = tuple(sorted(clause, key=lambda lit: (abs(lit), lit)))
            if ordered in keys:
                dup += 1
                changed = True
                continue
            keys.add(ordered)
            unique.append(list(ordered))
        clauses = unique
        while True:
            unit = next((c[0] for c in clauses if len(c) == 1), None)
            if unit is None:
                break
            var = abs(unit)
            value = unit > 0
            clauses = _apply_assignment(clauses, var, value)
            if clauses is None:
                return (
                    cnf,
                    PreprocessReport(
                        units,
                        taut,
                        dup,
                        True,
                        tuple(fixed.items()),
                        (),
                        'COUNT_PRESERVING_UNSAT',
                    ),
                )
            fixed[var] = value
            units += 1
            changed = True
    simplified, remaining = _reindex(clauses, fixed, cnf.n)
    return (
        simplified,
        PreprocessReport(
            units,
            taut,
            dup,
            False,
            tuple(fixed.items()),
            remaining,
            'COUNT_PRESERVING_CONDITIONING',
        ),
    )
