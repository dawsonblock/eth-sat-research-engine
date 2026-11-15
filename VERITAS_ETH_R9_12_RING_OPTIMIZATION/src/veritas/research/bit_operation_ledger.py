"""Conservative bit-operation proxy for recursive R9 experiments (not cycle-accurate)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BitOperationLedger:
    """Accumulate category bit costs; children roll into parent totals."""

    local: dict[str, int] = field(default_factory=dict)
    children: list['BitOperationLedger'] = field(default_factory=list)
    depth: int = 0

    def charge(self, category: str, bits: int) -> None:
        if type(bits) is not int or bits < 0:
            raise ValueError('nonnegative integer bits required')
        if not category:
            raise ValueError('category required')
        self.local[category] = self.local.get(category, 0) + bits

    def child(self) -> 'BitOperationLedger':
        child = BitOperationLedger(depth=self.depth + 1)
        self.children.append(child)
        return child

    @property
    def total_bits(self) -> int:
        return sum(self.local.values()) + sum(c.total_bits for c in self.children)

    def report(self) -> dict:
        return {
            'schema': 'VERITAS_BIT_OP_LEDGER_V1',
            'local_bits': sum(self.local.values()),
            'total_bits': self.total_bits,
            'local_by_category': dict(sorted(self.local.items())),
            'child_frames': len(self.children),
            'max_depth': max(
                [self.depth] + [c.report()['max_depth'] for c in self.children],
                default=self.depth,
            ),
            'measurement': 'PROXY_INSTRUMENTED_V1',
            'complexity_claim': False,
        }


# Engineering defaults (explicitly coarse).
BITS_PER_RECURSIVE_REQUEST = 256
BITS_PER_CACHE_LOOKUP = 128
BITS_PER_CACHE_KEY_BYTE = 8
BITS_PER_LEAF = 4096
BITS_PER_JET_MUL_EVENT = 64
