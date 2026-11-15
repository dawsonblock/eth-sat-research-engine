#!/usr/bin/env python3
"""Engineering gates: two-level R9 runs expose tree ledger + proxy bit operations."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from veritas.research.cost_ledger_bridge import RecursiveVisitTracker
from veritas.research.parent_child_r98.model import Budget, DEFAULT_POLICY


def _ledger_smoke() -> dict:
    policy = DEFAULT_POLICY
    tracker = RecursiveVisitTracker(policy)
    tracker.request()
    tracker.cache_lookup('alpha', hit=False)
    tracker.cache_lookup('alpha', hit=True)
    tracker.note_leaf()
    with tracker.child_frame():
        tracker.request()
        tracker.charge('jet_mul', 4)
    budget = Budget(policy)
    budget.tick(5)
    tree = tracker.finalize(budget)
    assert tree['bit_operations'] and tree['bit_operations'] > 0
    assert tree['bit_operation_detail']['measurement'] == 'PROXY_INSTRUMENTED_V1'
    return tree


def _two_level_flag() -> dict:
    return {
        'source_qualified_required_false': True,
        'bit_operations_on_tree_ledger_not_work_ledger': True,
        'theorem_mode_required_false': True,
        'note': 'Full manuscript two-level gate remains validate_v39_two_level_audit.py',
    }


def main() -> int:
    out = ROOT / 'validation' / 'r9_execution_cost_gates.json'
    report = {
        'schema': 'VERITAS_R9_EXECUTION_COST_GATES_V1',
        'bit_ledger_smoke': _ledger_smoke(),
        'two_level_policy': _two_level_flag(),
        'release_ready': {
            'tree_ledger_bit_ops_positive': None,
            'complexity_claim': False,
        },
    }
    report['release_ready']['tree_ledger_bit_ops_positive'] = report['bit_ledger_smoke']['bit_operations'] > 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2))
    ok = report['release_ready']['tree_ledger_bit_ops_positive']
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
