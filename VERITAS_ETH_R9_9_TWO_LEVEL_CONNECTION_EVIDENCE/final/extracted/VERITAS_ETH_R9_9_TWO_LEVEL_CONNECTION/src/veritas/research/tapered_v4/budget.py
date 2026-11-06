"""One shared, cooperative finite-work budget and a scoped event ledger."""
from __future__ import annotations

from collections import Counter
from time import monotonic


class Inconclusive(RuntimeError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status
        self.reason = reason


class WorkBudget:
    def __init__(self, policy):
        self.policy = policy
        self.deadline = monotonic() + policy.max_seconds
        self.used = 0
        self.counters = Counter()
        self.maximum_depth = 0
        self.maximum_precision_bits = 0
        self.maximum_parent_edges = 0
        self.maximum_child_edges = 0
        self.maximum_parent_degree = 0
        self.maximum_child_degree = 0
        self.accumulator_operand_bits = 0
        self.maximum_accumulator_operand_bits = 0
        self.mode_counts_by_weight = Counter()

    def check(self):
        if monotonic() >= self.deadline:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'cooperative deadline exhausted')

    def charge(self, name, amount=1):
        self.check()
        if type(amount) is not int or amount < 0:
            raise ValueError('nonnegative integer work charge required')
        if self.used + amount > self.policy.max_work:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'observed work-unit budget exhausted')
        self.used += amount
        self.counters[name] += amount

    def record_interrupted_work(self, name, amount):
        """Record already-observed subcall work even after its deadline expires.

        This does not authorize more work and cannot exceed the parent budget.
        Subcalls report cooperative work units, not complete bit-operation cost.
        """
        if amount is None:
            return
        if type(amount) is not int or amount < 0:
            raise ValueError('nonnegative interrupted work required')
        amount = min(amount, self.policy.max_work - self.used)
        self.used += amount
        self.counters[name] += amount

    def remaining(self):
        self.check()
        available = self.policy.max_work - self.used
        if available < 1:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'observed work-unit budget exhausted')
        seconds = self.deadline - monotonic()
        if seconds <= 0:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'cooperative deadline exhausted')
        return min(available, 2_000_000), min(seconds, 30.0)

    def accumulator_operation(self, kind, left, right):
        self.charge(kind)
        bits = sum(max(1, value.bit_length()) for element in (left, right)
                   for coefficient in element for value in coefficient)
        self.accumulator_operand_bits += bits
        self.maximum_accumulator_operand_bits = max(self.maximum_accumulator_operand_bits, bits)

    def snapshot(self):
        return {'observed_work_units': self.used, 'counters': dict(sorted(self.counters.items())),
                'maximum_depth': self.maximum_depth,
                'maximum_precision_bits': self.maximum_precision_bits,
                'maximum_parent_edges': self.maximum_parent_edges,
                'maximum_child_edges': self.maximum_child_edges,
                'maximum_parent_degree': self.maximum_parent_degree,
                'maximum_child_degree': self.maximum_child_degree,
                'accumulator_operand_bits': self.accumulator_operand_bits,
                'maximum_accumulator_operand_bits': self.maximum_accumulator_operand_bits,
                'mode_counts_by_weight': sorted(self.mode_counts_by_weight.items()),
                'complete': False,
                'unmeasured': ['internal mode and packing verification arithmetic',
                               'source Hermite plan generation and verification bit costs',
                               'child recipe replay bit costs and allocation',
                               'independent tuple oracle mode and source replay',
                               'independent tuple checker integer bit costs and allocation',
                               'nominal weighted-tuple dynamic-programming work',
                               'Hall matching bit costs and allocation when enabled',
                               'child topology replay work and allocation', 'interpolation bit operations',
                               'tensor-description allocation', 'peak process memory'],
                'hard_memory_limit_enforced': False}
