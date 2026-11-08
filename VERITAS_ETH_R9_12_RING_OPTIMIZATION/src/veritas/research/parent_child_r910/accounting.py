"""Exclusive deterministic work charges, explicitly separate from bit cost."""
from contextlib import contextmanager
import resource
import sys
from time import monotonic

from veritas.research.parent_child_r98.model import Budget, Refusal
from veritas.research.independent_r82.point_mode_oracle import OracleLimits


class AccountedBudget(Budget):
    def __init__(self, policy, oracle_limits=None):
        super().__init__(policy)
        self.oracle_limits = (OracleLimits(min(5_000_000, policy.max_work), policy.max_seconds)
                              if oracle_limits is None else oracle_limits)
        if type(self.oracle_limits) is not OracleLimits:
            raise TypeError('validated OracleLimits required')
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
        try:
            super().tick(n)
        except Refusal as exc:
            work = self.work > self.policy.max_work
            exc.resource_failure = {'scope':'overall '+self.stage,
                'resource':'WORK_UNITS' if work else 'WALL_TIME_US', 'limit_scope':'GLOBAL',
                'limit':self.policy.max_work if work else self.policy.max_seconds*1_000_000,
                'observed':self.work if work else int((monotonic()-self.started)*1_000_000)}
            raise

    @contextmanager
    def at(self, stage):
        previous, self.stage = self.stage, stage
        try:
            yield
        finally:
            self.stage = previous

    def report(self):
        return {**super().report(), 'oracle_policy':self.oracle_limits.record(),
                'oracle_clock_scope':'METER_LIFETIME_INCLUDING_NESTED_COMPUTATION',
                'stage_work_units': dict(sorted(self.charges.items())),
                'stage_sum_reconciles': sum(self.charges.values()) == self.work,
                'bit_operations': None, 'bit_operation_measurement': 'NOT_INSTRUMENTED',
                'process_peak_rss_bytes': self.rss(), 'process_peak_rss_before_bytes': self.rss_before,
                'rss_scope': 'PROCESS_HIGH_WATER_INCLUDES_IMPORTS_AND_PRIOR_WORK'}
