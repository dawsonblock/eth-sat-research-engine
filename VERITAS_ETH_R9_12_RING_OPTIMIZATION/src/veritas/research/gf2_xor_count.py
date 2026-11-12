"""GF(2) XOR systems for exact model counting (2^{n-rank} solutions)."""
from __future__ import annotations

from dataclasses import dataclass

from veritas.core.cnf import CNF


@dataclass(frozen=True)
class XorEquation:
    variables: tuple[int, ...]
    rhs: int

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in self.variables):
            raise ValueError('variables must be positive 1-indexed ids')
        if self.rhs not in (0, 1):
            raise ValueError('rhs must be 0 or 1')
        if len(set(self.variables)) != len(self.variables):
            raise ValueError('duplicate variable in xor equation')


def _row_mask(variables: tuple[int, ...], n: int) -> int:
    mask = 0
    for v in variables:
        if v > n:
            raise ValueError('variable exceeds n')
        mask ^= 1 << (v - 1)
    return mask


@dataclass(frozen=True)
class XorSolveReport:
    n: int
    rank: int
    consistent: bool
    solution_count: int
    redundant_equations: int
    contract: str


def solve_xor_system(equations: tuple[XorEquation, ...], n: int) -> XorSolveReport:
    if type(n) is not int or n < 0:
        raise ValueError('n must be nonnegative')
    pivots: dict[int, tuple[int, int]] = {}
    redundant = 0
    for eq in equations:
        mask, rhs = _row_mask(eq.variables, n), eq.rhs & 1
        cur_mask, cur_rhs = mask, rhs
        while cur_mask:
            lead = cur_mask.bit_length() - 1
            if lead in pivots:
                pivot_mask, pivot_rhs = pivots[lead]
                if cur_mask & (1 << lead):
                    cur_mask ^= pivot_mask
                    cur_rhs ^= pivot_rhs
                else:
                    break
            else:
                pivots[lead] = (cur_mask, cur_rhs)
                for other_lead in list(pivots):
                    if other_lead == lead:
                        continue
                    o_mask, o_rhs = pivots[other_lead]
                    if o_mask & (1 << lead):
                        pivots[other_lead] = (o_mask ^ cur_mask, o_rhs ^ cur_rhs)
                break
        else:
            if cur_rhs:
                return XorSolveReport(n, len(pivots), False, 0, redundant, 'GF2_INCONSISTENT')
            redundant += 1
    rank = len(pivots)
    free = max(0, n - rank)
    return XorSolveReport(
        n,
        rank,
        True,
        1 << free,
        redundant,
        'GF2_FREE_DIMENSION',
    )


def parse_xor_equations(data: list[dict], *, n: int) -> tuple[XorEquation, ...]:
    out: list[XorEquation] = []
    for row in data:
        out.append(XorEquation(tuple(row['variables']), int(row['rhs'])))
    return tuple(out)


def count_pure_xor(equations: tuple[XorEquation, ...], n: int) -> int:
    report = solve_xor_system(equations, n)
    if not report.consistent:
        return 0
    return report.solution_count


def xor_chain_example() -> tuple[tuple[XorEquation, ...], int]:
    """x1^x2=1, x2^x3=0, x1^x3=1  =>  rank 2 on three variables => count 2."""
    eqs = (
        XorEquation((1, 2), 1),
        XorEquation((2, 3), 0),
        XorEquation((1, 3), 1),
    )
    return eqs, 3


def structure_with_optional_xor(
    cnf: CNF,
    *,
    xor_equations: tuple[XorEquation, ...] | None = None,
    inner_count=None,
    preprocess: bool = True,
    **kwargs,
) -> dict:
    """Preprocess, optional pure-XOR shortcut, then structure-aware counting."""
    from veritas.research.cnf_structure import structure_aware_count

    original_digest = cnf.digest()
    steps: list[dict] = []
    from veritas.research.cnf_preprocess import count_preserving_preprocess

    if preprocess:
        cnf, prep = count_preserving_preprocess(cnf)
        steps.append({'stage': 'preprocess', 'report': prep.__dict__})
        if prep.empty_clause:
            return {
                'status': 'EXACT_COUNT',
                'count': '0',
                'engine': 'PREPROCESS_UNSAT',
                'formula_sha256': original_digest,
                'pipeline': {'steps': steps, 'complexity_claim': False},
            }
    if xor_equations:
        report = solve_xor_system(xor_equations, cnf.n)
        xor_vars = {v for eq in xor_equations for v in eq.variables}
        clause_vars = {abs(lit) for c in cnf.clauses for lit in c}
        if not clause_vars and xor_vars <= set(range(1, cnf.n + 1)):
            steps.append({'stage': 'xor_gf2', 'report': report.__dict__})
            return {
                'status': 'EXACT_COUNT',
                'count': str(report.solution_count),
                'engine': 'GF2_XOR_ELIMINATION',
                'formula_sha256': original_digest,
                'pipeline': {'steps': steps, 'complexity_claim': False},
            }
        xor_strategy = kwargs.pop('xor_strategy', 'auto')
        max_enum = int(kwargs.pop('max_xor_enum_bits', 18))
        verify_direct = kwargs.pop('verify_direct', cnf.n <= 18)

        def _mixed_reference():
            from veritas.research.gf2_xor_mixed import reference_mixed_count

            return reference_mixed_count(
                cnf, xor_equations, max_enum_bits=max_enum, exhaustive_max_n=18
            )

        def _verify_count(claimed: str) -> tuple[bool, dict | None]:
            if not verify_direct:
                return False, None
            try:
                ref = _mixed_reference()
            except ValueError as exc:
                return False, {'reference_unavailable': str(exc), 'independent_verification': False}
            if not ref.independent or ref.count is None:
                return False, {
                    'reference_engine': ref.engine,
                    'independent_verification': False,
                    'reason': 'no independent mixed reference for this formula size',
                }
            return str(claimed) == str(ref.count), {
                'reference_count': str(ref.count),
                'reference_engine': ref.engine,
                'matches_reference': str(claimed) == str(ref.count),
                'independent_verification': True,
            }

        from veritas.research.gf2_xor_mixed import xor_parametrization

        param_preview = xor_parametrization(xor_equations, cnf.n)
        free_bits = len(param_preview.free_variables)
        use_encode = xor_strategy == 'encode' or (
            xor_strategy == 'auto' and free_bits > max_enum
        )

        def _finish_encode(encoded: dict) -> dict:
            ok, cross = _verify_count(str(encoded['count']))
            steps.append({'stage': 'xor_cnf_encode', 'report': encoded.get('xor_encode')})
            encoded.update(
                {
                    'formula_sha256': original_digest,
                    'pipeline': {'steps': steps, 'complexity_claim': False},
                    'structure': {
                        'decomposed': False,
                        'cross_check': cross,
                        'warning': 'Mixed instance reduced to CNF with Tseitin auxiliaries.',
                    },
                    'independent_count_checked': bool(
                        cross and cross.get('independent_verification')
                    ),
                }
            )
            return encoded

        if use_encode:
            from veritas.research.gf2_xor_encode import count_via_xor_encoding

            return _finish_encode(
                count_via_xor_encoding(
                    cnf, xor_equations, inner_count=inner_count, **dict(kwargs)
                )
            )

        if xor_strategy in ('auto', 'substitute'):
            from veritas.research.gf2_xor_substitute import try_xor_algebraic_reduce

            algebraic = try_xor_algebraic_reduce(
                cnf, xor_equations, inner_count=inner_count, max_xor_enum_bits=max_enum, **dict(kwargs)
            )
            if algebraic is not None and (
                xor_strategy == 'substitute'
                or algebraic.get('substitute_report', {}).get('changed')
            ):
                ok, cross = _verify_count(str(algebraic['count']))
                if ok:
                    steps.append({'stage': 'xor_substitute', 'report': algebraic.get('substitute_report')})
                    algebraic.setdefault('formula_sha256', original_digest)
                    algebraic.setdefault('pipeline', {'steps': steps, 'complexity_claim': False})
                    algebraic['structure'] = {
                        'decomposed': False,
                        'cross_check': cross,
                        'warning': None,
                    }
                    algebraic['independent_count_checked'] = bool(
                        cross and cross.get('independent_verification')
                    )
                    return algebraic
                steps.append(
                    {
                        'stage': 'xor_substitute_rejected',
                        'report': {
                            'substitute_report': algebraic.get('substitute_report'),
                            'cross_check': cross,
                            'reason': 'COUNT_MISMATCH_WITH_XOR_REFERENCE',
                        },
                    }
                )
                if xor_strategy == 'substitute':
                    raise ValueError('algebraic XOR substitute count failed independent verification')
        from veritas.research.gf2_xor_components import try_component_product_mixed_xor
        from veritas.research.gf2_xor_mixed import count_mixed_xor_cnf

        component = try_component_product_mixed_xor(
            cnf,
            xor_equations,
            inner_count=inner_count,
            max_enum_bits=max_enum,
            **dict(kwargs),
        )
        if component is not None:
            ok, cross = _verify_count(str(component['count']))
            steps.append({'stage': 'xor_component_product', 'report': component.get('structure')})
            component.update(
                {
                    'formula_sha256': original_digest,
                    'pipeline': {'steps': steps, 'complexity_claim': False},
                    'structure': {**component.get('structure', {}), 'cross_check': cross},
                    'independent_count_checked': ok and bool(cross and cross.get('independent_verification')),
                }
            )
            return component
        mixed = count_mixed_xor_cnf(cnf, xor_equations, max_enum_bits=max_enum)
        steps.append({'stage': 'xor_mixed_conditioning', 'report': mixed})
        ok, cross = _verify_count(str(mixed['count']))
        return {
            'status': 'EXACT_COUNT',
            'count': str(mixed['count']),
            'engine': mixed['engine'],
            'formula_sha256': original_digest,
            'pipeline': {'steps': steps, 'complexity_claim': False},
            'structure': {
                'decomposed': False,
                'cross_check': cross,
                'warning': 'Mixed count uses xor null-space enumeration, not algebraic CNF elimination.',
            },
            'independent_count_checked': ok and bool(cross and cross.get('independent_verification')),
        }
    out = structure_aware_count(cnf, inner_count=inner_count, preprocess=False, **kwargs)
    out['formula_sha256'] = original_digest
    out.setdefault('pipeline', {})['steps'] = steps + out.get('pipeline', {}).get('steps', [])
    if steps:
        out['pipeline']['complexity_claim'] = False
    return out
