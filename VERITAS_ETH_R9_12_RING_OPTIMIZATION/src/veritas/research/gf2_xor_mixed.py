"""Mixed CNF + GF(2) XOR counting by conditioning on the xor null space."""
from __future__ import annotations

from dataclasses import dataclass

from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation, _row_mask, solve_xor_system


@dataclass(frozen=True)
class XorParametrization:
    n: int
    rank: int
    free_variables: tuple[int, ...]
    pivot_leads: tuple[int, ...]
    pivot_masks: tuple[int, ...]
    pivot_rhs: tuple[int, ...]
    consistent: bool


def xor_parametrization(equations: tuple[XorEquation, ...], n: int) -> XorParametrization:
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
                return XorParametrization(n, 0, (), (), (), (), False)
            redundant += 1
    pivot_vars = {lead + 1 for lead in pivots}
    free = tuple(v for v in range(1, n + 1) if v not in pivot_vars)
    leads = tuple(sorted(pivots))
    return XorParametrization(
        n,
        len(pivots),
        free,
        leads,
        tuple(pivots[l][0] for l in leads),
        tuple(pivots[l][1] for l in leads),
        True,
    )


def assignment_from_free(free_values: dict[int, int], param: XorParametrization) -> dict[int, bool]:
    if not param.consistent:
        raise ValueError('inconsistent xor system')
    values = {v: int(free_values.get(v, 0)) & 1 for v in param.free_variables}
    pivots = {param.pivot_leads[i]: (param.pivot_masks[i], param.pivot_rhs[i]) for i in range(len(param.pivot_leads))}
    for lead in sorted(pivots, reverse=True):
        mask, rhs = pivots[lead]
        var = lead + 1
        acc = rhs
        for b in range(param.n):
            if b == lead:
                continue
            if (mask >> b) & 1:
                acc ^= values.get(b + 1, 0)
        values[var] = acc
    return {v: bool(values.get(v, 0)) for v in range(1, param.n + 1)}


def count_mixed_xor_cnf(
    cnf: CNF,
    equations: tuple[XorEquation, ...],
    *,
    max_enum_bits: int = 18,
) -> dict:
    param = xor_parametrization(equations, cnf.n)
    report = solve_xor_system(equations, cnf.n)
    if not param.consistent:
        return {'count': 0, 'engine': 'MIXED_XOR_CONDITIONING', 'enumerated': 0}
    free_bits = len(param.free_variables)
    if free_bits > max_enum_bits:
        raise ValueError('xor free dimension exceeds conditioning budget')
    total = 0
    for mask in range(1 << free_bits):
        free_vals = {param.free_variables[i]: (mask >> i) & 1 for i in range(free_bits)}
        assignment = assignment_from_free(free_vals, param)
        if cnf.evaluate(assignment):
            total += 1
    return {
        'count': total,
        'engine': 'MIXED_XOR_CONDITIONING',
        'enumerated': 1 << free_bits,
        'xor_rank': report.rank,
        'free_xor_dimension': free_bits,
        'contract': 'COUNT_PRESERVING_CONDITIONING',
        'complexity_claim': False,
    }
