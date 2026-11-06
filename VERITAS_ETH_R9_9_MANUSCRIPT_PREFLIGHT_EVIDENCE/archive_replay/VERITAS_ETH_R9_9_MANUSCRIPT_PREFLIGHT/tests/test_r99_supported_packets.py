from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from math import prod

import pytest

from test_r99_general_packets import fixture
from veritas.research.parent_child_r98.model import Budget, Policy, ModeSet, Refusal, canonical
from veritas.research.parent_child_r99 import build_packet_modes, evaluate_packet_point
from veritas.research.parent_child_r99.support import fold_source_forms, build_support, SupportCertificate
from veritas.research.parent_child_r99.support_check import verify_support
from veritas.research.parent_child_r99.supported_engine import evaluate_supported_point, recover_supported_parent
from veritas.research.parent_child_r99.supported_verify import verify_supported_point, verify_supported_recovery
from veritas.research.parent_child_r99.row_degree import certify_row_degree, verify_row_degree
from veritas.research.parent_child_r99.degree_recovery import degree_points, recover_degree_grid
from veritas.research.parent_child_r99.engine import contract_packet_recursion


@pytest.fixture(scope='module')
def point():
    p, l = fixture(u=2)
    b = Budget()
    modes = build_packet_modes(p, l, 1, (1 << 40, 0, 0, 0), budget=b)
    value, certificate = evaluate_supported_point(p, l, modes, budget=b)
    return p, l, modes, value, certificate


def test_folding_has_higher_exponents_and_complete_scalar_value(point):
    p, l, modes, value, cert = point
    assert len(modes.certificate['modes']) == 106
    assert len(cert['folded_modes']['modes']) == 2
    assert len(cert['support']['tuples']) == 6
    assert any(2 in beta for beta in cert['support']['tuples'])
    assert cert['support']['original_weighted_tuple_count'] == 345770425887
    assert not cert['support']['original_weighted_stream_enumerated']
    modulus = 1 << modes.certificate['precision']
    T = 1 + 8 * (1 << 40)

    def w(x, y):
        rational = Fraction(prod(T - q for q in range(-4, 4) if q != y-x),
                            prod(-q for q in range(-4, 4) if q))
        return rational.numerator * pow(rational.denominator, -1, modulus) % modulus

    total = (4 + 10*(1+2*w(0, 2))*(1+2*w(2, 2)) +
             10*(1+2*w(0, 0))*(1+2*w(2, 0)) +
             25*(1+2*(w(0, 0)+w(0, 2)))*(1+2*(w(2, 0)+w(2, 2)))) % modulus
    assert value == ((total, 0, 0, 0),)
    assert verify_supported_point(p, l, cert, budget=Budget())[0] == value
    with pytest.raises(Refusal):
        evaluate_packet_point(p, l, modes, budget=Budget())


@pytest.mark.parametrize('attack', ['drop', 'duplicate', 'substitute', 'order', 'source', 'target',
                                   'coefficient', 'count', 'row_degree', 'child_value', 'result'])
def test_supported_point_mutations(point, attack):
    p, l, _, _, cert = point
    bad = deepcopy(cert)
    if attack == 'drop':
        bad['support']['tuples'].pop()
    elif attack == 'duplicate':
        bad['support']['tuples'][-1] = bad['support']['tuples'][0]
    elif attack == 'substitute':
        bad['support']['tuples'][-1] = [1, 2]
    elif attack == 'order':
        bad['support']['tuples'].reverse()
    elif attack in ('source', 'target'):
        bad['folded_modes']['modes'][0][attack + '_group'] += 1
    elif attack == 'coefficient':
        bad['folded_modes']['modes'][0]['rows'][0][1][0][0] ^= 2
    elif attack == 'count':
        bad['support']['original_weighted_tuple_count'] -= 1
    elif attack == 'row_degree':
        bad['support']['row_certificate'] = {'nonconstant_row_ports': []}
    elif attack == 'child_value':
        bad['child_values'][0][0] = ((123, 0, 0, 0),)
    else:
        bad['result'] = ((123, 0, 0, 0),)
    with pytest.raises((ValueError, KeyError)):
        verify_supported_point(p, l, bad, budget=Budget())


def test_support_checker_never_calls_production(point, monkeypatch):
    import veritas.research.parent_child_r99.support as producer
    import veritas.research.parent_child_r98.constructor as constructor
    import veritas.research.tapered_v4.source_recipes as recipes
    def forbidden(*a, **kw):
        raise AssertionError('production called by independent consumer')
    monkeypatch.setattr(producer, 'fold_source_forms', forbidden)
    monkeypatch.setattr(producer, 'build_support', forbidden)
    monkeypatch.setattr(constructor, 'construct_children', forbidden)
    monkeypatch.setattr(recipes, 'evaluate_compiled', forbidden)
    p, l, _, value, cert = point
    assert verify_supported_point(p, l, cert, budget=Budget())[0] == value


def test_complete_crossing_parent_multivaluation_recovery():
    p, l = fixture(u=2)
    policy = Policy(max_work=1_000_000_000, max_seconds=600, max_certificate_bytes=100_000_000)
    report = recover_supported_parent(p, l, policy=policy)
    assert report['status'] == 'PASS_FINITE_SUPPORTED_PACKET_RECOVERY', report
    assert report['result'] == ((1, 0, 0, 0),)
    assert report['ledger']['point_evaluations'] == 90
    assert report['ledger']['actual_calls'] == 23680
    replay = verify_supported_recovery(p, l, report['certificate'], policy=policy)
    assert replay['status'] == 'PASS_INDEPENDENT_SUPPORTED_RECOVERY', replay
    assert replay['result'] == report['result']
    assert not replay['actual_source_shrink']
    report['certificate']['points'].pop()
    assert 'result' not in verify_supported_recovery(p, l, report['certificate'], policy=policy)


@pytest.mark.parametrize('limit', ['max_tuples', 'max_calls', 'max_work', 'max_certificate_bytes'])
def test_support_budgets_refuse_before_result(point, limit):
    p, l, modes, *_ = point
    with pytest.raises(Refusal):
        evaluate_supported_point(p, l, modes, budget=Budget(replace(Policy(), **{limit: 1})))


def test_row_degree_original_creation_is_binding(point):
    p, l, *_ = point
    cert = certify_row_degree(p, l.a, budget=Budget())
    assert cert['degree_bound'] == 14
    assert verify_row_degree(p, l.a, cert, budget=Budget()) == (0, 1)
    bad = dict(cert, degree_bound=0, nonconstant_row_ports=[])
    with pytest.raises(ValueError):
        verify_row_degree(p, l.a, bad, budget=Budget())
    changed = replace(p, precision=p.precision + 1)
    with pytest.raises(ValueError):
        verify_row_degree(changed, l.a, cert, budget=Budget())


def test_degree_recovery_rational_monomials(point):
    p, l, *_ = point
    cert = certify_row_degree(p, l.a, budget=Budget())
    grid = tuple(degree_points(p, l, cert, budget=Budget()))
    from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
    for power in (0, 1, 2, 7, 14):
        rows = []
        for t, z, precision in grid:
            ring = ExtensionRing(precision, p.defining_polynomial)
            x = ring.add(ring.elem([t]), ring.mul(ring.elem([8]), z))
            value = ring.one
            for _ in range(power):
                value = ring.mul(value, x)
            rows.append([t, list(z), precision, list(value)])
        result, _ = recover_degree_grid(p, l, cert, rows, budget=Budget())
        assert result == ((int(power == 0), 0, 0, 0),)
        from veritas.research.parent_child_r99.degree_check import verify_degree_recovery
        assert verify_degree_recovery(p, l, cert, rows, result, budget=Budget()) == result
    rows[0][2] -= 1
    with pytest.raises(ValueError):
        recover_degree_grid(p, l, cert, rows, budget=Budget())


def test_explicit_grid_and_strategy_options_reject_invalid(point):
    p, *_ = point
    assert 'result' not in contract_packet_recursion(p, max_points=True)
    assert 'result' not in contract_packet_recursion(p, point_strategy='guess')


@pytest.fixture(scope='module')
def recursive_evidence(tmp_path_factory):
    from veritas.research.parent_child_r98.shrinking_cli import load_input
    from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
    from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
    from veritas.research.parent_child_r98.model import PacketLayout
    from veritas.research.parent_child_r99.degree_engine import contract_supported_recursion
    path = tmp_path_factory.mktemp('recursive-support') / 'input.json'
    data = {'root_s': 32, 'precision': 32, 'extension_degree': 2, 'edges': 22,
            'vertices': [{'side': side, 'ports': [e], 'table': (values if e == 0 else [1, 1])}
                         for e in range(22) for side, values in [('row', [1, 3]), ('column', [2, 5])]]}
    path.write_bytes(canonical(data))
    parent = load_input(path)

    def factory(call, a, u, budget):
        layout = construct_vertex_shrinking_layout(call, budget=budget)
        s = layout.source
        s['column_labels'] = {k: [(v[0]+1) % 22] for k, v in s['column_labels'].items()}
        packets = []
        for e, (r, c) in enumerate(s['edges']):
            x, y = s['row_labels'][str(r)][0], s['column_labels'][str(c)][0]
            packets.append({'symbol_pairs': [[min(x, y), max(x, y)]], 'index': 0,
                            'occupied_slots': [[int(x > y), e]]})
        s['packets'] = sorted(packets, key=lambda p: p['symbol_pairs'])
        return PacketLayout(call.content_digest, 1, 1, canonical(s), 'balanced_vertices')

    events = []
    report = contract_supported_recursion(parent, schedule=((1, 1),), layout_factory=factory,
                                         policy=DEFAULT_SHRINKING_POLICY, evidence_sink=events.append)
    assert report['status'] == 'PASS_FINITE_SUPPORTED_SHRINKING_RECURSION', report
    return parent, report, events, DEFAULT_SHRINKING_POLICY


def test_actual_shrinking_support_recursion_and_independent_replay(recursive_evidence, monkeypatch):
    from veritas.research.parent_child_r99.degree_verify import verify_recursive_events
    import veritas.research.parent_child_r99.degree_engine as engine
    import veritas.research.parent_child_r98.constructor as constructor
    import veritas.research.tapered_v4.source_recipes as recipes
    def forbidden(*args, **kwargs):
        raise AssertionError('independent recursive replay called production')
    monkeypatch.setattr(engine, 'contract_supported_recursion', forbidden)
    monkeypatch.setattr(constructor, 'construct_children', forbidden)
    monkeypatch.setattr(recipes, 'evaluate_compiled', forbidden)
    p, report, events, policy = recursive_evidence
    assert report['result'] == ((17 * 2**21, 0),)
    assert report['largest_edges_by_depth'] == {'0': 22, '1': 2}
    assert report['crossing_points_by_depth']['0'] > 0
    replay = verify_recursive_events(p, iter(events), report, policy=policy)
    assert replay['status'] == 'PASS_INDEPENDENT_SUPPORTED_RECURSION', replay
    assert replay['result'] == report['result']


@pytest.mark.parametrize('attack', ['drop', 'duplicate', 'child', 'degree', 'tail', 'depth', 'source_claim'])
def test_recursive_evidence_adversaries(recursive_evidence, attack):
    from hashlib import sha256
    from veritas.research.parent_child_r98.model import decode
    from veritas.research.parent_child_r99.degree_verify import verify_recursive_events
    p, report, events, policy = recursive_evidence
    report, events = deepcopy(report), list(events)
    if attack == 'drop':
        events.pop(0)
    elif attack == 'duplicate':
        events.insert(0, events[0])
    elif attack == 'source_claim':
        report['source_qualified'] = True
    elif attack == 'child':
        d = decode(events[0]);d['certificate']['child_values'][0][0] = [[123, 0]];events[0] = canonical(d)
    else:
        d = decode(events[-1])
        if attack == 'degree':
            d['certificate']['degree_certificate']['degree_bound'] = 0
        elif attack == 'tail':
            d['certificate']['nodes'][0]['exact_zero_tail_from'] = 0
        else:
            d['depth'] += 1
        events[-1] = canonical(d)
    chain = '0'*64
    for event in events:
        chain = sha256(bytes.fromhex(chain)+event).hexdigest()
    report['evidence_chain'], report['evidence_bytes'] = chain, sum(map(len, events))
    assert 'result' not in verify_recursive_events(p, events, report, policy=policy)


def test_cli_report_roundtrip_and_integer_math_boundary(recursive_evidence, tmp_path):
    from veritas.research.parent_child_r99.cli import load_execution_report, main
    p, report, events, policy = recursive_evidence
    path = tmp_path/'report.json'
    path.write_bytes(canonical(report))
    assert canonical(load_execution_report(path, max_bytes=policy.max_certificate_bytes)) == canonical(report)
    altered = deepcopy(report)
    altered['result'] = [[1.0, 0]]
    path.write_bytes(canonical(altered))
    with pytest.raises(ValueError, match='floating point'):
        load_execution_report(path, max_bytes=policy.max_certificate_bytes)
    with pytest.raises(ValueError):
        from veritas.research.parent_child_r98.model import decode
        decode(canonical({'coefficient': 1.0}))
    path.write_bytes(canonical(report))
    input_path, event_path, output_path = (tmp_path/name for name in ('input.json', 'events.jsonl', 'replay.json'))
    input_path.write_bytes(canonical({'root_s': 32, 'precision': 32, 'extension_degree': 2, 'edges': 22,
        'vertices': [{'side': side, 'ports': [e], 'table': values if e == 0 else [1, 1]}
                     for e in range(22) for side, values in [('row', [1, 3]), ('column', [2, 5])]]}))
    event_path.write_bytes(b''.join(raw+b'\n' for raw in events))
    assert main([str(input_path), '--mode', 'recursion', '--verify', '--result-report', str(path),
                 '--certificate', str(event_path), '--output', str(output_path)]) == 0
    import json
    assert json.loads(output_path.read_bytes())['status'] == 'PASS_INDEPENDENT_SUPPORTED_RECURSION'
