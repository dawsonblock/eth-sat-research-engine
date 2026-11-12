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


def substitute_binary_xor(cnf: CNF, equations: tuple[XorEquation, ...]) -> tuple[CNF, tuple[XorEquation, ...], dict]:
    """Replace x_a with x_b or its negation when an equation is exactly a XOR b = rhs."""
    eqs = list(equations)
    clauses = [list(c) for c in cnf.clauses]
    removed: set[int] = set()
    report: dict = {'binary_substitutions': 0, 'removed_variables': []}
    changed = True
    while changed:
        changed = False
        for i, eq in enumerate(list(eqs)):
            if len(eq.variables) != 2:
                continue
            a, b = sorted(eq.variables)
            if a in removed or b in removed:
                continue
            rhs = eq.rhs & 1
            clauses = [[_rewrite_lit(lit, a, b, rhs) for lit in cl] for cl in clauses]
            removed.add(a)
            eqs.pop(i)
            report['binary_substitutions'] += 1
            report['removed_variables'].append(a)
            changed = True
            break
    if not report['binary_substitutions']:
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
            # Fixed parity on one variable becomes unit unary — drop for caller preprocess.
            surviving.append(XorEquation(vars2, eq.rhs))
    return (
        CNF.from_lists(len(keep), new_clauses),
        tuple(surviving),
        {'changed': True, **report},
    )


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
    out = structure_aware_count(
        reduced,
        inner_count=inner_count,
        xor_equations=eqs or None,
        preprocess=False,
        **kwargs,
    )
    out['engine'] = 'XOR_BINARY_SUBSTITUTE_' + str(out.get('engine', 'STRUCTURE'))
    out['substitute_report'] = sub
    return out
