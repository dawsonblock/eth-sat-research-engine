from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r98.model import Budget, canonical, decode
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r99.cli import load_layout
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r910.recovery import Recovery, prefix_weights, reference_weights
from veritas.research.parent_child_r910.engine import contract
from veritas.research.parent_child_r910.checker import verify

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=1_000_000_000,
                 max_seconds=600, max_certificate_bytes=100_000_000)


@pytest.mark.parametrize('M', [1, 2, 5, 22])
def test_original_functional_prefix_is_unchanged(M):
    from veritas.research.eth_interpolation.source_hermite import (
        SourceHermiteLimits, make_source_tapered_plan)
    limits = SourceHermiteLimits(max_wires=32, max_degree=100, max_terms=256)
    original = make_source_tapered_plan(M=M, a=1, u=1, p=5, max_terms=256,
                                       max_precision_bits=4096, limits=limits)
    for d in (0, 1, 3*M):
        expected = tuple((t, row[:d+1]) for t,row in original.weights)
        assert prefix_weights(3*M, d, Budget(POLICY)) == expected
        assert reference_weights(3*M, d, Budget(POLICY)) == expected


def test_degree_optimization_cannot_invent_a_zero_tail():
    p = load_input(ROOT/'examples/r98_general_matching22.json')
    b = Budget(POLICY)
    layout = construct_vertex_shrinking_layout(p, budget=b)
    certificate = certify_row_degree(p, 1, budget=b)
    certificate['degree_bound'] = 0
    with pytest.raises(ValueError, match='degree'):
        Recovery(p, layout, certificate, budget=b)


@pytest.mark.parametrize('tables', [
    ((2, 3), (5, 7)), ((1, 1), (3, 5)), ((0, 0), (7, 9)),
    ((1, 31), (1, 1)), ((16, 0), (2, 3)), ((0, 1), (0, 1)),
])
def test_small_exhaustive_parents_and_cancellation(tables):
    from veritas.research.eth_arithmetic.gf2 import first_irreducible
    from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
    from veritas.research.tensor import Factor, TensorNetwork
    from veritas.research.parent_child_r98.model import from_described
    from veritas.research.parent_child_r98.packing import construct_layout
    from veritas.research.parent_child_r98.shrinking_oracle import parent_point, contract_independent
    from veritas.research.parent_child_r99.basis import build_packet_modes
    net = TensorNetwork(2, tuple(Factor((e,), values, side+str(e))
        for e in range(2) for side,values in zip(('row:','col:'), tables)))
    p = from_described(describe_integer_network(net, creation_precision=5,
        defining_polynomial=first_irreducible(3)), root_s=16, precision=5)
    b = Budget(POLICY)
    layout = construct_layout(p, a=1, u=1, budget=b)
    degree = certify_row_degree(p, 1, budget=b)
    producer = Recovery(p, layout, degree, budget=b)
    checker = Recovery(p, layout, degree, budget=b, independent=True)
    for t,zeta,precision in producer.points():
        modes = build_packet_modes(p,layout,t,zeta,budget=b)
        value = parent_point(p,layout,modes,budget=b)
        producer.add(t,zeta,precision,value[0])
        checker.add(t,zeta,precision,value[0])
    assert producer.finish() == checker.finish() == contract_independent(p,b)


@pytest.fixture(scope='module')
def two_level():
    p = load_input(ROOT/'examples/r910_matching235.json')
    layout = load_layout(p, ROOT/'examples/r910_matching235_layout.json', Budget(POLICY))
    def factory(call, a, u, budget):
        return layout if call.depth == p.depth else construct_vertex_shrinking_layout(call, budget=budget)
    events = []
    report = contract(p, schedule=((1,1),(1,1)), layout_factory=factory, policy=POLICY,
                      evidence_sink=events.append)
    assert report['status'] == 'PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION', report
    assert report['result'] == ((31*2**234, 0, 0),)
    assert report['active_calls_by_depth']['1'] > 0
    assert report['largest_active_edges_by_depth'] == {'0':235, '1':22}
    assert report['largest_deformation_degree_by_depth']['0'] == 3
    assert report['largest_deformation_degree_by_depth']['1'] > 0
    assert report['point_predictions_reconcile']
    assert report['ledger']['stage_sum_reconciles']
    assert report['ledger']['maximum_depth'] == 2
    assert report['ledger']['bit_operations'] is None
    return p, events, report


def test_two_levels_replay_without_production_arithmetic(two_level, monkeypatch):
    p, events, report = two_level
    import veritas.research.parent_child_r910.engine as producer
    import veritas.research.parent_child_r910.recovery as recovery
    import veritas.research.parent_child_r98.constructor as constructor
    import veritas.research.tapered_v4.source_recipes as entries
    def forbidden(*a, **k):
        pytest.fail('production computation called by independent checker')
    monkeypatch.setattr(producer, 'contract', forbidden)
    monkeypatch.setattr(recovery, 'prefix_weights', forbidden)
    monkeypatch.setattr(constructor, 'construct_children', forbidden)
    monkeypatch.setattr(entries, 'evaluate_compiled', forbidden)
    checked = verify(p, iter(events), report, policy=POLICY)
    assert checked['status'] == 'PASS_INDEPENDENT_NUMERICAL_REPLAY', checked
    assert canonical(checked['result']) == canonical(report['result'])


@pytest.mark.parametrize('attack', ['tail', 'weight', 'term', 'wire', 'beta', 'sum'])
def test_nested_evidence_faults_fail_closed(two_level, attack):
    p, originals, report = two_level
    events = list(originals)
    target = 'start' if attack in ('tail','weight') else 'point_value' if attack == 'sum' else 'term'
    i = next(i for i, raw in enumerate(events) if decode(raw)['kind'] == target)
    event = decode(events[i])
    if attack == 'tail':
        event['recovery']['zero_tail_from'] += 1
    elif attack == 'weight':
        event['recovery']['nodes'][0]['weights'][0] = '0'
    elif attack == 'term':
        event['product'][0][0] ^= 1
    elif attack == 'wire':
        event['children'][0]['wires'] += 1
    elif attack == 'beta':
        event['beta'].append(1)
    else:
        event['value'][0][0] ^= 1
    events[i] = canonical(event)
    assert 'result' not in verify(p, events, report, policy=POLICY)


def test_budget_exhaustion_never_returns_a_count():
    p = load_input(ROOT/'examples/r98_general_matching22.json')
    report = contract(p, policy=replace(POLICY,max_work=1))
    assert report['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in report
    assert report['ledger']['stage_sum_reconciles']


def test_preflight_cannot_admit_an_insufficient_depth():
    from veritas.research.parent_child_r910.preflight import preflight
    p = load_input(ROOT/'examples/r910_matching235.json')
    layout = load_layout(p,ROOT/'examples/r910_matching235_layout.json',Budget(POLICY))
    bad = preflight(p,layout,levels=1,max_points=8,policy=POLICY)
    assert not bad['admitted']
    good = preflight(p,layout,levels=2,max_points=8,policy=POLICY)
    assert good['admitted'] and good['root_expected_points']==8
    assert good['root_generic_points']==1412
    assert good['total_work_bound']=='NOT_ESTABLISHED'


def test_matching_oracle_checks_fixture_factors():
    from veritas.research.parent_child_r910.reference import matching_reference
    p = load_input(ROOT/'examples/r910_matching235.json')
    oracle = matching_reference(p)
    assert oracle['edge_factors']==[31]+[2]*234
    assert oracle['unreduced_integer']==31*2**234


@pytest.mark.parametrize('field', ['active_calls_by_depth', 'point_accounting', 'stage_work_units'])
def test_summary_faults_rejected_on_leaf(field):
    from test_r99_general_packets import fixture
    p,_ = fixture()
    events=[]
    report=contract(p,policy=POLICY,evidence_sink=events.append)
    if field=='stage_work_units':
        report['ledger'][field]['control'] += 1
    else:
        report[field] = {'forged': 1}
    assert 'result' not in verify(p,events,report,policy=POLICY)
