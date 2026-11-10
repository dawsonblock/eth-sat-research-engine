from dataclasses import replace

import pytest

from veritas.research.parent_child_r98.model import canonical, decode
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r910.checker import verify
from veritas.research.parent_child_r910.engine import contract
from test_r912_jets import jet_matching, multilevel_layout

POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=100_000_000, max_seconds=600)


@pytest.fixture(scope='module')
def jet_run():
    parent, events = jet_matching(), []
    report = contract(parent, policy=POLICY, layout_factory=multilevel_layout, evidence_sink=events.append)
    assert report['status'] == 'PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION', report
    assert verify(parent, events, report, policy=POLICY)['status'] == 'PASS_INDEPENDENT_NUMERICAL_REPLAY'
    return parent, events, report


def _mutate(events, kind, change):
    events = list(events)
    i = next(i for i, raw in enumerate(events) if decode(raw)['kind'] == kind)
    event = decode(events[i])
    if change(event) == 'drop':
        return events[:i] + events[i+1:]
    events[i] = canonical(event)
    return events


@pytest.mark.parametrize('attack', [
    'missing_child', 'missing_term', 'child_precision', 'point_precision',
    'truncated_product', 'truncated_leaf', 'truncated_point_value'])
def test_incomplete_or_mistyped_evidence_is_rejected(jet_run, attack):
    parent, originals, report = jet_run
    if attack == 'missing_child':
        events = _mutate(originals, 'term', lambda e: e['children'].pop())
    elif attack == 'missing_term':
        events = _mutate(originals, 'term', lambda e: 'drop')
    elif attack == 'child_precision':
        events = _mutate(originals, 'term', lambda e: e['children'][0].update(precision=e['children'][0]['precision']-1))
    elif attack == 'point_precision':
        events = _mutate(originals, 'point', lambda e: e['original'].update(precision=e['original']['precision']-1))
    elif attack == 'truncated_product':
        events = _mutate(originals, 'term', lambda e: e['product'].pop())
    elif attack == 'truncated_leaf':
        events = _mutate(originals, 'leaf', lambda e: e['result'].pop())
    else:
        events = _mutate(originals, 'point_value', lambda e: e['value'].pop())
    assert events != list(originals)
    checked = verify(parent, events, report, policy=POLICY)
    assert checked['status'] != 'PASS_INDEPENDENT_NUMERICAL_REPLAY'
    assert 'result' not in checked


def test_truncated_report_jet_is_rejected(jet_run):
    parent, events, report = jet_run
    forged = dict(report, result=report['result'][:-1])
    assert 'result' not in verify(parent, events, forged, policy=POLICY)


@pytest.mark.parametrize('flag', ['source_qualified', 'theorem_mode_enabled'])
def test_experimental_schedule_never_carries_qualification(jet_run, flag):
    parent, events, report = jet_run
    assert report['source_qualified'] is False and report['theorem_mode_enabled'] is False
    assert 'result' not in verify(parent, events, dict(report, **{flag: True}), policy=POLICY)


def test_execution_selector_never_qualifies_finite_or_source_requests():
    from veritas.research.parent_child_r99.execution import (
        ExecutionSpec, LeafKind, ScheduleKind, execute)
    parent = jet_matching(edges=1)
    finite = execute(parent, ExecutionSpec(schedule=((1, 1),)), policy=POLICY)
    assert finite['source_qualified'] is False
    with pytest.raises(ValueError):
        ExecutionSpec(schedule_kind=ScheduleKind.SOURCE, schedule=((1, 1),))
    source = execute(parent, ExecutionSpec(schedule_kind=ScheduleKind.SOURCE, schedule=(),
                                           leaves=LeafKind.SOURCE), policy=POLICY)
    assert source['source_qualified'] is False and 'result' not in source


def test_count_residue_requires_precision_above_variable_count(monkeypatch):
    from veritas.research.manuscript import cnf
    from veritas.research.manuscript.resources import Limits
    formula = cnf.Formula(4, ((1, 2), (1, 3), (1, 4)))
    good = cnf.count_fixed_density(formula, limits=Limits(max_work=100_000_000, max_seconds=30))
    assert good['status'] == 'PASS_EXACT_COUNT' and good['count'] == 9
    original = cnf.encode
    monkeypatch.setattr(cnf, 'encode', lambda f, b: replace(original(f, b), precision=f.n))
    with pytest.raises(ArithmeticError, match='P >= n\\+1'):
        cnf.count_fixed_density(formula, limits=Limits(max_work=100_000_000, max_seconds=30))
