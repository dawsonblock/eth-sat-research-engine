from dataclasses import replace
from pathlib import Path
import pytest

from veritas.research.parent_child_r98.model import Budget, ModeSet, canonical, decode
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.basis import build_packet_modes, verify_packet_modes, iter_packet_components
from veritas.research.parent_child_r99.resources import prepare_scalar_field, computation_key, ExactCache
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r99.stream_recovery import StreamRecovery
from veritas.research.parent_child_r99.stream_engine import contract_streaming
from veritas.research.parent_child_r99.stream_verify import verify_streaming
from veritas.research.parent_child_r99.recovery import make_packet_plan, packet_points, recover_packet_grid
from veritas.research.parent_child_r98.shrinking_oracle import parent_point
from test_r99_general_packets import fixture

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=1_000_000_000, max_seconds=300)


def test_field_preparation_preserves_original_creation_values():
    p = load_input(ROOT/'examples/r99_nonconstant_matching242.json')
    q = prepare_scalar_field(p, 727)
    assert q.defining_polynomial.bit_length()-1 == 10
    assert p.defining_polynomial != q.defining_polynomial
    for v, w in zip(p.vertices, q.vertices):
        assert v.ports == w.ports
        assert v.tensor.creation_precision == w.tensor.creation_precision
        assert [x[0][0] for x in decode(v.tensor.description)['data']] == [x[0][0] for x in decode(w.tensor.description)['data']]
    with pytest.raises(ValueError):
        prepare_scalar_field(replace(p, ancestry_digest='1'*64), 727)
    from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
    from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
    ring = ExtensionRing(16, q.defining_polynomial)
    points = distinct_residue_points(ring, 727, max_points=727)
    assert len(set(points)) == 727
    # Unique parity vectors prove every pairwise difference is a unit.
    assert len({tuple(x & 1 for x in point) for point in points}) == 727


def test_cache_identity_binds_precision_schedule_and_creation():
    p, _ = fixture()
    key = computation_key(p, ((2, 1),))
    assert key == computation_key(replace(p, ancestry_digest='a'*64), ((2, 1),))
    assert key != computation_key(replace(p, precision=p.precision+1), ((2, 1),))
    assert key != computation_key(p, ((2, 2),))
    from veritas.research.tapered_v4.source_recipes import make_reference
    v = p.vertices[0]
    ref = make_reference(kind='dense', arity=v.tensor.arity, creation_precision=v.tensor.creation_precision-1,
        defining_polynomial=p.defining_polynomial, jet_length=1, data=decode(v.tensor.description)['data'])
    changed = replace(p, vertices=(replace(v, tensor=ref), *p.vertices[1:]))
    assert key != computation_key(changed, ((2, 1),))
    cache = ExactCache(80)
    cache.put('a'*64, ((1, 2),))
    cache.put('b'*64, ((3, 4),))
    assert cache.get('a'*64) is None and cache.get('b'*64) == ((3, 4),)
    assert cache.report()['evictions'] == 1


def test_lazy_modes_and_certified_early_cancellation():
    p, layout = fixture(u=2)
    budget = Budget()
    stream = iter_packet_components(p, layout, 1, (1, 0, 0, 0), budget=budget)
    assert budget.work == 0
    assert next(stream)[0] in ('cross', 'local')
    degree = certify_row_degree(p, layout.a, budget=budget)
    reduced = build_packet_modes(p, layout, 1, (1, 0, 0, 0), budget=budget, row_certificate=degree)
    verify_packet_modes(p, layout, reduced, budget=budget)
    assert any(m['exponent'] > 0 for m in reduced.certificate['modes'])
    bad = reduced.certificate
    bad['row_cancellation']['nonconstant_row_ports'] = []
    with pytest.raises(ValueError):
        verify_packet_modes(p, layout, ModeSet(layout.content_digest, canonical(bad)), budget=budget)


def test_online_recovery_matches_batch_multiple_valuations():
    p, layout = fixture(u=2)
    budget = Budget()
    recovery = StreamRecovery(p, layout, budget=budget)
    independent = StreamRecovery(p, layout, budget=budget, independent=True)
    rows = []
    for t, zeta, precision in packet_points(p, layout, recovery.plan, budget=budget):
        modes = build_packet_modes(p, layout, t, zeta, budget=budget)
        value = parent_point(p, layout, modes, budget=budget)
        row = [t, list(zeta), precision, list(value[0])]
        rows.append(row)
        recovery.add(*row)
        independent.add(*row)
    expected, _ = recover_packet_grid(p, layout, rows, budget=budget)
    assert recovery.finish() == independent.finish() == expected
    assert recovery.polynomial == recovery.basis == []
    with pytest.raises(ValueError):
        recovery.add(*rows[0])
    incomplete = StreamRecovery(p, layout, budget=budget)
    with pytest.raises(ValueError):
        incomplete.finish()
    wrong = rows[0].copy(); wrong[2] -= 1
    with pytest.raises(ValueError):
        incomplete.add(*wrong)


@pytest.fixture(scope='module')
def run_stream():
    parent = load_input(ROOT/'examples/r98_general_matching22.json')
    events = []
    result = contract_streaming(parent, policy=POLICY, evidence_sink=events.append)
    assert result['status'] == 'PASS_FINITE_STREAMED_TAPERED_RECURSION', result
    assert result['cache']['hits'] > 0
    assert result['ledger']['actual_calls'] < result['requests'] == 8577
    assert result['ledger']['point_evaluations'] == 134
    # Each independent matching edge contracts to 2*5 + 3*7 = 31.
    data = decode(parent.vertices[-1].tensor.description)['data']
    c0, c1 = data[0][0][0], data[1][0][0]
    assert result['result'][0][0] == pow(2*c0+3*c1, 22, 1 << parent.precision)
    return parent, events, result


def test_recursive_consumer_streams_and_never_calls_producer(run_stream, monkeypatch):
    parent, events, report = run_stream
    import veritas.research.parent_child_r98.constructor as ctor
    import veritas.research.tapered_v4.source_recipes as entries
    monkeypatch.setattr(ctor, 'construct_children', lambda *a, **k: pytest.fail('production constructor'))
    monkeypatch.setattr(entries, 'evaluate_compiled', lambda *a, **k: pytest.fail('production evaluator'))
    checked = verify_streaming(parent, iter(events), report, policy=POLICY)
    assert checked['status'] == 'PASS_INDEPENDENT_STREAMED_RECURSION', checked


@pytest.mark.parametrize('attack', ['drop', 'duplicate', 'creation', 'reuse', 'value', 'precision'])
def test_recursive_stream_mutations_fail_closed(run_stream, attack):
    parent, original, report = run_stream
    events = list(original)
    if attack == 'drop': events.pop()
    elif attack == 'duplicate': events.insert(2, events[2])
    else:
        kind = {'creation':'start', 'reuse':'reuse', 'value':'leaf', 'precision':'point'}[attack]
        index = next(i for i, raw in enumerate(events) if decode(raw)['kind'] == kind)
        record = decode(events[index])
        if attack == 'creation': record['row_certificate']['parent_digest'] = '0'*64
        elif attack == 'reuse': record['key'] = '0'*64
        elif attack == 'value': record['result'][0][0] ^= 1
        else: record['original']['precision'] -= 1
        events[index] = canonical(record)
    checked = verify_streaming(parent, iter(events), report, policy=POLICY)
    assert 'result' not in checked


def test_streaming_resource_failure_has_no_result():
    parent = load_input(ROOT/'examples/r98_general_matching22.json')
    report = contract_streaming(parent, policy=replace(POLICY, max_calls=1))
    assert 'result' not in report and report['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'


def test_constant_rows_cancel_before_geometric_expansion():
    from veritas.research.tapered_v4.source_recipes import make_reference
    from veritas.research.parent_child_r99.support import fold_source_forms, build_support
    from veritas.research.parent_child_r99.support_check import verify_support
    p, layout = fixture(u=2)
    vertices = []
    for vertex in p.vertices:
        if vertex.side == 'row':
            ref = vertex.tensor
            data = decode(ref.description)['data']
            vertex = replace(vertex, tensor=make_reference(kind='dense', arity=ref.arity,
                creation_precision=ref.creation_precision, defining_polynomial=ref.defining_polynomial,
                jet_length=1, data=[data[0]] * len(data)))
        vertices.append(vertex)
    p = replace(p, vertices=tuple(vertices))
    layout = replace(layout, parent_digest=p.content_digest)
    b = Budget()
    row = certify_row_degree(p, layout.a, budget=b)
    original = build_packet_modes(p, layout, 1, (1, 0, 0, 0), budget=b)
    reduced = build_packet_modes(p, layout, 1, (1, 0, 0, 0), budget=b, row_certificate=row)
    assert original.certificate['modes'] and reduced.certificate['modes'] == []
    assert original.certificate['cross_pairs'] == reduced.certificate['cross_pairs']
    folded = fold_source_forms(p, layout, reduced, budget=b)
    support = build_support(reduced, folded, budget=b, row_certificate=row)
    verify_support(p, layout, reduced, folded, support, budget=b)
    from veritas.research.parent_child_r99.supported_engine import evaluate_supported_point
    value, _ = evaluate_supported_point(p, layout, reduced, budget=b, row_certificate=row)
    assert value == parent_point(p, layout, original, budget=b)


def test_leaf_stream_does_not_claim_hermite():
    p, _ = fixture()
    events = []
    report = contract_streaming(p, policy=POLICY, evidence_sink=events.append)
    assert report['status'] == 'PASS_FINITE_STREAMED_TAPERED_RECURSION'
    assert not report['source_tapered_functional_used']
    assert verify_streaming(p, events, report, policy=POLICY)['status'] == 'PASS_INDEPENDENT_STREAMED_RECURSION'


def test_non_scalar_root_cannot_be_reinterpreted_in_another_field():
    from veritas.research.tapered_v4.source_recipes import make_reference
    p, _ = fixture()
    v = p.vertices[0]
    data = decode(v.tensor.description)['data']; data[0][0][1] = 1
    ref = make_reference(kind='dense', arity=v.tensor.arity, creation_precision=v.tensor.creation_precision,
        defining_polynomial=p.defining_polynomial, jet_length=1, data=data)
    p = replace(p, vertices=(replace(v, tensor=ref), *p.vertices[1:]))
    with pytest.raises(ValueError, match='certified embedding'):
        prepare_scalar_field(p, 727)
