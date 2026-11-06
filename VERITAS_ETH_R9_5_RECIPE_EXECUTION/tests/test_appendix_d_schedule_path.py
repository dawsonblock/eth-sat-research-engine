import pytest

from veritas.research.appendix_d_schedule import schedule_path_preflight, schedule_preflight


def test_leaf_path_and_descendant_after_leaf():
    result = schedule_path_preflight(1024, [(342, 3)])
    assert result['status'] == 'FINITE_SCHEDULE_PATH_NUMERICS_CHECKED'
    assert result['ends_at_leaf']
    assert not result['child_identities_verified']
    assert not result['uniform_theorem_proven']
    assert schedule_path_preflight(1024, [(342, 3), (1, 1)])['status'] == 'INVALID_CHILD_AFTER_LEAF'


def test_actual_parent_shrink_is_checked_at_each_active_depth(monkeypatch):
    lam = 262144
    s = 1 << lam
    delta = 1 << ((9 * lam + 9) // 10)
    monkeypatch.setattr('veritas.research.appendix_d_schedule._ceil_tenth_root', lambda _: delta)
    accepted = schedule_path_preflight(s, [(s, 1), (3 * s // 32, 1)],
                                       max_size_bits=lam + 1)
    assert accepted['status'] == 'FINITE_SCHEDULE_PATH_NUMERICS_CHECKED'
    assert not accepted['ends_at_leaf']
    assert [(item['u'], item['a']) for item in accepted['calls']] == [(2, 4), (1, 6)]
    # This child obeys the weaker global s/8 depth bound but violates 3M/32.
    rejected = schedule_path_preflight(s, [(s, 1), (s // 10, 1)],
                                       max_size_bits=lam + 1)
    assert rejected['status'] == 'INVALID_CHILD_SHRINK'
    assert rejected['depth'] == 1


def test_path_and_integer_inputs_fail_closed():
    assert schedule_path_preflight(1024, [(342, 3)], max_calls=1)['ends_at_leaf']
    assert schedule_path_preflight(1024, [(342, 3), (0, 0)], max_calls=1)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert schedule_preflight(2, 0, 0, 0, size_constant=1 << 5000)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert schedule_preflight(2, 1 << 5000, 0, 0)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    with pytest.raises(ValueError):
        schedule_path_preflight(2, [(True, 1)])
    with pytest.raises(ValueError):
        schedule_path_preflight(2, [])
