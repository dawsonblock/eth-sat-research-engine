"""Total-work ledger for SAT decompositions (research scaffolding).

Implements the accounting identity from docs/UNIVERSAL_SAT_SPEEDUP_PLAN.md:

    W_new = W_transform + sum(W_j) + W_reconstruct + W_check

No universal speedup is claimed until inequalities are proved for the full 3-CNF class.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Optional


@dataclass
class DecompositionWorkLedger:
    """One decomposition step with explicit overhead."""

    name: str
    w_old: int
    w_transform: int = 0
    child_works: tuple[int, ...] = ()
    w_reconstruct: int = 0
    w_check: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def w_new(self) -> int:
        return self.w_transform + sum(self.child_works) + self.w_reconstruct + self.w_check

    @property
    def q(self) -> int:
        return len(self.child_works)

    def speedup_ratio(self) -> Optional[float]:
        if self.w_new <= 0:
            return None
        return self.w_old / self.w_new

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "w_old": self.w_old,
            "w_transform": self.w_transform,
            "child_works": list(self.child_works),
            "w_reconstruct": self.w_reconstruct,
            "w_check": self.w_check,
            "w_new": self.w_new,
            "q": self.q,
            "speedup_ratio": self.speedup_ratio(),
            "metadata": dict(self.metadata),
        }


def toy_child_sum_exponent(*, s: int, rho: float, q: int) -> dict:
    """Toy model: parent 2^s, each child 2^(rho*s), ignore overhead (plan §2)."""
    import math

    w_old = 2**s
    w_child_each = 2 ** (rho * s)
    w_children = q * w_child_each
    ratio = w_old / w_children if w_children else float("inf")
    return {
        "s": s,
        "rho": rho,
        "q": q,
        "w_old": w_old,
        "w_children_total": w_children,
        "speedup_ratio_before_overhead": ratio,
        "break_even_q": 2 ** ((1 - rho) * s) if rho < 1 else None,
    }


def exponential_width_proxy(edges: int, *, cap: int = 48) -> int:
    """Saturating 2^edges proxy for comparing splits (not a theorem bound)."""
    if edges <= 0:
        return 1
    if edges > cap:
        return 2**cap
    return 2**edges


def aggregate_ledger(ledgers: Iterable[DecompositionWorkLedger]) -> dict:
    rows = [x.to_dict() for x in ledgers]
    return {
        "schema": "VERITAS_SAT_WORK_AGGREGATE_V1",
        "steps": rows,
        "w_total_reported": sum(r["w_new"] for r in rows),
        "subexponential_bound_evidence": False,
        "theorem_backed": False,
        "qualification": "ledger_scaffolding_only_not_universal_speedup",
    }


def ledger_totals_summary(ledger_aggregate: Mapping[str, object]) -> dict:
    """Compact totals for CLI / micro-benchmark artifacts."""
    steps = ledger_aggregate.get("steps") or []
    by_name: dict[str, int] = {}
    for row in steps:
        if isinstance(row, dict):
            name = str(row.get("name", "unknown"))
            by_name[name] = by_name.get(name, 0) + int(row.get("w_new", 0))
    return {
        "schema": "VERITAS_LEDGER_TOTALS_V1",
        "step_count": len(steps),
        "w_total_reported": ledger_aggregate.get("w_total_reported"),
        "w_by_step_name": by_name,
    }
