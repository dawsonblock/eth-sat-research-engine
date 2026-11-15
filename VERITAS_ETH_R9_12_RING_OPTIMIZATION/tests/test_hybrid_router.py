import pytest

from veritas.core.cnf import CNF
from veritas.research.contraction_planner import ContractLimit
from veritas.research.hybrid_router import estimate_backends, hybrid_count


def test_two_component_formula_prefers_boundary_estimate():
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    estimates = estimate_backends(cnf)
    names = {e.name for e in estimates}
    assert 'EXACT_BOUNDARY_DP' in names
    assert 'EXACT_VARIABLE_ELIMINATION' in names
    result = hybrid_count(cnf, timeout_s=5)
    assert 'routing' in result
    assert result['routing']['chosen_backend'] in names
    assert result['count'] == '9'


def test_routing_carries_no_complexity_claim():
    cnf = CNF.from_lists(3, [[1, 2], [-1, 2]])
    result = hybrid_count(cnf, timeout_s=5)
    assert 'subexponential' in result['routing']['warning']


def test_elimination_route_keeps_heuristic_planner_above_twelve_variables():
    # A 13-variable chain has a width-1 elimination order; fib(15) = 610 models.
    cnf = CNF.from_lists(13, [[i, i + 1] for i in range(1, 13)])
    result = hybrid_count(cnf, timeout_s=5)
    assert result['status'] == 'EXACT_COUNT'
    assert result['count'] == '610'
    assert result['optimal_order_work_certified'] is False


def test_small_elimination_route_still_uses_certified_order():
    cnf = CNF.from_lists(5, [[i, i + 1] for i in range(1, 5)])
    result = hybrid_count(cnf, timeout_s=5)
    assert result['count'] == '13'
    if result['routing']['chosen_backend'] == 'EXACT_VARIABLE_ELIMINATION':
        assert result['portfolio_mode'] == 'optimal_small'


def test_zero_max_separator_skips_separator_search():
    cnf = CNF.from_lists(4, [[1, 2], [3, 4]])
    assert estimate_backends(cnf, max_separator=0)
    assert hybrid_count(cnf, max_separator=0, timeout_s=5)['count'] == '9'


def test_routing_seconds_excludes_execution_and_shares_one_budget(monkeypatch):
    import veritas.research.hybrid_router as router
    seen = {}

    def fake_adaptive(cnf, **kwargs):
        seen.update(kwargs)
        return {'count': '0', 'elapsed_seconds': 0.0}

    monkeypatch.setattr(router, 'adaptive_count', fake_adaptive)
    result = router.hybrid_count(CNF.from_lists(3, [[1, 2], [-1, 2]]), timeout_s=5)
    assert 0 < seen['timeout_s'] <= 5
    assert 0 <= result['routing']['routing_seconds'] <= 5 - seen['timeout_s'] + 1e-3


def test_exhausted_budget_fails_closed(monkeypatch):
    import veritas.research.hybrid_router as router
    clock = iter([0.0, 100.0, 100.0, 100.0])
    monkeypatch.setattr(router, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(router, 'estimate_backends', lambda *a, **k: [
        router.BackendEstimate('EXACT_VARIABLE_ELIMINATION', 0, 1, True, 'stub')])
    with pytest.raises(ContractLimit):
        router.hybrid_count(CNF.from_lists(2, [[1, 2]]), timeout_s=5)
