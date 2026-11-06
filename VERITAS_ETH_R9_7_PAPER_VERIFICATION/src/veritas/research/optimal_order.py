"""Exhaustive subset-DP elimination-order optimization for SMALL factor graphs.

This is an exact combinatorial optimization of the stated dense contraction
cost proxy, NOT a subexponential SAT solver or a proof of paper D.4.4.

For any eliminated vertex subset S, the fill graph on V\\S is independent of
which order was used to eliminate S: two remaining vertices become adjacent
iff their original vertices are connected through a path whose internal
vertices are all in S.  This permits subset DP instead of n! permutations.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from time import monotonic
from veritas.research.contraction_planner import (ContractLimit, ContractionPlan,
                                                   FactorModel)
from veritas.research.graph_decomposition import primal_graph, from_elimination_order


MAX_OPTIMAL_VERTICES = 12


@dataclass(frozen=True)
class OptimalityEvidence:
    objective: str
    states_evaluated: int
    exhaustive_subset_states: int
    model_vertices: int
    optimal_cost_proxy: int
    induced_width: int
    certificate_type: str = 'EXACT_SUBSET_DYNAMIC_PROGRAM_RECOMPUTABLE'


def replay_order(model: FactorModel, order: tuple[int, ...]) -> tuple[int, int]:
    """Independently replay graph fill and report (dense work, peak width)."""
    if len(order) != len(model.variables) or set(order) != set(model.variables):
        raise ValueError('invalid elimination permutation')
    graph = primal_graph(model.variables, model.factors)
    working = {v: set(neighbors) for v, neighbors in graph.items()}
    cost = 0
    peak = 0
    for vertex in order:
        neighbors = sorted(working.pop(vertex))
        degree = len(neighbors)
        peak = max(peak, degree)
        cost += 1 << (degree + 1)
        for u in neighbors:
            working[u].discard(vertex)
            working[u].update(set(neighbors) - {u})
    return cost, peak


def optimize_small_model(model: FactorModel, *, objective: str = 'work',
                         max_vertices: int = MAX_OPTIMAL_VERTICES,
                         deadline: float | None = None) -> tuple[ContractionPlan, OptimalityEvidence]:
    """Find a global optimum for either dense work or induced width.

    objective='work' minimizes SUM 2**(degree+1), and then peak degree.
    objective='width' minimizes peak degree, then work among all orders
    achieving the globally minimum width. Both are exact for the model's
    undirected primal graph, not predictions of real runtime.

    Restrict to <=12 vertices so the worst-case 2**n subset search is bounded.
    Time limits fail closed; no incomplete optimizer output is published.
    """
    if objective not in ('work', 'width'):
        raise ValueError('objective must be work or width')
    if type(max_vertices) is not int or not 0 <= max_vertices <= MAX_OPTIMAL_VERTICES:
        raise ValueError('max_vertices must be in 0..12')
    variables = tuple(sorted(model.variables))
    n = len(variables)
    if n > max_vertices:
        raise ContractLimit(f'certified order search requires <= {max_vertices} wires; got {n}')
    if deadline is not None and monotonic() > deadline:
        raise ContractLimit('optimal planning deadline exceeded')
    graph = primal_graph(model.variables, model.factors)
    where = {v: i for i, v in enumerate(variables)}
    adjacency = tuple(sum(1 << where[u] for u in graph[v]) for v in variables)
    full = (1 << n) - 1
    examined = 0

    def check():
        nonlocal examined
        examined += 1
        if deadline is not None and (examined & 31) == 1 and monotonic() > deadline:
            raise ContractLimit('optimal planning deadline exceeded')

    def degree_after_eliminating(mask: int, vertex: int) -> int:
        """Number of remaining neighbors after eliminating exactly `mask`."""
        bit = 1 << vertex
        direct = adjacency[vertex]
        left = full & ~mask & ~bit
        neighbors = direct & left
        visited = 0
        pending = direct & mask
        while pending:
            low = pending & -pending
            pending ^= low
            if visited & low:
                continue
            visited |= low
            index = low.bit_length() - 1
            neighbors |= adjacency[index] & left
            pending |= adjacency[index] & mask & ~visited
        return neighbors.bit_count()

    @lru_cache(maxsize=None)
    def min_work(mask: int) -> tuple[int, int, tuple[int, ...]]:
        check()
        if mask == full:
            return (0, 0, ())
        best = None
        for i in range(n):
            if mask & (1 << i):
                continue
            d = degree_after_eliminating(mask, i)
            work, width, suffix = min_work(mask | (1 << i))
            candidate = (work + (1 << (d + 1)), max(d, width), (i,) + suffix)
            if best is None or candidate < best:
                best = candidate
        assert best is not None
        return best

    @lru_cache(maxsize=None)
    def minimum_width(mask: int) -> int:
        check()
        if mask == full:
            return 0
        return min(max(degree_after_eliminating(mask, i), minimum_width(mask | (1 << i)))
                   for i in range(n) if not mask & (1 << i))

    if objective == 'work':
        cost, width, indices = min_work(0)
    else:
        width = minimum_width(0)

        @lru_cache(maxsize=None)
        def work_under_width(mask: int) -> tuple[int, tuple[int, ...]] | None:
            check()
            if mask == full:
                return (0, ())
            best = None
            for i in range(n):
                if mask & (1 << i):
                    continue
                degree = degree_after_eliminating(mask, i)
                if degree > width:
                    continue
                suffix = work_under_width(mask | (1 << i))
                if suffix is None:
                    continue
                candidate = (suffix[0] + (1 << (degree + 1)), (i,) + suffix[1])
                if best is None or candidate < best:
                    best = candidate
            return best

        optimum = work_under_width(0)
        if optimum is None:
            raise AssertionError('width optimization produced no valid order')
        cost, indices = optimum

    order = tuple(variables[i] for i in indices)
    independent_cost, independent_width = replay_order(model, order)
    if (independent_cost, independent_width) != (cost, width):
        raise AssertionError('optimal subset DP disagrees with graph-fill replay')
    tree = from_elimination_order(graph, order)
    if tree.width != width:
        raise AssertionError('tree decomposition width does not match replay')
    plan = ContractionPlan(model.representation, 'exact_subset_dp_' + objective,
                           order, width, 1 << width, cost, True)
    evidence = OptimalityEvidence(objective, examined, 1 << n, n, cost, width)
    return plan, evidence
