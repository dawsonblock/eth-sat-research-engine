from itertools import product
from random import Random

import pytest

from veritas.research.eth_packing_v26.symbolic_regular import (RegularPackingWitness,
                                                               MultiCoordinateRegularPackingWitness)
from veritas.research.eth_packing_v26.implicit import ImplicitPacking, check_implicit_packing


def test_complete_small_family_has_a_bijection_without_padding():
    witness = RegularPackingWitness(radix=3, degree=4, copies=2)
    addresses = set()
    for edge in product(range(3), range(3), range(2), range(4), range(4)):
        slot = witness.edge_to_slot(edge)
        assert witness.slot_to_edge(slot) == edge
        addresses.add(slot)
    expected = set()
    for low in range(3):
        for high in range(low, 3):
            n = witness.class_edges // 2 if low == high else witness.class_edges
            expected.update((low, high, index, bit) for index in range(n) for bit in (0, 1))
    assert addresses == expected
    assert len(addresses) == witness.edge_count == 2 * witness.packet_count


def test_full_radix_witness_is_packing_eligible_without_edge_materialization():
    witness = RegularPackingWitness(radix=64, degree=4, copies=2048)
    audit = witness.audit()
    assert audit['parent_edges'] == 134_217_728
    assert audit['vertices'] == 67_108_864
    assert audit['packets'] == 67_108_864
    assert audit['row_load_each_group'] == audit['column_load_each_group'] == 2_097_152
    assert audit['child_edges_each_group'] == 4_194_304
    for key in ('packing_numeric_conditions', 'packing_count_bound', 'side_load_bound',
                'child_six_M_over_r_bound', 'strict_one_eighth_shrink', 'three_M_over_32_bound'):
        assert audit[key]
    for key in ('manuscript_active_schedule_compatible', 'full_contraction_executed', 'deterministic_constructor_replayed',
                'uniform_complexity_proven'):
        assert not audit[key]
    rng = Random(20261102)
    edges = [(0, 0, 0, 0, 0), (63, 0, 2047, 3, 3), (63, 63, 2047, 3, 3)]
    edges.extend((rng.randrange(64), rng.randrange(64), rng.randrange(2048),
                  rng.randrange(4), rng.randrange(4)) for _ in range(100))
    for edge in edges:
        assert witness.slot_to_edge(witness.edge_to_slot(edge)) == edge


def test_small_eligible_graph_matches_existing_independent_packet_checker():
    witness = RegularPackingWitness(2, 4, 2)
    edges, rows, columns, classes = [], {}, {}, {}
    for row, col, copy, i, j in product(range(2), range(2), range(2), range(4), range(4)):
        component = (row * 2 + col) * 2 + copy
        u, v = component * 4 + i, component * 4 + j
        rows[u], columns[v] = (row,), (col,)
        classes.setdefault(((row,), (col,)), []).append(len(edges))
        edges.append((u, v))
    classes = {key: tuple(value) for key, value in classes.items()}
    # The generic checker independently reconstructs classes and real slots.
    score = 4 * sum(len(value) ** 2 for value in classes.values())
    packing = ImplicitPacking(tuple(edges), 2, 1, witness.class_edges, rows, columns,
                              classes, 0, score, ())
    checked = check_implicit_packing(packing)
    assert checked['valid'] and checked['d3_numeric_preconditions']
    assert checked['packing_count_bound'] and checked['symbol_port_bound']
    for eid, edge in enumerate(product(range(2), range(2), range(2), range(4), range(4))):
        low, high, index, bit = witness.edge_to_slot(edge)
        assert packing.packet_slot(((low, high),), index, bit) == eid


def test_numeric_premises_are_not_assumed_from_balanced_labels():
    witness = RegularPackingWitness(radix=64, degree=4, copies=2047)
    assert not witness.audit()['packing_numeric_conditions']
    assert witness.audit()['strict_one_eighth_shrink']


@pytest.mark.parametrize('args', [(True, 4, 1), (1, 4, 1), (65, 4, 1),
                                  (2, 3, 1), (2, 5, 1), (2, 4, 0),
                                  (2, 4, (1 << 24) + 1)])
def test_invalid_family_inputs_are_rejected(args):
    with pytest.raises(ValueError):
        RegularPackingWitness(*args)


@pytest.mark.parametrize('edge', [(0, 0, 0, 0, True), (0, 2, 0, 0, 0),
                                  (0, 0, 1, 0, 0), (0, 0, 0, 4, 0)])
def test_invalid_edge_addresses_are_rejected(edge):
    with pytest.raises(ValueError):
        RegularPackingWitness(2, 4, 1).edge_to_slot(edge)


@pytest.mark.parametrize('slot', [(1, 0, 0, 0), (0, 2, 0, 0), (0, 0, 8, 0),
                                  (0, 1, 16, 0), (0, 1, 0, 2)])
def test_invalid_packet_slot_addresses_are_rejected(slot):
    with pytest.raises(ValueError):
        RegularPackingWitness(2, 4, 1).slot_to_edge(slot)


def test_two_coordinate_witness_matches_every_generic_packet_slot():
    # This materialized instance meets the sufficient packing inequalities:
    # D=16, L=4, delta=8 and M=4096=2*D^2*delta.
    witness = MultiCoordinateRegularPackingWitness(2, 2, 8, 4)
    words = list(product(range(2), repeat=2))
    edges, rows, columns, classes, original = [], {}, {}, {}, []
    for row, col, copy, i, j in product(words, words, range(4), range(8), range(8)):
        component = ((words.index(row) * len(words) + words.index(col)) * 4 + copy)
        u, v = component * 8 + i, component * 8 + j
        rows[u], columns[v] = row, col
        classes.setdefault((row, col), []).append(len(edges))
        edges.append((u, v))
        original.append((row, col, copy, i, j))
    classes = {key: tuple(value) for key, value in classes.items()}
    score = 16 * sum(len(value) ** 2 for value in classes.values())
    packing = ImplicitPacking(tuple(edges), 2, 2, witness.class_edges, rows, columns,
                              classes, 0, score, ())
    check = check_implicit_packing(packing)
    assert check['valid'] and check['d3_numeric_preconditions']
    assert check['packing_count_bound'] and check['symbol_port_bound']
    slots = set()
    for eid, edge in enumerate(original):
        pairs, index, bits = witness.edge_to_slot(edge)
        assert witness.slot_to_edge((pairs, index, bits)) == edge
        assert packing.packet_slot(pairs, index, bits) == eid
        slots.add((pairs, index, bits))
    assert len(slots) == len(edges) == witness.L * witness.packet_count


def test_active_root_schedule_with_symbolic_graph_and_shrinking_loads():
    from veritas.research.appendix_d_schedule import schedule_preflight
    exponent = 131080
    witness = MultiCoordinateRegularPackingWitness(64, 2, 8, 1 << (exponent - 30))
    s = 1 << exponent
    assert witness.edge_count == s
    scheduled_delta = 1 << (9 * exponent // 10)
    packing = witness.audit(degree_bound=scheduled_delta)
    assert packing['packing_numeric_conditions']
    assert packing['strict_one_eighth_shrink'] and packing['three_M_over_32_bound']
    assert packing['row_load_each_group'] == s // 64
    assert packing['child_half_wires_each_group'] == s // 32
    check = schedule_preflight(s, witness.edge_count, witness.degree, 0,
                               max_size_bits=exponent + 1)
    assert check['status'] == 'ACTIVE_NUMERIC_PRECONDITIONS_MET'
    assert (check['u'], check['a'], check['degree_limit']) == (1, 2, scheduled_delta)
    assert not packing['manuscript_schedule_verified']
    assert not packing['full_contraction_executed']
    assert not packing['deterministic_constructor_replayed']


@pytest.mark.parametrize('a', [3, 4])
def test_higher_coordinate_slot_bits_match_independent_packet_lookup(a):
    witness = MultiCoordinateRegularPackingWitness(2, a, 2 * (1 << a), 1)
    rng = Random(20261102 + a)
    offsets = tuple(range(witness.class_edges))
    for _ in range(100):
        row = tuple(rng.randrange(2) for _ in range(a))
        col = tuple(rng.randrange(2) for _ in range(a))
        i, j = rng.randrange(witness.degree), rng.randrange(witness.degree)
        edge = (row, col, 0, i, j)
        pairs, index, bits = witness.edge_to_slot(edge)
        # This reader decodes orientation and equal-coordinate bits using the
        # existing generic D.3 packet representation, not this witness.
        packing = ImplicitPacking((), 2, a, witness.class_edges, {}, {},
                                  {(row, col): offsets}, 0, 0, ())
        assert packing.packet_slot(pairs, index, bits) == i * witness.degree + j
        assert witness.slot_to_edge((pairs, index, bits)) == edge


def test_multi_coordinate_input_and_slot_validation():
    for args in ((64, 0, 8, 1), (64, 2, 4, 1), (64, 2, 9, 1),
                 (64, 2, 8, 1 << 262144)):
        with pytest.raises(ValueError):
            MultiCoordinateRegularPackingWitness(*args)
    witness = MultiCoordinateRegularPackingWitness(2, 2, 8, 1)
    edge = ((0, 0), (1, 1), 0, 0, 0)
    assert witness.slot_to_edge(witness.edge_to_slot(edge)) == edge
    for address in (((), 0, 0), (((0, 1), (0, 1)), 0, 4),
                    (((0, 1), (1, 0)), 0, 0)):
        with pytest.raises(ValueError):
            witness.slot_to_edge(address)
    with pytest.raises(ValueError):
        witness.audit(degree_bound=7)


def test_symbolic_theorem_root_script_reports_scope_and_exact_checks():
    import json
    from pathlib import Path
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_symbolic_theorem_root.py'
    output = subprocess.run([sys.executable, str(script)], check=True, capture_output=True,
                            text=True, timeout=10)
    result = json.loads(output.stdout)
    assert result['scope'] == 'STRUCTURED_SYMBOLIC_ROOT_PACKING_ONLY'
    assert result['schedule_status'] == 'ACTIVE_NUMERIC_PRECONDITIONS_MET'
    assert (result['schedule_u'], result['schedule_a']) == (1, 2)
    assert all(result['schedule_numeric_preconditions'].values())
    for flag in ('packing_numeric_conditions', 'boundary_slot_roundtrips',
                 'each_side_load_is_M_over_64', 'each_group_half_wires_are_M_over_32',
                 'strict_one_eighth_shrink'):
        assert result[flag] is True
    for flag in ('deterministic_constructor_replayed', 'children_constructed',
                 'full_contraction_executed', 'uniform_complexity_proven'):
        assert result[flag] is False
