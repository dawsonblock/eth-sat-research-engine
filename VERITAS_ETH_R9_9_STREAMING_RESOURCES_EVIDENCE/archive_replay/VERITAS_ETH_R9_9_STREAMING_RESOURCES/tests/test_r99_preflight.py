from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r98.model import Budget, ExponentTuple, canonical, decode
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.conformance import conformance_ledger
from veritas.research.parent_child_r99.execution import (
    ExecutionSpec, ScheduleKind, TupleStrategy, RecoveryKind, LeafKind, execute,
)
from veritas.research.parent_child_r99.preflight import (
    two_level_call_floor, preflight_packet_recursion, compare_group_counts,
    project_packet_children, verify_projected_children,
)
from test_r99_general_packets import fixture

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_calls=2_000_000, max_work=1_000_000_000)


@pytest.mark.parametrize('options', [
    {'groups': 512}, {'schedule': [[1, 1]]}, {'schedule': ((True, 1),)},
    {'schedule_kind': 'FINITE_SCALED_EXPERIMENT'}, {'leaves': LeafKind.SOURCE},
    {'recovery': RecoveryKind.DEGREE}, {'schedule_kind': ScheduleKind.SOURCE},
    {'schedule_kind': ScheduleKind.SOURCE, 'schedule': (), 'leaves': LeafKind.SOURCE,
     'tuples': TupleStrategy.SUPPORT},
])
def test_incompatible_execution_choices_rejected(options):
    with pytest.raises((TypeError, ValueError)):
        ExecutionSpec(**options)


def test_execution_digest_and_source_selector_never_activate_finite(monkeypatch):
    spec = ExecutionSpec()
    assert spec.content_digest == ExecutionSpec().content_digest
    assert spec.content_digest != replace(spec, tuples=TupleStrategy.SUPPORT).content_digest
    import veritas.research.parent_child_r99.engine as engine
    monkeypatch.setattr(engine, 'contract_packet_recursion', lambda *a, **k: pytest.fail('finite path called'))
    parent, _ = fixture()
    source = ExecutionSpec(schedule_kind=ScheduleKind.SOURCE, schedule=(), leaves=LeafKind.SOURCE)
    report = execute(parent, source, policy=POLICY)
    assert report['status'] == 'INCONCLUSIVE_SOURCE_REFINEMENT'
    assert 'result' not in report and not report['source_qualified']


def test_two_level_minimum_is_incompatible_with_existing_call_policy():
    record = two_level_call_floor()
    m, M = record['minimum_active_child_edges'], record['minimum_parent_edges']
    assert all(3 * n // 64 == 0 for n in range(1, m))
    assert all(6 * n < 64 * m for n in range(M))
    assert record['minimum_calls'] == 1 + 2 * 706 * (63 + 1 + 64 * 134) == 12_199_681
    assert record['minimum_calls'] > POLICY.max_calls


def test_general_multislot_projection_matches_actual_children(monkeypatch):
    parent, layout = fixture(u=2)
    modes = build_packet_modes(parent, layout, -2, (0, 0, 0, 0), budget=Budget())
    beta = ExponentTuple(modes.content_digest, (0,) * len(modes.certificate['modes']))
    children = construct_children(parent, layout, modes, beta, budget=Budget(), _admitted=True)
    import veritas.research.parent_child_r98.constructor as constructor
    import veritas.research.parent_child_r99.basis as basis
    def forbidden(*a, **k):
        pytest.fail('preflight evaluated arithmetic or called constructor')
    monkeypatch.setattr(constructor, 'construct_children', forbidden)
    monkeypatch.setattr(basis, 'build_packet_modes', forbidden)
    projected = verify_projected_children(parent, layout, modes, children, budget=Budget())
    assert len(projected) == 64 and sum(c.topology.edges for c in projected) == 4
    assert len(projected[0].packet_ids) == 1  # multi-slot packet stays one vertex
    with pytest.raises(ValueError, match='missing group'):
        verify_projected_children(parent, layout, modes, children[:-1], budget=Budget())
    corrupt = replace(children[0], edge_map=tuple(tuple([*row[:3], row[3] ^ 1, *row[4:]])
                                                for row in children[0].edge_map))
    with pytest.raises(ValueError, match='projection'):
        verify_projected_children(parent, layout, modes, (corrupt, *children[1:]), budget=Budget())


def test_single_level_preflight_has_exact_grid_floor_without_entries(monkeypatch):
    parent = load_input(ROOT / 'examples/r98_general_matching22.json')
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(POLICY))
    import veritas.research.parent_child_r98.engine as engine
    monkeypatch.setattr(engine, 'leaf', lambda *a, **k: pytest.fail('preflight contracted a node'))
    report = preflight_packet_recursion(parent, layout, ExecutionSpec(), policy=POLICY)
    assert report['status'] == 'PASS_FINITE_NECESSARY_CONDITIONS', report
    assert report['recursive_calls_lower_bound'] == 8577
    assert report['descendant_topologies_complete']
    assert report['nodes'][0]['coordinates'][0]['tuple_count_status'] == 'EXACT_ONE_NO_CROSSING'
    assert 'result' not in report and not report['launch_authorized_by_preflight']


def test_two_level_refusal_precedes_modes_and_hermite_weights(monkeypatch):
    parent = load_input(ROOT / 'examples/r99_nonconstant_matching242.json')
    import veritas.research.parent_child_r99.engine as engine
    def forbidden(*a, **k):
        pytest.fail('arithmetic started before structural preflight refusal')
    monkeypatch.setattr(engine, 'make_packet_plan', forbidden)
    monkeypatch.setattr(engine, 'build_packet_modes', forbidden)
    report = engine.contract_packet_recursion(parent, schedule=((1, 1), (1, 1)),
        layout_factory=lambda call, a, u, budget: construct_vertex_shrinking_layout(call, budget=budget),
        policy=POLICY, max_points=4096, point_strategy='certified_support')
    assert report['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert report['ledger']['actual_calls'] == 1 and report['ledger']['point_evaluations'] == 0
    assert report['preflight']['recursive_calls_lower_bound'] >= two_level_call_floor()['minimum_calls']
    assert 'result' not in report


def test_preflight_work_is_charged_to_the_total_production_budget(monkeypatch):
    import veritas.research.parent_child_r99.engine as engine
    parent = load_input(ROOT / 'examples/r98_general_matching22.json')
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(POLICY))
    monkeypatch.setattr(engine, 'preflight_packet_recursion', lambda *a, **k: {
        'status': 'PASS_FINITE_NECESSARY_CONDITIONS', 'preflight_work_units': 10,
        'recursive_calls_lower_bound': 1})
    monkeypatch.setattr(engine, 'make_packet_plan', lambda *a, **k: pytest.fail('exhausted budget continued'))
    report = engine.contract_packet_recursion(parent, schedule=((1, 1),),
        layout_factory=lambda *a: layout, policy=replace(POLICY, max_work=10))
    assert report['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert report['ledger']['work_units'] > 10 and report['ledger']['actual_calls'] == 1
    assert 'result' not in report


def test_actual_cycle_group_candidates_are_nonmonotone():
    parent = load_input(ROOT / 'examples/r98_shrinking_cycle484.json')
    report = compare_group_counts(parent, policy=POLICY)
    cases = {r['groups']: r for r in report['candidates']}
    assert cases[64]['largest_edges_by_depth'] == {'0': 484, '1': 44, '2': 4}
    assert cases[64]['recursive_calls_lower_bound'] > POLICY.max_calls
    assert cases[512]['largest_edges_by_depth'] == {'0': 484, '1': 4}
    assert cases[512]['recursive_calls_lower_bound'] == 1_487_873
    assert cases[512]['root_crossing_pairs'] == 242
    assert cases[512]['root_nonzero_point_tuple_count'] > POLICY.max_tuples
    assert cases[512]['descendant_packing'] == 'PASS_TO_FOUR_EDGE_LEAVES'
    assert not cases[512]['general_r99_executor_supported']
    for count in (128, 256, 1024):
        assert cases[count]['descendant_packing'] == 'INCOMPLETE_OR_REFUSED'
    assert not report['tensor_entries_evaluated']


def test_symbolic_singleton_count_agrees_with_materialized_general_modes():
    parent = load_input(ROOT / 'examples/r98_transfer_cycle44.json')
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(POLICY))
    report = compare_group_counts(parent, (64,), policy=POLICY)['candidates'][0]
    e = parent.defining_polynomial.bit_length() - 1
    for t, point in ((-1, (0,) * e), (1, (1,) + (0,) * (e - 1))):
        modes = build_packet_modes(parent, layout, t, point, budget=Budget(POLICY))
        key = 'root_nonzero_point_tuple_count' if point[0] else 'root_zero_point_tuple_count'
        assert report[key] == modes.certificate['mode_tuple_count']


def test_preflight_binds_schedule_and_layout():
    parent, layout = fixture(u=2)
    report = preflight_packet_recursion(parent, layout, ExecutionSpec(), policy=POLICY)
    assert report['status'] == 'INVALID_PACKET_PREFLIGHT'
    assert 'differs' in report['reason'] and 'result' not in report


def test_conformance_binds_pinned_statements_without_proof_promotion():
    ledger = conformance_ledger()
    assert ledger['paper']['commit'] == '4eaee87548250b2682affda7d05d947c05554bae'
    assert len(ledger['paper']['files']) == 4
    assert all(len(r['statement']['statement_sha256']) == 64 and
               not r['universal_executable_correspondence_proved'] for r in ledger['obligations'])
    assert not ledger['source_qualified']


def test_external_group_cli_writes_new_evidence_only(tmp_path):
    from veritas.research.parent_child_r99.preflight_cli import main
    output = tmp_path / 'groups.json'
    argv = [str(ROOT / 'examples/r98_shrinking_cycle484.json'), '--output', str(output),
            '--compare-groups', '64,512', '--max-calls', '2000000']
    assert main(argv) == 0
    raw = output.read_bytes()
    report = decode(raw)
    assert report['candidates'][1]['recursive_calls_lower_bound'] == 1_487_873
    assert main(argv) == 2 and output.read_bytes() == raw


def test_constant_row_cancellation_keeps_complete_tapered_grid(tmp_path, monkeypatch):
    import json
    from veritas.research.parent_child_r98.model import PacketLayout
    from veritas.research.parent_child_r99.engine import contract_packet_recursion
    from veritas.research.parent_child_r99.supported_verify import verify_supported_point
    import veritas.research.parent_child_r99.supported_engine as supported
    data = json.loads((ROOT / 'examples/r98_general_matching22.json').read_text())
    for vertex in data['vertices']:
        if vertex['side'] == 'row':
            vertex['table'] = [2, 2]
    path = tmp_path / 'constant_rows.json'
    path.write_text(json.dumps(data))
    parent = load_input(path)
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(POLICY))
    src = layout.source
    src['column_labels']['0'], src['column_labels']['1'] = [1], [0]
    for packet in src['packets']:
        edge = packet['occupied_slots'][0][1]
        if edge in (0, 1):
            packet.update(symbol_pairs=[[0, 1]], index=edge, occupied_slots=[[edge, edge]])
    src['packets'].sort(key=lambda p: (p['symbol_pairs'], p['index']))
    layout = PacketLayout(parent.content_digest, 1, 1, canonical(src), layout.strategy)
    original, observed = supported.evaluate_supported_point, []
    def checked(call, packing, modes, **kwargs):
        assert kwargs['row_certificate']['nonconstant_row_ports'] == []
        value, certificate = original(call, packing, modes, **kwargs)
        # All 64 actual children in this one-level fixture are leaves. Replay
        # their stored values under the standalone leaf-point checker contract.
        replay = dict(certificate, child_value_method='EXACT_FOUR_EDGE_LEAVES')
        assert verify_supported_point(call, packing, replay, budget=Budget(POLICY))[0] == value
        assert len(certificate['support']['tuples']) == 1
        observed.append(modes.certificate['mode_tuple_count'])
        return value, certificate
    monkeypatch.setattr(supported, 'evaluate_supported_point', checked)
    report = contract_packet_recursion(parent, schedule=((1, 1),),
        layout_factory=lambda *a: layout, policy=POLICY, point_strategy='certified_support')
    assert report['status'] == 'PASS_FINITE_GENERAL_PACKET_RECURSION', report
    assert report['result'][0][0] == 24 ** 22
    assert report['source_tapered_functional_used']
    assert not report['original_weighted_stream_enumerated']
    assert report['ledger']['point_evaluations'] == len(observed) == 134
    assert report['ledger']['actual_calls'] == 8577
    assert max(observed) > 1
