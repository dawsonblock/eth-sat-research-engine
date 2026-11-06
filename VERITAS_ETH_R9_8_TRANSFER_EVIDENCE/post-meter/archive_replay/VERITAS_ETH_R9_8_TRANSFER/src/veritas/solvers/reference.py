"""Bounded, transparent reference SAT/#SAT solver. Intended for modest CNFs.

Counting uses unit propagation only: pure literal elimination would be UNSOUND
for #SAT. Branching and leaf factors preserve unused declared variables.
"""
from __future__ import annotations
from dataclasses import dataclass
import time
from veritas.core.cnf import CNF


class ResourceLimit(Exception):
    pass


@dataclass
class SearchResult:
    status: str
    model: dict[int, bool] | None = None
    count: int | None = None
    nodes: int = 0
    seconds: float = 0.0
    reason: str | None = None


class _Search:
    def __init__(self, cnf: CNF, seconds: float, max_nodes: int):
        self.cnf = cnf
        self.deadline = time.monotonic() + seconds
        self.nodes = 0
        self.max_nodes = max_nodes
        self.started = time.monotonic()

    def guard(self):
        self.nodes += 1
        if self.nodes > self.max_nodes or time.monotonic() > self.deadline:
            raise ResourceLimit("search budget exceeded")

    def propagate(self, clauses: tuple[tuple[int, ...], ...], model: dict[int, bool]):
        """Return simplified clauses/model, or None when contradicted."""
        while True:
            self.guard()
            changed = False
            new_clauses = []
            for clause in clauses:
                unknown = []
                satisfied = False
                for lit in clause:
                    v = abs(lit)
                    if v in model:
                        if model[v] == (lit > 0):
                            satisfied = True
                            break
                    else:
                        unknown.append(lit)
                if satisfied:
                    continue
                if not unknown:
                    return None
                if len(unknown) == 1:
                    lit = unknown[0]
                    key, truth = abs(lit), lit > 0
                    if key in model and model[key] != truth:
                        return None
                    if key not in model:
                        model[key] = truth
                        changed = True
                new_clauses.append(tuple(unknown))
            clauses = tuple(new_clauses)
            if not changed:
                return clauses, model

    def _branch(self, clauses, model, counting):
        stack = [(clauses, dict(model))]
        count = 0
        while stack:
            self.guard()
            current, assignment = stack.pop()
            propagated = self.propagate(current, assignment)
            if propagated is None:
                continue
            current, assignment = propagated
            if not current:
                if counting:
                    count += 1 << (self.cnf.n - len(assignment))
                    continue
                return {v: assignment.get(v, False) for v in range(1, self.cnf.n + 1)}
            literal = min(current, key=len)[0]
            key = abs(literal)
            # LIFO order preserves the previous search's preferred first branch.
            first = True if counting else literal > 0
            stack.append((current, {**assignment, key: not first}))
            stack.append((current, {**assignment, key: first}))
        return count if counting else None

    def solve(self, counting):
        try:
            # Duplicate literals and tautological clauses can otherwise cause
            # unnecessary branching even though they impose no new condition.
            normalized = []
            for clause in self.cnf.clauses:
                unique = tuple(dict.fromkeys(clause))
                literals = set(unique)
                if not any(-lit in literals for lit in unique):
                    normalized.append(unique)
            result = self._branch(tuple(normalized), {}, counting)
            if counting:
                return SearchResult("COUNT", count=result, nodes=self.nodes, seconds=time.monotonic()-self.started)
            return SearchResult("SAT" if result is not None else "UNSAT", model=result, nodes=self.nodes, seconds=time.monotonic()-self.started)
        except ResourceLimit as exc:
            return SearchResult("UNKNOWN", nodes=self.nodes, seconds=time.monotonic()-self.started, reason=str(exc))


def solve(cnf: CNF, *, count: bool = False, timeout_s: float = 4.0, max_nodes: int = 150_000) -> SearchResult:
    if not (0 < timeout_s <= 30):
        raise ValueError("timeout_s must be in (0, 30]")
    if not (1 <= max_nodes <= 2_000_000):
        raise ValueError("max_nodes must be 1..2,000,000")
    return _Search(cnf, timeout_s, max_nodes).solve(count)


def exhaustive_count(cnf: CNF, *, max_vars: int = 18) -> int:
    if cnf.n > max_vars:
        raise ValueError(f"exhaustive oracle requires at most {max_vars} variables")
    return sum(cnf.evaluate({i + 1: bool(mask >> i & 1) for i in range(cnf.n)}) for mask in range(1 << cnf.n))
