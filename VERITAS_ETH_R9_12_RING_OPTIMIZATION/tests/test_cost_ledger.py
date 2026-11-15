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


def test_tree_budget_covers_ancestors_and_siblings():
    root = CostLedger(max_tree_work=3)
    root.tick('a', 2)
    child = root.child()
    with pytest.raises(RuntimeError):
        child.tick('a', 2)
    root = CostLedger(max_tree_work=3)
    first, second = root.child(), root.child()
    first.tick('a', 2)
    grandchild = second.child()
    assert grandchild.max_tree_work == 3
    with pytest.raises(RuntimeError):
        grandchild.tick('a', 2)


def test_tree_budget_allows_work_up_to_the_cap():
    root = CostLedger(max_tree_work=4)
    root.tick('a', 2)
    root.child().tick('a', 2)
    assert root.total_work == 4


def test_report_aggregates_descendant_cache_statistics():
    root = CostLedger()
    child = root.child()
    child.record_cache(hit=True)
    child.record_cache(hit=False)
    child.child().record_cache(hit=True)
    child.note_unique_subproblem()
    rep = root.report()
    assert (rep['cache_hits'], rep['cache_misses'], rep['unique_subproblems']) == (0, 0, 0)
    assert rep['cache_hit_rate_ppm'] is None
    assert (rep['tree_cache_hits'], rep['tree_cache_misses']) == (2, 1)
    assert rep['tree_cache_hit_rate_ppm'] == 666_666
    assert rep['tree_unique_subproblems'] == 1
    assert CostLedger().report()['tree_cache_hit_rate_ppm'] is None
