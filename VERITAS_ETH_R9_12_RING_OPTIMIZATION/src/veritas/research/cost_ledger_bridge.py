"""Bridge R9 recursive executors to CostLedger (observational only)."""
from __future__ import annotations

from contextlib import contextmanager

from veritas.research.bit_operation_ledger import (
    BITS_PER_CACHE_KEY_BYTE,
    BITS_PER_CACHE_LOOKUP,
    BITS_PER_JET_MUL_EVENT,
    BITS_PER_LEAF,
    BITS_PER_RECURSIVE_REQUEST,
    BitOperationLedger,
)
from veritas.research.cost_ledger import CostLedger
from veritas.research.parent_child_r98.model import Budget, Policy


class RecursiveVisitTracker:
    """Track recursive visits, cache reuse and child frames without replacing Budget."""

    def __init__(self, policy: Policy):
        if type(policy) is not Policy:
            raise TypeError('Policy required')
        self.ledger = CostLedger(max_tree_work=policy.max_work)
        self.bit_ops = BitOperationLedger()
        self._stack: list[CostLedger] = [self.ledger]
        self._bit_stack: list[BitOperationLedger] = [self.bit_ops]
        self._keys: set[str] = set()
        self.recursive_requests = 0
        self.leaf_evaluations = 0

    def request(self) -> None:
        self.recursive_requests += 1
        self._stack[-1].tick('recursive_request', 1)
        self._bit_stack[-1].charge('recursive_request', BITS_PER_RECURSIVE_REQUEST)

    def cache_lookup(self, key: str, *, hit: bool) -> None:
        self.ledger.record_cache(hit=hit)
        self._stack[-1].tick('cache_lookup', 1)
        self._bit_stack[-1].charge(
            'cache_lookup',
            BITS_PER_CACHE_LOOKUP + len(key) * BITS_PER_CACHE_KEY_BYTE,
        )
        if not hit and key not in self._keys:
            self._keys.add(key)
            self.ledger.note_unique_subproblem()

    def note_leaf(self) -> None:
        self.leaf_evaluations += 1
        self._stack[-1].tick('leaf', 1)
        self._bit_stack[-1].charge('leaf', BITS_PER_LEAF)

    def charge(self, category: str, units: int = 1) -> None:
        self._stack[-1].tick(category, units)
        if category == 'jet_mul':
            self._bit_stack[-1].charge('jet_mul', units * BITS_PER_JET_MUL_EVENT)

    @contextmanager
    def child_frame(self):
        child = self._stack[-1].child()
        bit_child = self._bit_stack[-1].child()
        self._stack.append(child)
        self._bit_stack.append(bit_child)
        try:
            yield child
        finally:
            self._stack.pop()
            self._bit_stack.pop()

    def finalize(self, budget: Budget) -> dict:
        report = self.ledger.report()
        report['recursive_requests'] = self.recursive_requests
        report['leaf_evaluations'] = self.leaf_evaluations
        report['budget_work_units'] = budget.work
        report['observational_only'] = True
        report['complexity_claim'] = False
        bit_report = self.bit_ops.report()
        report['bit_operations'] = bit_report['total_bits']
        report['bit_operation_detail'] = bit_report
        return report
