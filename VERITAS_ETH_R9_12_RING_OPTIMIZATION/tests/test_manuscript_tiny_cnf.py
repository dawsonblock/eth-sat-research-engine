"""Tiny #SAT conversion and bounded recursive exact-count demonstration."""
from copy import deepcopy
from pathlib import Path
import runpy
import pytest


@pytest.fixture(scope='module')
def implementation():
    return runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/validate_manuscript_tiny_cnf.py'))


@pytest.fixture(scope='module')
def certificate(implementation):return implementation['produce']()


def test_tiny_cnf_pipeline_completes_two_active_levels(implementation,certificate):
    result=implementation['replay'](certificate)
    assert result['exact_count']==3
    assert result['independent_satisfying_assignments']==[[0,1],[1,0],[1,1]]
    assert result['recursive_replay']['maximum_depth']==2
    assert result['recursive_replay']['recovered_active_nodes']>1
    assert result['source_qualified'] is False


@pytest.mark.parametrize('mutation',['literal','port','clause_table','equality_table','schema','n','extra'])
def test_formula_or_conversion_tampering_rejected(implementation,certificate,mutation):
    c=deepcopy(certificate)
    if mutation=='literal':c['formula']['clauses'][0][0]=-1
    elif mutation=='port':c['tensor_certificate']['fixture']['vertices'][0]['ports']=[1]
    elif mutation=='clause_table':c['tensor_certificate']['fixture']['vertices'][2]['values'][0]=[1,0]
    elif mutation=='equality_table':c['tensor_certificate']['fixture']['vertices'][0]['values'][0]=[0,0]
    elif mutation=='schema':c['schema']='wrong'
    elif mutation=='n':c['formula']['n']=True
    else:c['unexpected']=True
    with pytest.raises(implementation['connected'].ReplayError):implementation['replay'](c)


@pytest.mark.parametrize('clauses',[[[1,2]],[[-1,2]],[[1,-2]],[[-1,-2]],[[1,-1]],[[1,2],[-1]]])
def test_truth_tables_represent_formula(implementation,clauses):
    fixture=implementation['build_fixture'](2,clauses)
    graph=implementation['connected'].decode_fixture(fixture)
    expected=sum(all(any(bool((assignment>>(abs(lit)-1))&1)==(lit>0) for lit in c) for c in clauses)
                 for assignment in range(4))
    assert implementation['connected'].exact(graph,3)==((expected,0,0,0),(0,0,0,0))


def test_modulo_ambiguity_is_refused_not_reported_as_zero(implementation,monkeypatch):
    connected=implementation['connected'];fixture=implementation['build_fixture'](2,[[1,-1]])
    certificate=dict(schema='VERITAS_TINY_CNF_TWO_LEVEL_V1',formula=dict(n=2,clauses=[[1,-1]]),
                     tensor_certificate=dict(fixture=fixture))
    monkeypatch.setattr(connected,'replay',lambda c:dict(root_modular_jet=[0,0]))
    with pytest.raises(connected.ReplayError,match='AMBIGUOUS_MODULUS'):implementation['replay'](certificate)


@pytest.mark.parametrize('n,clauses',[(3,[[1,2]]),(2,[]),(2,[[0,1]]),(2,[[1]]),(2,[[1,2],[1,2]]),(True,[[1,2]])])
def test_unsupported_input_refused(implementation,n,clauses):
    with pytest.raises(ValueError):implementation['build_fixture'](n,clauses)


def test_replay_does_not_reuse_builder(implementation,certificate,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('builder called in replay')
    monkeypatch.setitem(implementation['replay'].__globals__,'build_fixture',forbidden)
    assert implementation['replay'](certificate)['exact_count']==3
