from veritas.research.cost_ledger_bridge import RecursiveVisitTracker
from veritas.research.parent_child_r98.model import Budget, DEFAULT_POLICY


def test_tracker_records_cache_and_children():
    budget = Budget(DEFAULT_POLICY)
    tracker = RecursiveVisitTracker(DEFAULT_POLICY)
    tracker.request()
    tracker.cache_lookup('k1', hit=False)
    tracker.cache_lookup('k1', hit=True)
    with tracker.child_frame():
        tracker.charge('child_work', 3)
    report = tracker.finalize(budget)
    assert report['cache_hits'] == 1
    assert report['cache_misses'] == 1
    assert report['unique_subproblems'] == 1
    assert report['child_count'] == 1
    assert report['observational_only'] is True
