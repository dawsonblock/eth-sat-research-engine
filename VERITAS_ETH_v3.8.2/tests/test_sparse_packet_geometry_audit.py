from copy import deepcopy

from veritas.research.eth_packing_v26.geometry_audit import audit_sparse_packet_geometry
from veritas.research.eth_packing_v26.implicit import (
    SPARSE_MODE_SCHEMA, check_implicit_mode_source, construct_implicit_packing,
    implicit_sparse_mode_source,
)


def arbitrary_labeled_source():
    return {
        'schema': SPARSE_MODE_SCHEMA,
        'claim': 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS',
        'r': 2, 'a': 1, 'L': 2, 'D': 4, 'M': 2, 'H_pad': 2,
        'edges': [[0, 0], [1, 1]],
        'row_labels': {'0': [0], '1': [1]},
        'column_labels': {'0': [0], '1': [1]},
        'packets': [
            {'symbol_pairs': [[0, 0]], 'index': 0, 'occupied_slots': [[0, 0]]},
            {'symbol_pairs': [[1, 1]], 'index': 0, 'occupied_slots': [[0, 1]]},
        ],
    }


def test_audits_valid_noncanonical_labels_without_claiming_a_trace():
    source = arbitrary_labeled_source()
    assert not check_implicit_mode_source(source)['valid']
    audit = audit_sparse_packet_geometry(source)
    assert audit['valid']
    assert not audit['deterministic_trace_verified']
    assert not audit['constructed_children_verified']
    assert not audit['contraction_identity_verified']
    assert not audit['uniform_theorem_proven']
    coordinate = audit['coordinates'][0]
    assert coordinate['per_side_port_bound']
    assert coordinate['per_child_six_M_over_r']
    assert [item['predicted_child_wires'] for item in coordinate['groups']] == [2, 2]


def test_real_constructor_source_checks_every_coordinate_load():
    edges = [(0, 1), (1, 0), (1, 1), (2, 0), (2, 1)]
    source = implicit_sparse_mode_source(construct_implicit_packing(edges, r=3, a=2))
    audit = audit_sparse_packet_geometry(source)
    assert audit['valid']
    assert audit['coordinate_count'] == 2
    for result in audit['coordinates']:
        assert sum(group['predicted_child_wires'] for group in result['groups']) == 2 * len(edges)
        if result['per_side_port_bound']:
            assert result['per_child_six_M_over_r']


def test_geometry_rejects_forged_orientation_slot_coverage_and_padding():
    original = arbitrary_labeled_source()
    wrong_orientation = deepcopy(original)
    wrong_orientation['packets'][0]['symbol_pairs'] = [[0, 1]]
    wrong_orientation['packets'][0]['occupied_slots'] = [[1, 0]]
    duplicate = deepcopy(original)
    duplicate['packets'][1]['occupied_slots'] = [[0, 0]]
    omitted = deepcopy(original)
    omitted['packets'].pop()
    padding = deepcopy(original)
    padding['H_pad'] = 1
    for source in (wrong_orientation, duplicate, omitted, padding):
        assert not audit_sparse_packet_geometry(source)['valid']
    assert audit_sparse_packet_geometry(original, max_work=1)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
