import importlib.util
from pathlib import Path

import pytest

pytest.importorskip('numpy')

_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_materialized_child_shrink.py'
_spec = importlib.util.spec_from_file_location('audit_materialized_child_shrink', _SCRIPT)
shrink = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shrink)

NON_CLAIMS = ('deterministic_constructor_replayed', 'on_manuscript_schedule',
              'tensor_network_built', 'children_constructed', 'contraction_executed',
              'complexity_claim')


def test_minimum_edges_matches_lean_hypotheses():
    assert shrink.minimum_edges(48, 1, 1) == 2 * (48 ** 2) ** 2
    assert shrink.minimum_edges(64, 1, 2) == 2 * (64 ** 2) ** 2 * 2
    assert shrink.minimum_edges(64, 2, 8) == 1 << 52


def test_small_radix_checks_packing_but_not_one_eighth():
    result = shrink.audit(radix=4, a=1, degree=3, seed=5)
    assert result['scope'] == 'MATERIALIZED_OFF_SCHEDULE_PACKING_INSTANCE_ONLY'
    assert result['edges'] >= result['minimum_edges_required']
    assert all(result['hypotheses'].values())
    assert result['conclusions']['child_edges_times_r_at_most_6M']
    assert result['conclusions']['padded_slots_at_most_3M']
    assert result['one_eighth_bound_applicable'] is False
    assert result['all_checks_pass']
    for flag in NON_CLAIMS:
        assert result[flag] is False


def test_two_coordinates_check_every_coordinate():
    result = shrink.audit(radix=3, a=2, degree=2, seed=1)
    assert result['D'] == 81 and result['L'] == 4
    assert result['all_checks_pass']


def test_smallest_one_eighth_instance():
    result = shrink.audit(radix=48, a=1, degree=1, seed=0)
    M = result['edges']
    assert M >= 10_616_832
    assert all(result['hypotheses'].values())
    assert all(result['conclusions'].values())
    assert result['worst_child_edges'] * 8 <= M
    assert result['worst_child_edges'] * 48 <= 6 * M
    assert result['all_checks_pass']


@pytest.mark.parametrize('kwargs', [
    {'radix': 1}, {'radix': 65}, {'a': 0}, {'a': 3}, {'degree': 0}, {'seed': -1},
    {'radix': True}, {'degree': 1.0},
])
def test_rejects_out_of_range_parameters(kwargs):
    with pytest.raises(ValueError):
        shrink.audit(**kwargs)


def test_refuses_sizes_above_the_materialization_cap():
    with pytest.raises(ValueError, match='materialization cap'):
        shrink.audit(radix=64, a=2, degree=8)
