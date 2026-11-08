"""Independent leaf-value replay beyond aggregate traversal counters."""
from copy import deepcopy
from pathlib import Path
import runpy

import pytest

from veritas.research.manuscript.finite_replay import ReplayError


@pytest.fixture(scope='module')
def full_replay():
    return runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_full_children.py'))


@pytest.fixture(scope='module')
def full_certificate(full_replay):
    return full_replay['produce']()


def test_every_child_contraction_recomputed(full_replay,full_certificate):
    report=full_replay['replay_children'](full_certificate)
    assert report['independently_recomputed_child_contractions']==76960
    assert report['independent_integer_jet']==[5,15]
    assert report['modular_jet']==[1,3]
    assert report['source_qualified'] is False


@pytest.mark.parametrize('mutation',['value','count','missing','order','boolean_value','boolean_count'])
def test_lossless_child_stream_rejects_tampering(full_replay,full_certificate,mutation):
    forged=deepcopy(full_certificate)
    if mutation=='value':forged['child_runs'][0]['result'][0][0]^=1
    elif mutation=='count':forged['child_runs'][0]['count']+=1
    elif mutation=='missing':forged['child_runs'].pop()
    elif mutation=='boolean_value':forged['child_runs'][0]['result'][0][0]=True
    elif mutation=='boolean_count':forged['child_runs'][0]['count']=True
    else:forged['child_runs'][0],forged['child_runs'][1]=forged['child_runs'][1],forged['child_runs'][0]
    with pytest.raises(ReplayError,match='child contraction'):
        full_replay['replay_children'](forged)


def test_independent_compositions_complete_and_lexicographic(full_replay):
    values=list(full_replay['_betas']())
    assert len(values)==len(set(values))==4810
    assert values==sorted(values)
    assert all(sum((1+j//4)*power for j,power in enumerate(beta))<=8 for beta in values)
