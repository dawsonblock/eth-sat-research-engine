"""Exact recursive separator contraction for generic Boolean tensor networks.

This is a conventional, bounded divide-and-conquer tensor-network algorithm,
NOT the ETH manuscript's Cauchy / collision-packed mode recursion.

Partition factor vertices into two sets. For each cut edge b, sum over its
Boolean assignment and independently contract the induced children with that
edge fixed. Every edge belongs to exactly two factors. Recursion is exact;
worst-case execution is exponential and no ETH bound is implied.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
from time import monotonic
from typing import Mapping

from veritas.research.tensor import TensorNetwork


@dataclass(frozen=True)
class SeparatorPlan:
    left: tuple[int, ...]
    right: tuple[int, ...]
    cut_edges: tuple[int, ...]
    # Collisions here mean multiple crossing edges incident on one factor.
    # This is a *diagnostic*, not the paper's packet-collision theorem.
    incident_collisions: int
    method: str = 'balanced-exhaustive-cut-v1'


@dataclass
class RecursiveStats:
    calls: int = 0
    cache_hits: int = 0
    leaf_assignments: int = 0
    branch_assignments: int = 0
    max_separator_edges: int = 0
    max_depth: int = 0
    optimized_partitions: int = 0


class ResourceLimit(Exception):
    """A fail-closed bounded reference computation ran out of resources."""


def edge_owners(net: TensorNetwork) -> tuple[tuple[int, int], ...]:
    if net.edges < 0:
        raise ValueError('invalid edge count')
    owners: list[list[int]] = [[] for _ in range(net.edges)]
    for fidx, factor in enumerate(net.factors):
        for e in factor.ports:
            owners[e].append(fidx)
    if any(len(x) != 2 or x[0] == x[1] for x in owners):
        raise ValueError('each edge must join two distinct factors')
    return tuple((a, b) for a, b in owners)


def _plan(factor_ids: tuple[int, ...], owners: tuple[tuple[int,int], ...], *, max_candidates: int = 12_000) -> SeparatorPlan:
    if len(factor_ids) < 2:
        raise ValueError('at least two factors required for a cut')
    if len(factor_ids) > 18:
        raise ValueError('small exact partition planner accepts at most 18 factors')
    local = set(factor_ids)
    internal = [(e,a,b) for e,(a,b) in enumerate(owners) if a in local and b in local]
    split_size = len(factor_ids)//2
    best: tuple[int, int, tuple[int,...], tuple[int,...], tuple[int,...]] | None = None
    checked = 0
    for left in combinations(factor_ids, split_size):
        if len(factor_ids)%2 == 0 and factor_ids[0] not in left:
            continue  # symmetric complements
        checked += 1
        if checked > max_candidates:
            raise ResourceLimit('partition candidate budget exhausted')
        lset = set(left)
        right = tuple(i for i in factor_ids if i not in lset)
        cut = tuple(e for e,a,b in internal if (a in lset) != (b in lset))
        # The first objective minimizes the separator; the second the maximum
        # number of cut edges sharing a vertex. Deterministic ties by factor IDs.
        counts: dict[int,int] = {}
        for e in cut:
            a,b = owners[e]
            counts[a] = counts.get(a,0)+1
            counts[b] = counts.get(b,0)+1
        collisions = sum(v*(v-1)//2 for v in counts.values())
        candidate = (len(cut),collisions,left,right,cut)
        if best is None or candidate < best:
            best = candidate
    assert best is not None
    _,coll,left,right,cut = best
    return SeparatorPlan(tuple(left), tuple(right), tuple(cut), coll)


def separator_plan(net: TensorNetwork) -> SeparatorPlan:
    return _plan(tuple(range(len(net.factors))),edge_owners(net))


def recursive_contract(net: TensorNetwork, *, modulus: int | None = None,
                       leaf_factors: int = 3, max_cut_edges: int = 10,
                       max_leaf_edges: int = 16, max_calls: int = 200_000,
                       timeout_s: float = 10.0) -> tuple[int, RecursiveStats]:
    """Exactly contract through recursive balanced factor partitions.

    Return count and measured stats. If any limit is exceeded, RAISE rather
    than silently return an unverified partial count.
    """
    if type(leaf_factors) is not int or not 1 <= leaf_factors <= 9:
        raise ValueError('leaf_factors must be 1..9')
    if type(max_cut_edges) is not int or not 0 <= max_cut_edges <= 16:
        raise ValueError('max_cut_edges must be 0..16')
    if type(max_leaf_edges) is not int or not 0 <= max_leaf_edges <= 22:
        raise ValueError('max_leaf_edges must be 0..22')
    if type(max_calls) is not int or not 1 <= max_calls <= 1_000_000:
        raise ValueError('max_calls must be 1..1_000_000')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
        raise ValueError('timeout_s must be in (0,30]')
    if modulus is not None and (type(modulus) is not int or not 2 <= modulus <= 1 << 256):
        raise ValueError('invalid modulus')
    owners = edge_owners(net)
    if len(net.factors) > 18 or net.edges > 40:
        raise ValueError('bounded separator prototype: <=18 factors and <=40 edges')
    deadline=monotonic()+timeout_s
    stats=RecursiveStats()
    plans: dict[tuple[int,...], SeparatorPlan] = {}
    cache: dict[tuple[tuple[int,...], tuple[tuple[int,int],...]],int]={}

    def check_budget() -> None:
        if monotonic()>deadline:
            raise ResourceLimit('recursive separator timeout')
        if stats.calls>=max_calls:
            raise ResourceLimit('recursive separator call limit')

    def rec(ids: tuple[int,...], fixed: tuple[tuple[int,int],...], depth: int) -> int:
        check_budget()
        stats.calls+=1
        stats.max_depth=max(stats.max_depth,depth)
        key=(ids,fixed)
        if key in cache:
            stats.cache_hits+=1
            return cache[key]
        idset=set(ids)
        assigned=dict(fixed)
        active=tuple(e for e,(a,b) in enumerate(owners) if a in idset and b in idset and e not in assigned)
        # Every edge with exactly one endpoint inside the subproblem must be
        # fixed by an ancestor's separator assignment.
        for e,(a,b) in enumerate(owners):
            if (a in idset) != (b in idset) and e not in assigned:
                raise AssertionError('unfixed open boundary')
        if len(ids)<=leaf_factors or not active:
            if len(active)>max_leaf_edges:
                raise ResourceLimit('leaf has too many free edges')
            total=0
            # avoid imported itertools.product; bit order matches Factor.value
            for mask in range(1<<len(active)):
                if (mask & 255)==0: check_budget()
                stats.leaf_assignments+=1
                values=dict(assigned)
                values.update({e:(mask>>i)&1 for i,e in enumerate(active)})
                p=1
                for fid in ids:
                    f=net.factors[fid]
                    slot=sum(1<<i for i,e in enumerate(f.ports) if values[e])
                    p*=f.table[slot]
                    if not p: break
                total+=p
                if modulus is not None:total%=modulus
        else:
            plan=plans.get(ids)
            if plan is None:
                plan=_plan(ids,owners)
                plans[ids]=plan
                stats.optimized_partitions+=1
            if len(plan.cut_edges)>max_cut_edges:
                raise ResourceLimit('separator exceeds cut-edge budget')
            stats.max_separator_edges=max(stats.max_separator_edges,len(plan.cut_edges))
            total=0
            for mask in range(1<<len(plan.cut_edges)):
                if (mask & 63)==0:check_budget()
                stats.branch_assignments+=1
                assigned_next=dict(assigned)
                assigned_next.update({e:(mask>>i)&1 for i,e in enumerate(plan.cut_edges)})
                lf=tuple(sorted((e,v) for e,v in assigned_next.items()
                                if any(e in net.factors[i].ports for i in plan.left)))
                rf=tuple(sorted((e,v) for e,v in assigned_next.items()
                                if any(e in net.factors[i].ports for i in plan.right)))
                left=rec(plan.left,lf,depth+1)
                if left:
                    right=rec(plan.right,rf,depth+1)
                    total+=left*right
                    if modulus is not None: total%=modulus
        cache[key]=total
        return total

    result=rec(tuple(range(len(net.factors))),tuple(),0)
    return result,stats
