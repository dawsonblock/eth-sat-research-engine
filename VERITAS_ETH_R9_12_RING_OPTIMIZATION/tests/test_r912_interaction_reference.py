from itertools import product
import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('interaction_probe',Path(__file__).resolve().parents[1]/'scripts/experiment_r912_interaction.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


@pytest.mark.parametrize('n',[3,4,5])
def test_high_interaction_integer_oracle_against_exhaustive(n):
    data=probe.graph(n,2);total=0
    for bits in product((0,1),repeat=data['edges']):
        term=1
        for vertex in data['vertices']:
            term*=vertex['table'][sum(bits[e]<<i for i,e in enumerate(vertex['ports']))]
        total+=term
    result=probe.integer_elimination(data)
    assert result['integer']==total
    assert all(len(set(v['table']))>1 for v in data['vertices'])
