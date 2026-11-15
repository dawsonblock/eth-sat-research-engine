"""Disjoint CNF components with per-component XOR (no cross-component parity links)."""
from __future__ import annotations

from veritas.core.cnf import CNF
from veritas.research.cnf_structure import _project_component, analyze_cnf_structure
from veritas.research.gf2_xor_count import XorEquation


def _reindex_equations(
    equations: tuple[XorEquation, ...], mapping: dict[int, int]
) -> tuple[XorEquation, ...]:
    out: list[XorEquation] = []
    for eq in equations:
        vars2 = tuple(mapping[v] for v in sorted(eq.variables) if v in mapping)
        if len(vars2) >= 1 and len(set(vars2)) == len(vars2):
            out.append(XorEquation(vars2, eq.rhs))
    return tuple(out)


def try_component_product_mixed_xor(
    cnf: CNF,
    equations: tuple[XorEquation, ...],
    *,
    inner_count=None,
    max_enum_bits: int = 18,
    **kwargs,
) -> dict | None:
    """Exact product when every XOR equation lies in a single CNF component."""
    if not equations:
        return None
    report = analyze_cnf_structure(cnf)
    if report.component_count <= 1:
        return None
    groups = [set(c.variables) for c in report.components]
    buckets: list[list[XorEquation]] = [[] for _ in groups]
    for eq in equations:
        vs = set(eq.variables)
        owners = [i for i, group in enumerate(groups) if vs <= group]
        if len(owners) != 1:
            return None
        buckets[owners[0]].append(eq)
    from veritas.research.gf2_xor_mixed import count_mixed_xor_cnf
    from veritas.research.hybrid_router import hybrid_count

    counter = inner_count if inner_count is not None else hybrid_count
    passthrough = {
        k: v
        for k, v in kwargs.items()
        if k not in ('xor_strategy', 'verify_direct', 'xor_equations', 'max_xor_enum_bits', 'preprocess')
    }
    product = 1
    parts: list[dict] = []
    for comp, comp_eqs in zip(report.components, buckets):
        mapping = {v: i + 1 for i, v in enumerate(sorted(comp.variables))}
        sub = _project_component(cnf, comp.variables)
        local_eqs = _reindex_equations(tuple(comp_eqs), mapping)
        if comp.clause_count == 0 and not local_eqs:
            factor = 2**comp.local_n
            engine = 'UNCONSTRAINED_COMPONENT'
        elif not local_eqs:
            sub_out = counter(sub, **passthrough)
            factor = int(sub_out['count'])
            engine = str(sub_out.get('engine', 'HYBRID'))
        else:
            mixed = count_mixed_xor_cnf(sub, local_eqs, max_enum_bits=max_enum_bits)
            factor = int(mixed['count'])
            engine = mixed['engine']
        product *= factor
        parts.append(
            {
                'variables': list(comp.variables),
                'xor_equations': len(local_eqs),
                'engine': engine,
                'count': str(factor),
            }
        )
    return {
        'status': 'EXACT_COUNT',
        'count': str(product),
        'engine': 'MIXED_XOR_COMPONENT_PRODUCT',
        'structure': {
            'decomposed': True,
            'parts': parts,
            'contract': report.contract,
            'warning': 'Valid only when XOR constraints do not span CNF components.',
        },
        'complexity_claim': False,
    }
