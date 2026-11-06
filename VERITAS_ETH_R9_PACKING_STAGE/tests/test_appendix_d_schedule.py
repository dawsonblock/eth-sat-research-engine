import pytest

from veritas.research.appendix_d_schedule import _ceil_tenth_root, schedule_preflight, uniform_schedule_lemma


def test_exact_tenth_root_at_boundaries():
    for k in range(1, 60):
        assert _ceil_tenth_root(k**10) == k
        assert _ceil_tenth_root(k**10 + 1) == k + 1
        if k > 1:
            assert _ceil_tenth_root(k**10 - 1) == k


def test_leaf_threshold_and_large_fallback_refusal():
    # lambda=10, H=ceil(1024/3)=342.
    leaf = schedule_preflight(1024, 342, 3, 0)
    assert leaf['status'] == 'DIRECT_LEAF_ALLOWED'
    assert leaf['leaf_threshold'] == 342
    large = schedule_preflight(1024, 343, 3, 0)
    assert large['status'] == 'INCONCLUSIVE_SCHEDULE'
    assert not large['complexity_proven']


def test_bad_degree_and_recursive_size_fail_closed():
    assert schedule_preflight(1024, 3, 4, 0)['status'] == 'INVALID_DEGREE'
    assert schedule_preflight(1024, 129, 1, 1)['status'] == 'INVALID_RECURSIVE_SIZE_BOUND'
    assert schedule_preflight(1024, 300, 1000, 0)['status'] == 'INVALID_DEGREE'
    assert schedule_preflight(1024, 600, 513, 0)['status'] == 'INVALID_DEGREE_BOUND'


def test_input_and_resource_limits():
    assert schedule_preflight(1024, 0, 0, 0, max_size_bits=10)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    with pytest.raises(ValueError):
        schedule_preflight(True, 0, 0, 0)
    with pytest.raises(ValueError):
        schedule_preflight(2, 0, 0, -1)


def test_active_schedule_arithmetic_without_materializing_packets(monkeypatch):
    # Keep the very large integer but replace the expensive root operation;
    # the exact-root implementation is checked separately above.
    lam = 131072
    s = 1 << lam
    delta = 1 << ((9 * lam + 9) // 10)
    monkeypatch.setattr('veritas.research.appendix_d_schedule._ceil_tenth_root',
                        lambda _: delta)
    result = schedule_preflight(s, s, 1, 0, max_size_bits=lam + 1)
    assert result['status'] == 'ACTIVE_NUMERIC_PRECONDITIONS_MET'
    assert (result['u'], result['a']) == (1, 2)
    assert all(result['numeric_preconditions'].values())
    assert not result['packing_proven']


def test_explicit_uniform_threshold_is_conditional_and_fails_closed():
    threshold = (1 << 600) * 2 ** 10
    assert uniform_schedule_lemma(threshold - 1, size_constant=2)['status'] == 'INCONCLUSIVE_SUFFICIENT_THRESHOLD'
    result = uniform_schedule_lemma(threshold, size_constant=2)
    assert result['status'] == 'CONDITIONAL_UNIFORM_PACKING_NUMERICS'
    assert result['requires_child_shrink_and_degree_invariants']
    assert not result['packing_constructor_proven']
    assert not result['implementation_complexity_proven']
    assert uniform_schedule_lemma(threshold, size_constant=2, max_integer_bits=100)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
