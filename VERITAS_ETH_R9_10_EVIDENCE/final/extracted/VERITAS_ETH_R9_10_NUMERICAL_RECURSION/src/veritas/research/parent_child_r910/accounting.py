"""Exclusive deterministic work charges, explicitly separate from bit cost."""
from contextlib import contextmanager
import resource
import sys

from veritas.research.parent_child_r98.model import Budget


class AccountedBudget(Budget):
    def __init__(self, policy):
        super().__init__(policy)
        self.stage = 'control'
        self.charges = {}
        self.rss_before = self.rss()

    @staticmethod
    def rss():
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return raw if sys.platform == 'darwin' else raw*1024

    def tick(self, n=1):
        if type(n) is not int or n < 0:
            raise ValueError('nonnegative work charge required')
        self.charges[self.stage] = self.charges.get(self.stage, 0)+n
        super().tick(n)

    @contextmanager
    def at(self, stage):
        previous, self.stage = self.stage, stage
        try:
            yield
        finally:
            self.stage = previous

    def report(self):
        return {**super().report(), 'stage_work_units': dict(sorted(self.charges.items())),
                'stage_sum_reconciles': sum(self.charges.values()) == self.work,
                'bit_operations': None, 'bit_operation_measurement': 'NOT_INSTRUMENTED',
                'process_peak_rss_bytes': self.rss(), 'process_peak_rss_before_bytes': self.rss_before,
                'rss_scope': 'PROCESS_HIGH_WATER_INCLUDES_IMPORTS_AND_PRIOR_WORK'}
