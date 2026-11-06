"""Deterministic, dependency-free graph planning primitives.

A *primal graph* puts an edge between every pair of variables occurring in
one factor scope. Tree decompositions are checked rather than assumed valid.
These heuristics do not establish bounded treewidth for arbitrary CNF.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from veritas.research.tensor import Factor


def primal_graph(variables: tuple[int, ...], factors: tuple[Factor, ...]) -> dict[int, set[int]]:
    graph = {v: set() for v in variables}
    for f in factors:
        if any(v not in graph for v in f.ports):
            raise ValueError('factor contains an undeclared variable')
        for v in f.ports:
            graph[v].update(set(f.ports)-{v})
    return graph


def components(graph: dict[int, set[int]], excluded: frozenset[int] = frozenset()) -> tuple[tuple[int, ...], ...]:
    remaining = set(graph) - excluded
    result = []
    while remaining:
        seed = min(remaining)
        visited = {seed}
        stack = [seed]
        while stack:
            for nb in graph[stack.pop()] - excluded:
                if nb not in visited:
                    visited.add(nb)
                    stack.append(nb)
        remaining.difference_update(visited)
        result.append(tuple(sorted(visited)))
    return tuple(result)


@dataclass(frozen=True)
class Separator:
    variables: tuple[int, ...]
    components: tuple[tuple[int, ...], ...]
    largest_component: int


def small_separator(graph: dict[int, set[int]], max_size: int = 2,
                    max_vertices: int = 96, candidate_limit: int = 18) -> Separator | None:
    """Find a nontrivial separating set of size <=max_size, with search caps.

    Exhaustively checks singleton cuts; for larger cuts considers a deterministic
    subset of high-degree and low-degree vertices, not an optimality certificate.
    """
    if not 1 <= max_size <= 3:
        raise ValueError('separator size must be 1..3')
    if len(graph) > max_vertices or len(graph) < 3 or len(components(graph)) != 1:
        return None
    ranked = sorted(graph, key=lambda v: (-len(graph[v]), v))
    candidates = sorted(set(ranked[:candidate_limit] + ranked[-min(candidate_limit//2,len(ranked)):]))
    best = None
    for k in range(1, min(max_size, len(graph)-2) + 1):
        search = sorted(graph) if k == 1 else candidates
        for cut in combinations(search, k):
            groups = components(graph, frozenset(cut))
            if len(groups) <= 1:
                continue
            largest = max(map(len, groups))
            # Prefer small cuts first, then balanced decomposition.
            score = (k, largest, cut)
            if best is None or score < best[0]:
                best = (score, Separator(cut, groups, largest))
        if best is not None:
            break
    return best[1] if best else None


@dataclass(frozen=True)
class TreeDecomposition:
    bags: tuple[tuple[int, ...], ...]
    parent: tuple[int | None, ...]
    width: int


def from_elimination_order(graph: dict[int, set[int]], order: tuple[int, ...]) -> TreeDecomposition:
    """Elimination bags with an elimination-forest parent relation."""
    if len(order) != len(graph) or set(order) != set(graph):
        raise ValueError('order must be a permutation of graph vertices')
    working = {v: set(ns) for v, ns in graph.items()}
    positions = {v:i for i,v in enumerate(order)}
    bags = []
    parent = []
    for v in order:
        ns = sorted(working[v])
        bags.append(tuple(sorted((v, *ns))))
        parent.append(positions[min(ns, key=positions.get)] if ns else None)
        for i,u in enumerate(ns):
            working[u].discard(v)
            working[u].update(ns[:i] + ns[i+1:])
        del working[v]
    result = TreeDecomposition(tuple(bags), tuple(parent), max((len(b)-1 for b in bags), default=0))
    if not verify_decomposition(graph, result):
        raise AssertionError('invalid elimination tree decomposition')
    return result


def verify_decomposition(graph: dict[int, set[int]], decomposition: TreeDecomposition) -> bool:
    """Check bag coverage, graph edges, acyclic bag forest, running intersection."""
    bags, parents = decomposition.bags, decomposition.parent
    n = len(bags)
    if len(parents) != n or any(p is not None and (p == i or p < 0 or p >= n)
                                    for i,p in enumerate(parents)):
        return False
    all_vertices = set().union(*(set(b) for b in bags)) if bags else set()
    if all_vertices != set(graph):
        return False
    if any(not any(u in bag and v in bag for bag in bags)
           for u,ns in graph.items() for v in ns):
        return False
    adjacency = [set() for _ in bags]
    for i,p in enumerate(parents):
        if p is not None:
            adjacency[i].add(p); adjacency[p].add(i)
    # A forest requires exactly one fewer edge than vertices per component.
    found = set()
    for i in range(n):
        if i in found: continue
        stack = [(i, None)]
        while stack:
            j, prior = stack.pop()
            if j in found: return False
            found.add(j)
            stack.extend((k, j) for k in adjacency[j] if k != prior)
    for v in graph:
        contains = {i for i,b in enumerate(bags) if v in b}
        seen={min(contains)}; queue=[min(contains)]
        while queue:
            j=queue.pop()
            for k in adjacency[j] & contains - seen:
                seen.add(k); queue.append(k)
        if seen != contains: return False
    return decomposition.width == max((len(b)-1 for b in bags), default=0)
