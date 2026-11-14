"""Encode GF(2) XOR constraints as CNF (Tseitin chain); #SAT-preserving with auxiliaries."""
from __future__ import annotations

from veritas.core.cnf import CNF
from veritas.research.gf2_xor_count import XorEquation


def _xor3_zero_clauses(x: int, y: int, z: int) -> list[tuple[int, ...]]:
    """CNF for x ⊕ y ⊕ z = 0 (even parity)."""
    return [
        (x, y, -z),
        (-x, -y, -z),
        (-x, y, z),
        (x, -y, z),
    ]


def _xor2_rhs_clauses(a: int, b: int, rhs: int) -> list[tuple[int, ...]]:
    """CNF for a ⊕ b = rhs."""
    if rhs & 1:
        return [(a, b), (-a, -b)]
    return [(-a, b), (a, -b)]


def encode_xor_equations(
    cnf: CNF,
    equations: tuple[XorEquation, ...],
) -> tuple[CNF, dict]:
    """Append XOR equations as CNF; introduce fresh variables as needed."""
    clauses: list[list[int]] = [list(c) for c in cnf.clauses]
    next_var = cnf.n
    aux_added = 0
    xor_clauses = 0
    for eq in equations:
        rhs = eq.rhs & 1
        variables = list(eq.variables)
        if not variables:
            if rhs:
                clauses.append([1, -1])
                xor_clauses += 1
            continue
        if len(variables) == 1:
            v = variables[0]
            clauses.append([v] if rhs else [-v])
            xor_clauses += 1
            continue
        acc = variables[0]
        for v in variables[1:-1]:
            next_var += 1
            aux = next_var
            aux_added += 1
            for cl in _xor3_zero_clauses(acc, v, aux):
                clauses.append(list(cl))
            xor_clauses += 4
            acc = aux
        last = variables[-1]
        for cl in _xor2_rhs_clauses(acc, last, rhs):
            clauses.append(list(cl))
        xor_clauses += 2
    out = CNF.from_lists(next_var, clauses)
    report = {
        'aux_variables_added': aux_added,
        'xor_cnf_clauses_added': xor_clauses,
        'encoded_n': out.n,
        'contract': 'GF2_XOR_TSEITIN_CHAIN',
        'complexity_claim': False,
    }
    return out, report


def count_via_xor_encoding(
    cnf: CNF,
    equations: tuple[XorEquation, ...],
    *,
    inner_count=None,
    **kwargs,
) -> dict:
    """Exact #SAT by reducing mixed instance to pure CNF."""
    from veritas.research.cnf_structure import structure_aware_count

    encoded, enc_report = encode_xor_equations(cnf, equations)
    passthrough = {
        k: v
        for k, v in kwargs.items()
        if k
        not in ('xor_strategy', 'verify_direct', 'xor_equations', 'max_xor_enum_bits', 'preprocess')
    }
    if encoded.n <= 18:
        from veritas.solvers.reference import exhaustive_count

        count = exhaustive_count(encoded)
        return {
            'status': 'EXACT_COUNT',
            'count': str(count),
            'engine': 'XOR_CNF_ENCODE_EXHAUSTIVE',
            'xor_encode': enc_report,
            'complexity_claim': False,
        }
    passthrough['max_wires'] = max(int(passthrough.get('max_wires', 1800)), encoded.n)
    passthrough['portfolio_mode'] = 'auto'
    passthrough['enable_separators'] = True
    out = structure_aware_count(encoded, preprocess=False, verify_direct=False, **passthrough)
    out['engine'] = 'XOR_CNF_ENCODE_' + str(out.get('engine', 'STRUCTURE'))
    out['xor_encode'] = enc_report
    return out
