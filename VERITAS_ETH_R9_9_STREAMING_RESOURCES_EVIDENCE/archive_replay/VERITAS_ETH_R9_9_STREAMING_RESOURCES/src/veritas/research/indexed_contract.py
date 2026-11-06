"""Exact optimized factor contraction with compiled local bit projections.

This is the same ordinary Boolean bucket-elimination algorithm as
contraction_planner.contract_order, with fewer Python allocations. It has the
same treewidth/exponential worst-case bounds; it is NOT the ETH paper solver.
"""
from __future__ import annotations
from time import monotonic
from veritas.research.tensor import Factor
from veritas.research.contraction_planner import FactorModel, ContractionPlan, ExactStats, ContractLimit


def _index_projection(neighbors: tuple[int, ...], factor: Factor,
                      entries: int) -> tuple[list[int], int]:
    positions = {v: i for i,v in enumerate(factor.ports)}
    shifts = [1 << positions[p] if p in positions else 0 for p in neighbors]
    projection = [0] * entries
    for mask in range(1, entries):
        bit = mask & -mask
        projection[mask] = projection[mask ^ bit] | shifts[bit.bit_length() - 1]
    return projection, 1 << positions[next(v for v in factor.ports if v not in neighbors)]


def indexed_contract_order(model: FactorModel, plan: ContractionPlan, *,
                           modulus: int | None = None, max_table_entries: int = 65536,
                           max_work_assignments: int = 2_000_000,
                           deadline: float | None = None) -> tuple[int, ExactStats]:
    if type(max_table_entries) is not int or not 1 <= max_table_entries <= (1 << 20):
        raise ValueError('bad table-entry budget')
    if type(max_work_assignments) is not int or not 1 <= max_work_assignments <= 20_000_000:
        raise ValueError('bad evaluation budget')
    if modulus is not None and (type(modulus) is not int or not 2 <= modulus <= 2**256):
        raise ValueError('bad modulus')
    if len(plan.order) != len(model.variables) or set(plan.order) != set(model.variables):
        raise ValueError('invalid elimination order')
    if any(len(f.table) > max_table_entries for f in model.factors):
        raise ContractLimit('input factor exceeds table budget')
    if plan.peak_table_entries > max_table_entries or plan.estimated_assignments > max_work_assignments:
        raise ContractLimit('predicted contraction exceeds resource budget')
    start = monotonic()
    if deadline is None:
        deadline = start + 15
    factors = list(model.factors)
    peak = max((len(f.table) for f in factors), default=1)
    work = lookups = 0
    for vertex in plan.order:
        if monotonic() > deadline:
            raise ContractLimit('deadline exceeded')
        touched = [f for f in factors if vertex in f.ports]
        factors = [f for f in factors if vertex not in f.ports]
        neighbors = tuple(sorted({p for f in touched for p in f.ports} - {vertex}))
        entries = 1 << len(neighbors)
        if entries > max_table_entries or work + 2*entries > max_work_assignments:
            raise ContractLimit('intermediate exceeds resource budget')
        projections = []
        # Bound scratch allocation: no more than 262,144 projected indices
        # across a bucket. Large buckets use a slower on-demand projection.
        precompute = entries * len(touched) <= 262144
        for f in touched:
            if precompute:
                projection, edge_bit = _index_projection(neighbors, f, entries)
                projections.append((f.table, projection, edge_bit, None))
            else:
                pos={v:i for i,v in enumerate(f.ports)}
                shift=tuple(1<<pos[v] if v in pos else 0 for v in neighbors)
                edge_bit=1<<pos[vertex]
                projections.append((f.table, None, edge_bit, shift))
        results = [0]*entries
        for mask in range(entries):
            if (mask & 511) == 0 and monotonic() > deadline:
                raise ContractLimit('deadline exceeded')
            accum = 0
            for on in (False, True):
                product = 1
                for table, projection, edge_bit, shift in projections:
                    if projection is None:
                        current=mask
                        local=0
                        while current:
                            lowbit=current & -current
                            local|=shift[lowbit.bit_length()-1]
                            current^=lowbit
                    else:
                        local=projection[mask]
                    value = table[local | (edge_bit if on else 0)]
                    lookups += 1
                    if value == 0:
                        product = 0
                        break
                    product *= value
                    if modulus is not None:
                        product %= modulus
                accum += product
            results[mask] = accum % modulus if modulus is not None else accum
        work += 2*entries
        peak = max(peak, entries)
        factors.append(Factor(neighbors, tuple(results), f'indexed:{vertex}'))
    count = 1
    for f in factors:
        if f.ports:
            raise AssertionError('uneliminated variable')
        count *= f.table[0]
        if modulus is not None:
            count %= modulus
    return count, ExactStats(peak, work, lookups, len(plan.order), monotonic()-start,
                             method='EXACT_INDEXED_FACTOR_ELIMINATION')
