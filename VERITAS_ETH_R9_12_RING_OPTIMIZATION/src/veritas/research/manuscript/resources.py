"""Cooperative execution limits, without changing mathematical parameters."""
from dataclasses import dataclass
from time import monotonic


class ResourceLimit(RuntimeError):
    pass


@dataclass(frozen=True)
class Limits:
    max_work: int | None = 10_000_000
    max_seconds: float | None = 300
    max_items: int | None = 2_000_000
    max_integer_bits: int | None = 1_000_000

    def __post_init__(self):
        for name in ('max_work', 'max_items', 'max_integer_bits'):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError('positive integer or None required: '+name)
        if self.max_seconds is not None and (type(self.max_seconds) not in (int, float)
                                             or not 0 < self.max_seconds < float('inf')):
            raise ValueError('positive finite time limit or None required')


class Budget:
    def __init__(self, limits=Limits()):
        self.limits = limits
        self.started = monotonic()
        self.work = 0
        self.calls = self.points = self.tuples = self.max_depth = 0

    def tick(self, amount=1):
        if type(amount) is not int or amount < 0:
            raise ValueError('nonnegative work charge required')
        self.work += amount
        if self.limits.max_work is not None and self.work > self.limits.max_work:
            raise ResourceLimit('operation allowance exhausted')
        if self.limits.max_seconds is not None and monotonic()-self.started > self.limits.max_seconds:
            raise ResourceLimit('elapsed-time allowance exhausted')

    def items(self, count, what):
        self.tick(0)
        if self.limits.max_items is not None and count > self.limits.max_items:
            raise ResourceLimit(what+' exceeds allocation item allowance')

    def bits(self, count, what):
        self.tick(0)
        if self.limits.max_integer_bits is not None and count > self.limits.max_integer_bits:
            raise ResourceLimit(what+' exceeds integer bit allowance')

    def report(self):
        return dict(work_units=self.work, elapsed_seconds=monotonic()-self.started,
                    calls=self.calls, interpolation_points=self.points,
                    exponent_tuples=self.tuples, maximum_depth=self.max_depth,
                    bit_operations=None, hard_memory_limit_enforced=False)
