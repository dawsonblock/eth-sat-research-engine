"""Count-preserving XOR simplifications before mixed CNF+XOR counting.

Every elimination below is applied to *all* constraints, not just the clauses:

* a unary equation ``x = c`` fixes ``x`` everywhere (clauses and the other equations);
* a binary equation ``a xor b = r`` rewrites ``a := b xor r`` everywhere.

Both steps remove one variable and one equation, and exactly one value of the removed
variable satisfies the removed equation, so the model count is unchanged.  The earlier
implementation only rewrote the clauses (and for unary units applied the polarity
backwards), which left other equations pointing at deleted variables.
"""
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


def _normalize_clause(clause) -> list[int] | None:
    """Drop duplicate literals; return None for a tautological clause."""
    seen: set[int] = set()
    out: list[int] = []
    for lit in clause:
        if -lit in seen:
            return None
        if lit in seen:
            continue
        seen.add(lit)
        out.append(lit)
    return out


def _simplify(
    cnf: CNF,
    equations: tuple[XorEquation, ...],
    *,
    binary: bool,
    require_pivot_in_clauses: bool,
) -> tuple[CNF, tuple[XorEquation, ...], dict]:
    n = cnf.n
    for eq in equations:
        if any(v > n for v in eq.variables):
            raise ValueError('variable exceeds n')
    clauses: list[list[int]] = [list(c) for c in cnf.clauses]
    eqs: list[tuple[frozenset[int], int]] = [
        (frozenset(eq.variables), eq.rhs & 1) for eq in equations
    ]
    removed: set[int] = set()
    report: dict = {
        'binary_substitutions': 0,
        'removed_variables': [],
        'skipped_safe': 0,
        'unary_units': 0,
    }
    unsat = any(len(cl) == 0 for cl in clauses)  # explicit empty clause

    def assign(var: int, value: bool) -> bool:
        """Fix ``var`` everywhere; return False when a clause becomes empty."""
        nonlocal clauses, eqs
        out: list[list[int]] = []
        for cl in clauses:
            satisfied = False
            row: list[int] = []
            for lit in cl:
                if abs(lit) == var:
                    if (lit > 0) == value:
                        satisfied = True
                        break
                    continue
                row.append(lit)
            if satisfied:
                continue
            if not row:
                return False
            out.append(row)
        clauses = out
        eqs = [
            ((vs - {var}, rhs ^ int(value)) if var in vs else (vs, rhs)) for vs, rhs in eqs
        ]
        return True

    def replace(a: int, b: int, rhs: int) -> None:
        """Rewrite ``a := b xor rhs`` in every clause and equation."""
        nonlocal clauses, eqs
        out: list[list[int]] = []
        for cl in clauses:
            row = _normalize_clause([_rewrite_lit(lit, a, b, rhs) for lit in cl])
            if row is not None:
                out.append(row)
        clauses = out
        eqs = [
            (((vs - {a}) ^ {b}, r ^ rhs) if a in vs else (vs, r)) for vs, r in eqs
        ]

    progress = True
    while progress and not unsat:
        progress = False
        for idx, (vs, rhs) in enumerate(eqs):
            if len(vs) == 0:
                if rhs:
                    unsat = True
                    break
                eqs.pop(idx)
                progress = True
                break
            if len(vs) == 1:
                (var,) = vs
                eqs.pop(idx)
                report['unary_units'] += 1
                removed.add(var)
                if not assign(var, bool(rhs)):
                    unsat = True
                progress = True
                break
            if binary and len(vs) == 2:
                a, b = sorted(vs)
                if require_pivot_in_clauses and not any(
                    abs(lit) == a for cl in clauses for lit in cl
                ):
                    continue
                eqs.pop(idx)
                replace(a, b, rhs)
                removed.add(a)
                report['binary_substitutions'] += 1
                report['removed_variables'].append(a)
                progress = True
                break

    if require_pivot_in_clauses:
        live = {abs(lit) for cl in clauses for lit in cl}
        report['skipped_safe'] = sum(
            1 for vs, _ in eqs if len(vs) == 2 and min(vs) not in live
        )

    if unsat:
        report.update({'changed': True, 'empty_clause': True})
        return CNF.from_lists(max(n, 1), [[1], [-1]]), (), report

    if not report['binary_substitutions'] and not report['unary_units']:
        report['changed'] = False
        return cnf, equations, report

    keep = [v for v in range(1, n + 1) if v not in removed]
    mapping = {old: idx for idx, old in enumerate(keep, start=1)}
    new_clauses = [
        [mapping[abs(lit)] if lit > 0 else -mapping[abs(lit)] for lit in cl] for cl in clauses
    ]
    surviving = tuple(
        XorEquation(tuple(sorted(mapping[v] for v in vs)), rhs) for vs, rhs in eqs
    )
    report['changed'] = True
    return CNF.from_lists(len(keep), new_clauses), surviving, report


def apply_xor_unary_units(
    cnf: CNF, equations: tuple[XorEquation, ...]
) -> tuple[CNF, tuple[XorEquation, ...], dict]:
    """Fix single-variable XOR equations ``x_v = rhs`` everywhere and drop ``v``.

    Returns the reduced (reindexed) CNF and the surviving equations, renumbered to match.
    """
    out_cnf, eqs, report = _simplify(
        cnf, equations, binary=False, require_pivot_in_clauses=False
    )
    unary = {'unary_units': report['unary_units']}
    if report.get('empty_clause'):
        unary['empty_clause'] = True
    return out_cnf, eqs, unary


def substitute_binary_xor(
    cnf: CNF, equations: tuple[XorEquation, ...], *, require_pivot_in_clauses: bool = True
) -> tuple[CNF, tuple[XorEquation, ...], dict]:
    """Eliminate unary and ``a xor b = rhs`` equations by substitution.

    With ``require_pivot_in_clauses`` (default) a binary equation whose pivot never
    appears in a clause is left in place as a pure XOR constraint.  Substitution is
    propagated into the remaining equations, so the result is count-preserving either way.
    """
    return _simplify(
        cnf, equations, binary=True, require_pivot_in_clauses=require_pivot_in_clauses
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
