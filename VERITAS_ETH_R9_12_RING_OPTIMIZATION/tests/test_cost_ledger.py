import pytest

from veritas.research.cost_ledger import CostLedger


def test_tree_aggregation_and_cache_metrics():
    root = CostLedger(max_tree_work=100)
    root.tick('rewrite', 10)
    child = root.child()
    child.tick('arithmetic', 5)
    root.record_cache(hit=False)
    root.record_cache(hit=True)
    root.note_unique_subproblem()
    rep = root.report()
    assert rep['total_work'] == 15
    assert rep['cache_hits'] == 1
    assert rep['cache_misses'] == 1
    assert rep['unique_subproblems'] == 1
    assert rep['recursion_depth'] == 1


def test_tree_budget_enforced():
    root = CostLedger(max_tree_work=3)
    root.tick('a', 3)
    with pytest.raises(RuntimeError):
        root.tick('b', 1)


def test_cache_profitable_criterion():
    assert CostLedger.cache_profitable(appearances=5, eval_cost=100, lookup_cost=1, key_cost=10)
    assert not CostLedger.cache_profitable(appearances=2, eval_cost=1, lookup_cost=100, key_cost=100)
