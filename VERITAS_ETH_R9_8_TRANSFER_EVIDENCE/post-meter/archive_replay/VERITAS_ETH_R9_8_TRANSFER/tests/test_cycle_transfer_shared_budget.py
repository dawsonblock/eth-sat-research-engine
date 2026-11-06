"""Shared budgets include calls consumed before the cycle transfer invocation."""

from dataclasses import replace

from test_cycle_transfer_fixture import three_crossing_matching
from veritas.research.parent_child_r98.cycle_transfer_recovery import contract_cycle_transfer
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY


def test_preexisting_call_reduces_available_full_grid_budget():
    parent, layout, _ = three_crossing_matching(extension_degree=7, precision=128)
    policy = replace(DEFAULT_SHRINKING_POLICY, max_calls=9899,
                     max_certificate_bytes=100_000_000)
    budget = Budget(policy)
    budget.call(0)
    report = contract_cycle_transfer(parent, layout, budget=budget)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "call budget" in report["reason"]
    assert report["required_actual_calls"] == 9899
    assert report["completed_points"] == 0
    assert report["ledger"]["actual_calls"] == 2
    assert "result" not in report and "certificate" not in report
