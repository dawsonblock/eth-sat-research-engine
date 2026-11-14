"""Count-preserving XOR simplifications before mixed CNF+XOR counting."""
from __future__ import annotations

from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation


def _rewrite_lit(lit: int, pivot: int, rep: int, rhs: int) -> int:
    if abs(lit) != pivot:
        return lit
    pos = lit > 0
    if rhs:
        pos = not pos
    return rep if pos else -rep


def apply_xor_unary_units(
    cnf: CNF, equations: tuple[XorEquation, ...]
) -> tuple[CNF, tuple[XorEquation, ...], dict]:
    """Fold single-variable XOR equations x_v = rhs into unit literals."""
    eqs = list(equations)
    units: list[tuple[int, bool]] = []
    remaining: list[XorEquation] = []
    for eq in eqs:
        if len(eq.variables) == 1:
            units.append((eq.variables[0], bool(eq.rhs & 1)))
        else:
            remaining.append(eq)
    if not units:
        return cnf, equations, {'unary_units': 0}
    unit_map = dict(units)
    clauses: list[list[int]] = []
    for cl in cnf.clauses:
        row: list[int] = []
        ok = True
        for lit in cl:
            v = abs(lit)
            if v in unit_map:
                if unit_map[v] != (lit > 0):
                    ok = False
                    break
                continue
            row.append(lit)
        if not ok:
            return CNF.from_lists(cnf.n, [[1], [-1]]), tuple(remaining), {'unary_units': len(units), 'empty_clause': True}
        if row:
            clauses.append(row)
    return (
        CNF.from_lists(cnf.n, clauses),
        tuple(remaining),
        {'unary_units': len(units)},
    )


def substitute_binary_xor(
    cnf: CNF, equations: tuple[XorEquation, ...], *, require_pivot_in_clauses: bool = True
) -> tuple[CNF, tuple[XorEquation, ...], dict]:
    """Replace x_a with x_b or its negation when an equation is exactly a XOR b = rhs.

    Substitution is count-preserving only when the eliminated variable appears in the
    CNF; otherwise the XOR link would be dropped from the problem.
    """
    clause_vars = {abs(lit) for c in cnf.clauses for lit in c}
    cnf, equations, unary = apply_xor_unary_units(cnf, equations)
    if unary.get('empty_clause'):
        return cnf, equations, {'changed': True, 'binary_substitutions': 0, **unary}
    eqs = list(equations)
    clauses = [list(c) for c in cnf.clauses]
    removed: set[int] = set()
    report: dict = {'binary_substitutions': 0, 'removed_variables': [], 'skipped_safe': 0, **unary}
    changed = True
    while changed:
        changed = False
        for i, eq in enumerate(list(eqs)):
            if len(eq.variables) != 2:
                continue
            a, b = sorted(eq.variables)
            if a in removed or b in removed:
                continue
            if require_pivot_in_clauses and a not in clause_vars:
                report['skipped_safe'] += 1
                continue
            rhs = eq.rhs & 1
            clauses = [[_rewrite_lit(lit, a, b, rhs) for lit in cl] for cl in clauses]
            removed.add(a)
            clause_vars.discard(a)
            eqs.pop(i)
            report['binary_substitutions'] += 1
            report['removed_variables'].append(a)
            changed = True
            break
    if not report['binary_substitutions'] and not unary.get('unary_units'):
        return cnf, equations, {'changed': False, **report}
    keep = [v for v in range(1, cnf.n + 1) if v not in removed]
    mapping = {old: idx for idx, old in enumerate(keep, start=1)}
    new_clauses: list[list[int]] = []
    for cl in clauses:
        row: list[int] = []
        for lit in cl:
            v = abs(lit)
            if v in removed:
                continue
            nv = mapping[v]
            row.append(nv if lit > 0 else -nv)
        if row:
            new_clauses.append(row)
    surviving: list[XorEquation] = []
    for eq in eqs:
        vars2 = tuple(mapping[v] for v in sorted(eq.variables) if v not in removed)
        if len(vars2) >= 2 and len(set(vars2)) == len(vars2):
            surviving.append(XorEquation(vars2, eq.rhs))
        elif len(vars2) == 1:
            surviving.append(XorEquation(vars2, eq.rhs))
    out_cnf = CNF.from_lists(len(keep), new_clauses)
    out_cnf, surviving_eqs, unary2 = apply_xor_unary_units(out_cnf, tuple(surviving))
    report.update(unary2)
    return out_cnf, surviving_eqs, {'changed': True, **report}


def try_xor_algebraic_reduce(
    cnf: CNF,
    equations: tuple[XorEquation, ...],
    *,
    inner_count=None,
    **kwargs,
) -> dict | None:
    """Binary XOR substitution then delegate to structure / pure-XOR paths."""
    from veritas.research.cnf_structure import structure_aware_count
    from veritas.research.gf2_xor_count import count_pure_xor

    reduced, eqs, sub = substitute_binary_xor(cnf, equations)
    if not sub.get('changed'):
        return None
    if sub.get('empty_clause'):
        return {
            'status': 'EXACT_COUNT',
            'count': '0',
            'engine': 'XOR_BINARY_SUBSTITUTE_UNSAT',
            'substitute_report': sub,
            'complexity_claim': False,
        }
    if not reduced.clauses:
        if eqs:
            count = count_pure_xor(eqs, reduced.n)
        else:
            count = 1 << reduced.n
        return {
            'status': 'EXACT_COUNT',
            'count': str(count),
            'engine': 'XOR_BINARY_SUBSTITUTE',
            'substitute_report': sub,
            'complexity_claim': False,
        }
    passthrough = {
        k: v
        for k, v in kwargs.items()
        if k not in ('xor_strategy', 'verify_direct', 'xor_equations', 'max_xor_enum_bits', 'preprocess')
    }
    passthrough.pop('max_xor_enum_bits', None)
    if eqs:
        out = structure_aware_count(
            reduced,
            inner_count=inner_count,
            xor_equations=eqs,
            preprocess=False,
            xor_strategy='condition',
            verify_direct=False,
            max_xor_enum_bits=kwargs.get('max_xor_enum_bits', 18),
            **passthrough,
        )
    else:
        out = structure_aware_count(
            reduced,
            inner_count=inner_count,
            preprocess=False,
            verify_direct=False,
            **passthrough,
        )
    out['engine'] = 'XOR_BINARY_SUBSTITUTE_' + str(out.get('engine', 'STRUCTURE'))
    out['substitute_report'] = sub
    return out
