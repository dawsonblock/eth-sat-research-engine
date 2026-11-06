"""Check the independent integer cycle oracle against literal enumeration."""
import importlib.util
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('r911_experiment',
    Path(__file__).resolve().parents[1]/'scripts/experiment_r911.py')
experiment=importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


@pytest.mark.parametrize('n',[2,3,4,5])
@pytest.mark.parametrize('all_columns',[False,True])
def test_cycle_reference_including_asymmetric_tables(n,all_columns):
    data=experiment.cycle_input(n=n,active_rows=2,all_columns=all_columns)
    assert experiment.cycle_reference(data)['unreduced_integer']==experiment.exhaustive_reference(data)


def test_cycle_oracle_rejects_wrong_port_order():
    data=experiment.cycle_input(n=3)
    data['vertices'][0]['ports'].reverse()
    with pytest.raises(ValueError,match='incidence'):
        experiment.cycle_reference(data)


def test_genuine_core_has_rank_two_vertices_and_constant_padding():
    r=experiment.cycle_reference(experiment.cycle_input())
    assert r['rank_two_vertices']==3
    assert not r['all_vertices_rank_two']


@pytest.mark.parametrize('b',[1,2,4,8,16,32,242])
def test_matching_sweep_shape(b):
    data=experiment.matching_input(b)
    rows=[v for v in data['vertices'] if v['side']=='row']
    assert sum(v['table']==[1,3] for v in rows)==b
    assert 3*b+1<=2**data['extension_degree']
