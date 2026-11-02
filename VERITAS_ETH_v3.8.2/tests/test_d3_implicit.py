from dataclasses import replace
from types import MappingProxyType

import pytest

from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_packing_v26.implicit import (
    check_implicit_packing, construct_implicit_packing, materialize_finite_certificate,
    implicit_mode_source, implicit_sparse_mode_source, check_implicit_mode_source,
    audit_d3_child_wire_loads, construct_preconditioned_d3_packing,
    real_packet_slots,
)


@pytest.mark.parametrize('edges', [[], [(0, 0)], [(0, 0), (0, 0), (1, 1), (0, 1)]])
@pytest.mark.parametrize('a', [1, 2])
def test_lazy_packets_match_explicit_reference(edges, a):
    implicit = construct_implicit_packing(edges, r=2, a=a)
    explicit = construct_d3_packing(edges, r=2, a=a)
    assert implicit.H == explicit['H_pad']
    assert implicit.packet_count == len(explicit['packets'])
    streamed = list(implicit.iter_packets(max_packets=1000))
    assert [list(slots) for _, _, slots in streamed] == [p['slots'] for p in explicit['packets']]
    for pairs, index, slots in streamed:
        assert tuple(implicit.packet_slot(pairs, index, j) for j in range(implicit.L)) == slots
    assert check_implicit_packing(implicit)['valid']
    assert materialize_finite_certificate(implicit) == explicit


def test_fixed_radix_large_class_space_is_sparse_and_checked():
    edges = [(0, 0), (0, 1), (1, 0), (1, 1)]
    packing = construct_implicit_packing(edges, r=64, a=2)
    checked = check_implicit_packing(packing)
    assert checked['valid']
    assert checked['directed_classes'] == 64**4
    assert checked['nonempty_classes'] <= len(edges)
    assert checked['packet_count'] >= 64**4
    assert not checked['universal_theorem_proven']
    with pytest.raises(ValueError, match='budget'):
        next(packing.iter_packets(max_packets=10))
    with pytest.raises(ValueError, match='budget'):
        materialize_finite_certificate(packing)


def test_sparse_slot_source_handles_large_packet_width_without_dense_padding():
    edges = [(0, 0), (0, 1), (1, 0), (1, 1)]
    packing = construct_implicit_packing(edges, r=64, a=9)
    source = implicit_sparse_mode_source(packing)
    checked = check_implicit_mode_source(source)
    assert checked['valid']
    assert checked['empty_packet_slots_materialized'] is False
    assert packing.L == 512
    assert packing.D == 64**18
    assert len(source['packets']) <= len(edges)
    assert all('slots' not in packet and
               len(packet['occupied_slots']) <= len(edges)
               for packet in source['packets'])
    for packet in source['packets']:
        assert real_packet_slots(packet, packing.L)


def test_sparse_slot_source_is_consumed_by_geometric_mode_engine():
    from veritas.core.cnf import CNF
    from veritas.research.tensor import from_cnf
    from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
    from veritas.research.eth_recursive_contraction_v39.point_modes import (
        make_point_modes, check_point_modes,
    )

    network = from_cnf(CNF.from_lists(2, [[1, 2]]))
    packing = construct_implicit_packing(make_bipartite_edges(network), r=2, a=1)
    source = implicit_sparse_mode_source(packing)
    modes = make_point_modes(source, node=1, precision=5, extension_degree=3)
    assert check_point_modes(modes)['valid']
    assert modes['d3_certificate']['schema'].endswith('SPARSE_ACTIVE_V1')


def test_implicit_checker_replays_conditional_expectation_trace():
    packing = construct_implicit_packing([(0, 0), (0, 1), (1, 1)], r=2, a=2)
    replay = check_implicit_packing(packing, check_trace=True)
    assert replay['valid']
    assert replay['conditional_expectation_trace_verified']
    changed = replace(packing, trace=packing.trace[:-1])
    assert not check_implicit_packing(changed, check_trace=True)['valid']


def test_child_wire_audit_never_promotes_a_single_packing_to_theorem():
    packing = construct_implicit_packing([(i, i) for i in range(16)], r=64, a=1)
    report = audit_d3_child_wire_loads(packing, coordinate=0)
    assert report['valid']
    assert report['claim'] == 'ONE_PACKING_INSTANCE_ONLY'
    assert not report['universal_theorem_proven']
    assert report['sum_child_wires'] == 32
    rejected = construct_preconditioned_d3_packing([(0, 0)], a=1)
    assert rejected['status'] == 'INCONCLUSIVE_D3_PRECONDITIONS'
    assert 'packing' not in rejected


def test_corruption_and_budgets_fail_closed():
    packing = construct_implicit_packing([(0, 0), (0, 1)], r=2, a=1)
    assert not check_implicit_packing(replace(packing, H=packing.H+2))['valid']
    assert not check_implicit_packing(replace(packing, classes=MappingProxyType({})))['valid']
    assert check_implicit_packing(packing, max_work=0)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    with pytest.raises(ValueError):
        packing.packet(((0, 1),), -1)
    with pytest.raises(ValueError):
        packing.packet(((0, 1),), 0, max_slots=1)
    with pytest.raises(ValueError):
        packing.packet_slot(((0, 1),), 0, packing.L)


def test_bounded_implicit_certificate_drives_existing_child_engine():
    from veritas.core.cnf import CNF
    from veritas.research.tensor import from_cnf
    from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
    from veritas.research.eth_modes_v31 import make_jet_tile_modes
    from veritas.research.eth_child_elimination_v38 import construct_elimination_reference

    network = from_cnf(CNF.from_lists(2, [[1, 2]]))
    implicit = construct_implicit_packing(make_bipartite_edges(network), r=2, a=1)
    cert = materialize_finite_certificate(implicit)
    modes = make_jet_tile_modes(cert, node=1, precision=5, jet_length=2)
    result = construct_elimination_reference(network, modes, compare_v37=True)
    assert result['exact_direct_reference_matches']
    assert result['v37_cross_check_performed']
    assert result['result'] == [[0, 0, 0], [16, 0, 0]]
    assert not result['subexponential_runtime_proven']


def test_implicit_packets_feed_mode_generator_without_explicit_bridge():
    from veritas.core.cnf import CNF
    from veritas.research.tensor import from_cnf
    from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
    from veritas.research.eth_modes_v31 import (
        make_jet_tile_modes, check_jet_tile_modes, contract_mode_children,
        check_mode_child_certificate,
    )
    from veritas.research.eth_packet_tensors_v36 import (
        construct_packet_tensor_certificate, check_packet_tensor_certificate,
    )

    network = from_cnf(CNF.from_lists(2, [[1, 2]]))
    edges = make_bipartite_edges(network)
    implicit = construct_implicit_packing(edges, r=2, a=1)
    sparse_source = implicit_mode_source(implicit)
    assert check_implicit_mode_source(sparse_source)['valid']
    sparse_modes = make_jet_tile_modes(sparse_source, node=1, precision=5, jet_length=2)
    assert check_jet_tile_modes(sparse_modes)['valid']
    sparse_child = contract_mode_children(network, sparse_modes)
    assert sparse_child['direct_oracle_matches']
    assert check_mode_child_certificate(sparse_child)['valid']
    sparse_tensors = construct_packet_tensor_certificate(network, sparse_modes)
    assert check_packet_tensor_certificate(sparse_tensors)['valid']

    # Differential reference: compare all mode data after translating packet
    # identifiers from the sparse occupied-packet order to explicit IDs.
    explicit = construct_d3_packing(edges, r=2, a=1)
    explicit_ids = {}
    next_index = {}
    for pid, packet in enumerate(explicit['packets']):
        key_pairs = tuple(tuple(pair) for pair in packet['symbol_pairs'])
        index = next_index.get(key_pairs, 0)
        explicit_ids[(key_pairs, index)] = pid
        next_index[key_pairs] = index + 1
    sparse_keys = [
        (tuple(tuple(pair) for pair in packet['symbol_pairs']), packet['index'])
        for packet in sparse_source['packets']
    ]
    explicit_modes = make_jet_tile_modes(explicit, node=1, precision=5, jet_length=2)
    explicit_child = contract_mode_children(network, explicit_modes)
    assert explicit_child['result'] == sparse_child['result']
    explicit_tensors = construct_packet_tensor_certificate(network, explicit_modes)
    assert explicit_tensors['result'] == sparse_tensors['result']

    def normalize(cert, key_by_pid):
        modes = []
        for mode in cert['modes']:
            item = dict(mode)
            item['packet'] = key_by_pid[item['packet']]
            modes.append(item)
        return (cert['local'], cert['cross_pairs'], modes,
                cert['fully_vanishing_modes'], cert['mode_tuple_count'])

    assert normalize(sparse_modes, sparse_keys) == normalize(
        explicit_modes, [next(key for key, value in explicit_ids.items() if value == pid)
                         for pid in range(len(explicit['packets']))])


def test_implicit_mode_source_rejects_tampering():
    from copy import deepcopy

    packing = construct_implicit_packing([(0, 0), (0, 1), (1, 1)], r=2, a=1)
    source = implicit_mode_source(packing)
    assert check_implicit_mode_source(source)['valid']
    for mutate in (
        lambda x: x['row_labels'].__setitem__('0', [1]),
        lambda x: x['packets'][0]['slots'].__setitem__(0, 99),
        lambda x: x['conditional_expectation_trace'][0].__setitem__(0, 'forged'),
        lambda x: x.__setitem__('H_pad', x['H_pad'] + 2),
    ):
        corrupt = deepcopy(source)
        mutate(corrupt)
        assert not check_implicit_mode_source(corrupt)['valid']


def test_materialization_rejects_tampered_trace_and_slot_budget():
    packing = construct_implicit_packing([(0, 0), (1, 1)], r=2, a=1)
    forged = replace(packing, initial_score=packing.initial_score+1)
    with pytest.raises(ValueError, match='verification failed'):
        materialize_finite_certificate(forged)
    with pytest.raises(ValueError, match='budget'):
        materialize_finite_certificate(packing, max_packets=0)
