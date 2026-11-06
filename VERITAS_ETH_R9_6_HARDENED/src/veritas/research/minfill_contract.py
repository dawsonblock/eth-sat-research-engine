"""Legacy v1.4 deterministic minimum-DEGREE exact variable elimination.

Exponential in induced width. Uses integer arithmetic with optional modulus.
Refuses tensors outside caller-supplied memory/work/time budgets.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from itertools import product
from time import monotonic
from veritas.research.tensor import Factor,TensorNetwork


class ContractionBudgetExceeded(Exception):
    pass


@dataclass(frozen=True)
class ContractionStats:
    method: str
    eliminated_wires: int
    max_join_width: int
    peak_intermediate_entries: int
    evaluated_assignments: int
    factor_products: int
    elimination_order: tuple[int,...]
    elapsed_seconds: float


def minfill_contract(net: TensorNetwork, *, modulus: int | None = None,
                     max_table_entries: int = 1 << 16,
                     max_work_assignments: int = 5_000_000,
                     timeout_s: float = 15.0) -> tuple[int, ContractionStats]:
    if modulus is not None and (type(modulus) is not int or not 2 <= modulus <= 2**128):
        raise ValueError('modulus must be an integer between 2 and 2**128')
    if type(max_table_entries) is not int or not 1 <= max_table_entries <= (1 << 20):
        raise ValueError('max_table_entries must be an integer in 1..2**20')
    if type(max_work_assignments) is not int or not 1 <= max_work_assignments <= 20_000_000:
        raise ValueError('max_work_assignments must be an integer in 1..20000000')
    if type(timeout_s) not in (int,float) or not 0 < timeout_s <= 60:
        raise ValueError('timeout_s must be in (0,60]')
    start=monotonic()
    deadline=start+timeout_s
    factors=list(net.factors)
    active=set(range(net.edges))
    order=[]
    peak=1
    max_width=0
    assignments=0
    products=0
    while active:
        if monotonic()>deadline:
            raise ContractionBudgetExceeded('global deadline exceeded')
        # Min-neighbor (induced-width proxy), tie-broken by total table size
        # and stable original edge index. This is a heuristic, not optimality.
        neighborhoods=[]
        for edge in sorted(active):
            touched=[f for f in factors if edge in f.ports]
            neighbors=set()
            for factor in touched:
                neighbors.update(factor.ports)
            neighbors.discard(edge)
            neighborhoods.append((len(neighbors),sum(len(f.table) for f in touched),edge,
                                  tuple(sorted(neighbors)),touched))
        width,_,edge,neighbor_ports,touched=min(neighborhoods,key=lambda x:x[:3])
        entries=1<<width
        if entries>max_table_entries:
            raise ContractionBudgetExceeded('intermediate tensor exceeds entry budget')
        if assignments+2*entries>max_work_assignments:
            raise ContractionBudgetExceeded('global assignment budget exhausted')
        max_width=max(max_width,width)
        peak=max(peak,entries)
        remaining=[f for f in factors if edge not in f.ports]
        new_values=[]
        for assignment_index in range(entries):
            if assignment_index%1024==0 and monotonic()>deadline:
                raise ContractionBudgetExceeded('global deadline exceeded')
            value_map={p:bool(assignment_index & (1<<j)) for j,p in enumerate(neighbor_ports)}
            subtotal=0
            for edge_value in (False,True):
                value_map[edge]=edge_value
                prodval=1
                for factor in touched:
                    prodval *= factor.value(value_map)
                    products+=1
                    if prodval==0:break
                    if modulus is not None:prodval%=modulus
                subtotal+=prodval
                if modulus is not None:subtotal%=modulus
            new_values.append(subtotal)
        assignments+=2*entries
        factors=remaining+[Factor(neighbor_ports,tuple(new_values),f'minfill:{edge}')]
        active.remove(edge)
        order.append(edge)
    result=1
    for factor in factors:
        if factor.ports:
            raise AssertionError('uneliminated edge after contraction')
        result *= factor.table[0]
        if modulus is not None:result%=modulus
    stats=ContractionStats('DETERMINISTIC_MIN_NEIGHBOR_EXACT',len(order),max_width,
                           peak,assignments,products,tuple(order),monotonic()-start)
    return result,stats
