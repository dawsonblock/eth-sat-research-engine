"""Exact separator conditioning with memoized residual subproblems.

For separator S, Z = sum_s prod_C Z_C(s), with constant factors accounted
for once. Splitting and memoization preserve counts, including unused bits.
No assumption of small separators for arbitrary networks is made.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from veritas.research.tensor import Factor
from veritas.research.graph_decomposition import primal_graph, components, small_separator
from veritas.research.indexed_contract import indexed_contract_order
from veritas.research.sparse_contract import sparse_contract_order
from veritas.research.contraction_planner import (FactorModel, ContractLimit,
    elimination_order,contract_order)


@dataclass(frozen=True)
class BoundaryStats:
    separator_splits: int
    slice_splits: int
    component_splits: int
    cache_hits: int
    cache_entries: int
    calls: int
    leaf_contractions: int
    evaluated_assignments: int
    peak_table_entries: int
    elapsed_seconds: float
    method: str='EXACT_SEPARATOR_BOUNDARY_DP'


def _restrict_factor(f:Factor, bits:dict[int,bool], modulus:int|None)->Factor:
    ports=tuple(p for p in f.ports if p not in bits)
    if len(ports)==len(f.ports):return f
    table=[]
    for mask in range(1<<len(ports)):
        assignment=dict(bits)
        assignment.update({p:bool(mask&(1<<i)) for i,p in enumerate(ports)})
        v=f.value(assignment)
        table.append(v%modulus if modulus else v)
    return Factor(ports,tuple(table),f.label)


def boundary_contract(model:FactorModel, *, modulus:int|None=None,
                      max_separator:int=2, max_depth:int=20, max_cache_entries:int=10000,
                      max_calls:int=50000, max_slices:int=3, max_table_entries:int=65536,
                      max_work_assignments:int=2000000,
                      deadline:float|None=None, execution_mode:str='indexed')->tuple[int,BoundaryStats]:
    if execution_mode not in ('legacy','indexed','sparse'):raise ValueError('invalid execution_mode')
    if not 0<=max_separator<=3 or not 0<=max_depth<=100 or not 0<=max_slices<=8:
        raise ValueError('invalid separator/depth limits')
    if not 0<=max_cache_entries<=100000 or not 1<=max_calls<=1000000:
        raise ValueError('invalid cache/call limits')
    if type(max_work_assignments) is not int or not 1<=max_work_assignments<=20000000:
        raise ValueError('invalid global work budget')
    if type(max_table_entries) is not int or not 1<=max_table_entries<=1<<20:
        raise ValueError('invalid table budget')
    if modulus is not None and (type(modulus) is not int or not 2<=modulus<=2**256):
        raise ValueError('invalid modulus')
    start=monotonic(); deadline=deadline or start+15
    if any(len(f.table)>max_table_entries for f in model.factors):
        raise ContractLimit('input factor exceeds table budget')
    cache={}
    counts={'calls':0,'hits':0,'separators':0,'slices':0,'components':0,'leaf':0,'work':0,'peak':max((len(f.table) for f in model.factors),default=1)}

    def recurse(variables:tuple[int,...], factors:tuple[Factor,...], depth:int, sliced:int)->int:
        if monotonic()>deadline:raise ContractLimit('boundary recursion deadline exceeded')
        counts['calls']+=1
        if counts['calls']>max_calls:raise ContractLimit('boundary recursion call limit exceeded')
        # Relabel-invariant signatures are a future optimization. Here canonical
        # factors preserve exact identity; cache cannot introduce false equality.
        key=(variables,tuple(sorted((f.ports,f.table) for f in factors)))
        if key in cache:
            counts['hits']+=1
            return cache[key]
        def memo(value):
            if len(cache)<max_cache_entries:cache[key]=value
            return value
        constants=[f.table[0] for f in factors if not f.ports]
        scalar=1
        for c in constants:
            scalar*=c
            if modulus:scalar%=modulus
        if scalar==0:return memo(0)
        active=tuple(f for f in factors if f.ports)
        if not variables:return memo(scalar)
        graph=primal_graph(variables,active)
        groups=components(graph)
        if len(groups)>1:
            counts['components']+=1
            result=scalar
            lookup={v:i for i,g in enumerate(groups) for v in g}
            grouped=[[] for _ in groups]
            for f in active:
                ids={lookup[p] for p in f.ports}
                if len(ids)!=1:raise AssertionError('factor spanning independent components')
                grouped[next(iter(ids))].append(f)
            for group,fs in zip(groups,grouped):
                result*=recurse(group,tuple(fs),depth+1,sliced)
                if modulus:result%=modulus
            return memo(result)
        sep=small_separator(graph,max_size=max_separator) if depth<max_depth and max_separator else None
        if sep is not None and len(sep.variables)<=max_separator:
            counts['separators']+=1
            total=0
            remaining=tuple(v for v in variables if v not in sep.variables)
            for bits in range(1<<len(sep.variables)):
                if monotonic()>deadline:raise ContractLimit('boundary recursion deadline exceeded')
                assigned={v:bool(bits&(1<<i)) for i,v in enumerate(sep.variables)}
                conditioned=tuple(_restrict_factor(f,assigned,modulus) for f in active)
                total+=recurse(remaining,conditioned,depth+1,sliced)
                if modulus:total%=modulus
            return memo((scalar*total)%modulus if modulus else scalar*total)
        # No useful separator: use exact variable elimination with the shared budget.
        counts['leaf']+=1
        submodel=FactorModel(variables,active,'SEPARATOR_LEAF')
        quick=elimination_order(submodel, 'min_degree', deadline=deadline)
        remaining_work=max_work_assignments-counts['work']
        order=(quick if quick.peak_table_entries<=max_table_entries and
               quick.estimated_assignments<=remaining_work else
               min((elimination_order(submodel,h,deadline=deadline) for h in ('min_fill','weighted_min_fill')),
                   key=lambda p:(p.estimated_assignments,p.peak_table_entries,p.heuristic)))
        remaining_work=max_work_assignments-counts['work']
        if (order.peak_table_entries>max_table_entries or
            order.estimated_assignments>remaining_work) and sliced<max_slices:
            # Exact index slicing / DPLL conditioning. Guarantees smaller
            # remaining variable sets; trades time for bounded intermediate
            # memory. Each branch is computed with shared global budgets.
            pivot=min(variables,key=lambda v:(-len(graph[v]),v))
            remaining=tuple(v for v in variables if v!=pivot)
            counts['slices']+=1
            total=0
            for bit in (False,True):
                conditioned=tuple(_restrict_factor(f,{pivot:bit},modulus) for f in active)
                total+=recurse(remaining,conditioned,depth+1,sliced+1)
                if modulus:total%=modulus
            return memo((scalar*total)%modulus if modulus else scalar*total)
        if remaining_work<1:raise ContractLimit('shared work budget exhausted')
        engine_fn={'indexed':indexed_contract_order,'legacy':contract_order,'sparse':sparse_contract_order}[execution_mode]
        value,stat=engine_fn(submodel,order,modulus=modulus,
                                  max_table_entries=max_table_entries,
                                  max_work_assignments=remaining_work,deadline=deadline)
        counts['work']+=stat.evaluated_assignments
        counts['peak']=max(counts['peak'],stat.peak_table_entries)
        return memo((scalar*value)%modulus if modulus else scalar*value)
    result=recurse(tuple(sorted(model.variables)),model.factors,0,0)
    return result,BoundaryStats(counts['separators'],counts['slices'],counts['components'],counts['hits'],len(cache),
        counts['calls'],counts['leaf'],counts['work'],counts['peak'],monotonic()-start)
