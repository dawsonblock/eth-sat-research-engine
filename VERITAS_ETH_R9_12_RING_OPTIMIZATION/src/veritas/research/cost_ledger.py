"""Exact resource ledger for recursive exact counting experiments.

Aggregates local work, child ledgers, cache statistics, and optional
tree-wide caps. Intended for engineering measurement, not complexity proofs.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from time import monotonic


@dataclass
class CostLedger:
    max_tree_work: int | None = None
    local: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    children: list['CostLedger'] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    unique_subproblems: int = 0
    depth: int = 0
    _started: float = field(default_factory=monotonic, repr=False)

    def tick(self, category: str, units: int = 1) -> None:
        if type(units) is not int or units < 0:
            raise ValueError('nonnegative integer work units required')
        if not category:
            raise ValueError('category required')
        self.local[category] += units
        if self.max_tree_work is not None and self.total_work > self.max_tree_work:
            raise RuntimeError('recursive tree work budget exceeded')

    def child(self) -> 'CostLedger':
        child = CostLedger(max_tree_work=self.max_tree_work, depth=self.depth + 1)
        self.children.append(child)
        return child

    def record_cache(self, *, hit: bool) -> None:
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def note_unique_subproblem(self) -> None:
        self.unique_subproblems += 1

    @property
    def local_work(self) -> int:
        return sum(self.local.values())

    @property
    def total_work(self) -> int:
        return self.local_work + sum(c.total_work for c in self.children)

    @property
    def recursion_depth(self) -> int:
        if not self.children:
            return self.depth
        return max(c.recursion_depth for c in self.children)

    @property
    def elapsed_seconds(self) -> float:
        return monotonic() - self._started

    @staticmethod
    def cache_profitable(*, appearances: int, eval_cost: int, lookup_cost: int, key_cost: int) -> bool:
        """(q-1)c > qℓ + h from the engineering plan."""
        if appearances < 2:
            return False
        return (appearances - 1) * eval_cost > appearances * lookup_cost + key_cost

    def report(self) -> dict:
        hits = self.cache_hits
        misses = self.cache_misses
        return {
            'schema': 'VERITAS_COST_LEDGER_V1',
            'local_work': self.local_work,
            'total_work': self.total_work,
            'local_by_category': dict(self.local),
            'child_count': len(self.children),
            'cache_hits': hits,
            'cache_misses': misses,
            'cache_hit_rate': hits / (hits + misses) if hits + misses else None,
            'unique_subproblems': self.unique_subproblems,
            'recursion_depth': self.recursion_depth,
            'elapsed_seconds': round(self.elapsed_seconds, 6),
            'max_tree_work': self.max_tree_work,
            'complexity_claim': False,
        }
