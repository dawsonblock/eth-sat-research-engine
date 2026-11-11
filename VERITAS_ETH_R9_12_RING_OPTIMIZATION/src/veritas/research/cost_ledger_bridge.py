"""Bridge R9 recursive executors to CostLedger (observational only)."""
from __future__ import annotations

from contextlib import contextmanager

from veritas.research.cost_ledger import CostLedger
from veritas.research.parent_child_r98.model import Budget, Policy


class RecursiveVisitTracker:
    """Track recursive visits, cache reuse and child frames without replacing Budget."""

    def __init__(self, policy: Policy):
        if type(policy) is not Policy:
            raise TypeError('Policy required')
        self.ledger = CostLedger(max_tree_work=policy.max_work)
        self._stack: list[CostLedger] = [self.ledger]
        self._keys: set[str] = set()
        self.recursive_requests = 0
        self.leaf_evaluations = 0

    def request(self) -> None:
        self.recursive_requests += 1
        self._stack[-1].tick('recursive_request', 1)

    def cache_lookup(self, key: str, *, hit: bool) -> None:
        self.ledger.record_cache(hit=hit)
        self._stack[-1].tick('cache_lookup', 1)
        if not hit and key not in self._keys:
            self._keys.add(key)
            self.ledger.note_unique_subproblem()

    def note_leaf(self) -> None:
        self.leaf_evaluations += 1
        self._stack[-1].tick('leaf', 1)

    def charge(self, category: str, units: int = 1) -> None:
        self._stack[-1].tick(category, units)

    @contextmanager
    def child_frame(self):
        child = self._stack[-1].child()
        self._stack.append(child)
        try:
            yield child
        finally:
            self._stack.pop()

    def finalize(self, budget: Budget) -> dict:
        report = self.ledger.report()
        report['recursive_requests'] = self.recursive_requests
        report['leaf_evaluations'] = self.leaf_evaluations
        report['budget_work_units'] = budget.work
        report['observational_only'] = True
        report['complexity_claim'] = False
        return report
