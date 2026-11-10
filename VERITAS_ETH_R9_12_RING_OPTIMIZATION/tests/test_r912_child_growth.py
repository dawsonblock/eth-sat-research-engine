import importlib.util
from math import log2
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'child_growth', Path(__file__).resolve().parents[1]/'scripts/experiment_r912_child_growth.py')
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)


@pytest.mark.parametrize('n', [4, 9, 22])
def test_random_cubic_is_simple_three_regular_bipartite(n):
    data = census.random_cubic(n, 3)
    pairs = []
    for e in range(data['edges']):
        ends = [v['side'] for v in data['vertices'] if e in v['ports']]
        assert sorted(ends) == ['column', 'row']
        pairs.append(tuple(i % n for i, v in enumerate(data['vertices']) if e in v['ports']))
    assert len(set(pairs)) == len(pairs) == 3*n
    assert all(len(v['ports']) == 3 for v in data['vertices'])


def test_census_counts_requests_without_claiming_complexity():
    record = census.census('circulant', 22, 5, 'default', samples=1, checks=4, max_seconds=600)
    assert record['source_qualified'] is False and record['complexity_evidence'] is False
    for rows in record['sampled_points'].values():
        point = rows[0]
        assert point['random_tuple_consistency']
        assert point['precision_cutoff_prunes'] is False
        assert point['log2_support'] == point['modes']
        assert point['log2_distinct_children_if_factorized'] < point['log2_support']
    assert record['log2_child_requests_top_call_estimate'] > log2(record['interpolation_points'])
    assert record['mode_graph_elimination_width'] >= 1
