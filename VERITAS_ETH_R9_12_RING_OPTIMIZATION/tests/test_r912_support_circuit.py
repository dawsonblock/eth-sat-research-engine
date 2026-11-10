from dataclasses import replace
from itertools import product
from pathlib import Path
import random
from types import SimpleNamespace

import pytest

from veritas.research.parent_child_r98.model import Budget, Refusal, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r99.support import build_support, fold_source_forms
from veritas.research.parent_child_r99.support_circuit import SupportCircuit
from veritas.research.parent_child_r912.jet_recovery import JetRecovery

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=2_000_000_000, max_seconds=600,
                 max_certificate_bytes=100_000_000)


def mode_set(modes, precision):
    certificate = {'modes': modes, 'precision': precision, 'mode_tuple_count': 0}
    return SimpleNamespace(certificate=certificate, content_digest='0'*64)


def explicit(modes, precision, row_certificate=None):
    folded = mode_set(modes, precision)
    return build_support(folded, folded, budget=Budget(POLICY), row_certificate=row_certificate).record['tuples']


def random_modes(rng):
    count = rng.randint(1, 7)
    rows = [(rng.randrange(2), r) for r in range(rng.randint(0, 6))]
    modes = []
    for mid in range(count):
        packet = rng.randrange(2)
        own = [row for p, row in rows if p == packet and rng.random() < 0.5]
        modes.append({'packet': packet, 'weight': rng.randrange(0, 4), 'rows': [[row, None] for row in own]})
    return modes


def test_random_differential_against_explicit_enumeration():
    rng = random.Random(9120)
    for _ in range(400):
        modes, precision = random_modes(rng), rng.randint(1, 9)
        certificate = None
        if rng.random() < 0.3:
            certificate = {'nonconstant_row_ports': sorted({row for m in modes for row, _ in m['rows']
                                                            if rng.random() < 0.6})}
        expected = sorted(map(tuple, explicit(modes, precision, certificate)))
        circuit = SupportCircuit(modes, precision, budget=Budget(POLICY), row_certificate=certificate)
        assert circuit.count() == len(expected)
        assert circuit.tuples(limit=10**6) == expected
        members = set(expected)
        for beta in product(range(3), repeat=len(modes)) if len(modes) <= 4 else expected[:20]:
            assert circuit.contains(tuple(beta)) == (tuple(beta) in members)


def test_equal_valuation_distinct_vectors_are_never_merged():
    modes = [{'packet': 0, 'weight': 2, 'rows': [[0, None]]},
             {'packet': 0, 'weight': 2, 'rows': [[1, None]]},
             {'packet': 1, 'weight': 2, 'rows': [[0, None]]}]
    expected = sorted(map(tuple, explicit(modes, 4)))
    assert expected == [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)]
    circuit = SupportCircuit(modes, 4, budget=Budget(POLICY))
    # The diagram keeps one weight-2 state, yet all three weight-2 vectors survive.
    assert max(len(layer) for layer in circuit.layers) == 2
    assert circuit.count() == 4 and circuit.tuples(limit=4) == expected
    assert all(circuit.contains(beta) for beta in expected)
    assert not circuit.contains((1, 1, 0))


def test_shared_power_nodes_and_expansion_limit():
    modes = [{'packet': 0, 'weight': 1, 'rows': [[r, None] for r in range(5)]},
             {'packet': 0, 'weight': 1, 'rows': [[r, None] for r in range(5)]}]
    circuit = SupportCircuit(modes, 100, budget=Budget(POLICY))
    assert circuit.summary()['power_nodes'] == 1 and circuit.summary()['rows'] == 5
    assert circuit.count() == len(explicit(modes, 100)) == 21
    with pytest.raises(Refusal):
        circuit.tuples(limit=20)
    with pytest.raises(ValueError):
        SupportCircuit([{'packet': 0, 'weight': -1, 'rows': [[0, None]]}], 3, budget=Budget(POLICY))


def _points(parent, layout, a=1):
    b = Budget(POLICY)
    certificate = certify_row_degree(parent, a, budget=b)
    recovery = JetRecovery(parent, layout, certificate, budget=b, max_points=4096)
    for t, zeta, _ in recovery.points():
        original = build_packet_modes(parent, layout, t, zeta, budget=b, row_certificate=certificate)
        yield original, fold_source_forms(parent, layout, original, budget=b), certificate, b


def test_real_packet_points_match_explicit_support():
    parent = load_input(ROOT/'examples/r98_general_matching22.json')
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(POLICY))
    checked = 0
    for original, folded, certificate, b in _points(parent, layout):
        record = folded.certificate
        circuit = SupportCircuit(record['modes'], record['precision'], budget=b, row_certificate=certificate)
        tuples = build_support(original, folded, budget=b, row_certificate=certificate).record['tuples']
        assert circuit.tuples(limit=10**6) == sorted(map(tuple, tuples))
        checked += 1
    assert checked > 1


def test_96_wire_root_support_is_the_full_cube(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('probe', ROOT/'scripts/experiment_r912_interaction.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    source = tmp_path/'input.json'
    source.write_bytes(canonical(probe.graph()))
    parent = load_input(source, max_extension_degree=12)
    layout = probe.separated_layout(parent, 1, 1, Budget(POLICY))
    for index, (original, folded, certificate, b) in enumerate(_points(parent, layout)):
        record = folded.certificate
        circuit = SupportCircuit(record['modes'], record['precision'], budget=b, row_certificate=certificate)
        if index == 0:
            assert circuit.count() == 1
            continue
        summary = circuit.summary()
        assert circuit.count() == 2**96
        assert summary['components'] == 96 and summary['largest_local_support'] == 2
        with pytest.raises(Refusal, match='complete supported tuple cap'):
            build_support(original, folded, budget=b, row_certificate=certificate)
        ports = certificate['nonconstant_row_ports']
        for size in (1, 5, 10, 12):
            restricted = dict(certificate, nonconstant_row_ports=ports[::7][:size])
            tuples = build_support(original, folded, budget=b, row_certificate=restricted).record['tuples']
            small = SupportCircuit(record['modes'], record['precision'], budget=b, row_certificate=restricted)
            assert small.count() == len(tuples) == 2**size
            assert small.tuples(limit=4096) == sorted(map(tuple, tuples))
        break


def test_jet_packet_points_match_explicit_support():
    from test_r912_jets import jet_matching, multilevel_layout
    parent = jet_matching()
    sizes = []
    for a in (1, 2):
        layout = multilevel_layout(parent, a, a, Budget(POLICY))
        for original, folded, certificate, b in _points(parent, layout, a):
            record = folded.certificate
            circuit = SupportCircuit(record['modes'], record['precision'], budget=b, row_certificate=certificate)
            tuples = build_support(original, folded, budget=b, row_certificate=certificate).record['tuples']
            assert circuit.tuples(limit=10**6) == sorted(map(tuple, tuples))
            sizes.append(circuit.count())
    assert max(sizes) > 1
