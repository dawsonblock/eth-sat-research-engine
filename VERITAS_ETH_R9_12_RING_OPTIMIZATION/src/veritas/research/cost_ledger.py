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
    # Ledgers made by child() share the cap of the ledger at the top of their tree.
    _root: 'CostLedger | None' = field(default=None, repr=False, compare=False)
    _tree_charged: int = field(default=0, repr=False, compare=False)

    def tick(self, category: str, units: int = 1) -> None:
        if type(units) is not int or units < 0:
            raise ValueError('nonnegative integer work units required')
        if not category:
            raise ValueError('category required')
        root = self if self._root is None else self._root
        self.local[category] += units
        root._tree_charged += units
        if root.max_tree_work is not None and root._tree_charged > root.max_tree_work:
            raise RuntimeError('recursive tree work budget exceeded')

    def child(self) -> 'CostLedger':
        root = self if self._root is None else self._root
        child = CostLedger(max_tree_work=root.max_tree_work, depth=self.depth + 1, _root=root)
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
    def tree_cache_hits(self) -> int:
        return self.cache_hits + sum(c.tree_cache_hits for c in self.children)

    @property
    def tree_cache_misses(self) -> int:
        return self.cache_misses + sum(c.tree_cache_misses for c in self.children)

    @property
    def tree_unique_subproblems(self) -> int:
        return self.unique_subproblems + sum(c.tree_unique_subproblems for c in self.children)

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
        tree_hits = self.tree_cache_hits
        tree_misses = self.tree_cache_misses
        return {
            'schema': 'VERITAS_COST_LEDGER_V1',
            'local_work': self.local_work,
            'total_work': self.total_work,
            'local_by_category': dict(self.local),
            'child_count': len(self.children),
            'cache_hits': hits,
            'cache_misses': misses,
            # Integer parts-per-million: execution reports must stay float-free except for
            # elapsed-time metadata, so a float hit rate would break canonical replay.
            'cache_hit_rate_ppm': (hits * 1_000_000) // (hits + misses) if hits + misses else None,
            'unique_subproblems': self.unique_subproblems,
            # The three keys above are this ledger's own; these include every descendant.
            'tree_cache_hits': tree_hits,
            'tree_cache_misses': tree_misses,
            'tree_cache_hit_rate_ppm': ((tree_hits * 1_000_000) // (tree_hits + tree_misses)
                                        if tree_hits + tree_misses else None),
            'tree_unique_subproblems': self.tree_unique_subproblems,
            'recursion_depth': self.recursion_depth,
            'elapsed_seconds': round(self.elapsed_seconds, 6),
            'max_tree_work': self.max_tree_work,
            'complexity_claim': False,
        }
