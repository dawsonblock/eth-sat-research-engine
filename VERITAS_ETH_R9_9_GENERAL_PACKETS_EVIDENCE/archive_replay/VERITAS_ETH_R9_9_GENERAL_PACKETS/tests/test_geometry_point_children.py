from copy import deepcopy
from random import Random

import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_packing_v26.geometry_audit import audit_sparse_packet_geometry
from veritas.research.eth_packing_v26.implicit import SPARSE_MODE_SCHEMA, check_implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.geometry_point import (
    make_geometry_point_modes, check_geometry_point_modes,
    build_geometry_point_children, contract_geometry_point_expansion,
    direct_geometry_tuple_contribution, certify_geometry_point_matching_zero,
    replay_geometry_point_matching_zero,
)
from veritas.research.eth_recursive_contraction_v39.lazy_children import ChildEvaluationBudgetExceeded
from veritas.research.eth_recursive_contraction_v39.point_modes import check_point_modes, make_point_modes
from veritas.research.tensor import Factor, TensorNetwork, from_cnf


def source_and_parent():
    source = {
        'schema': SPARSE_MODE_SCHEMA, 'claim': 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS',
        'r': 2, 'a': 1, 'L': 2, 'D': 4, 'M': 2, 'H_pad': 2,
        'edges': [[0, 0], [1, 1]], 'row_labels': {'0': [0], '1': [1]},
        'column_labels': {'0': [1], '1': [0]},
        'packets': [{'symbol_pairs': [[0, 1]], 'index': 0,
                     'occupied_slots': [[0, 0], [1, 1]]}],
    }
    parent = describe_integer_network(from_cnf(CNF.from_lists(2, [[1], [2]])),
                                      creation_precision=5,
                                      defining_polynomial=first_irreducible(2))
    return source, parent


def test_noncanonical_geometry_modes_and_children_match_direct_oracle():
    source, parent = source_and_parent()
    assert audit_sparse_packet_geometry(source)['valid']
    assert not check_implicit_mode_source(source)['valid']
    with pytest.raises(ValueError):
        make_point_modes(source, node=1, precision=5, extension_degree=2)
    certificate = make_geometry_point_modes(source, node=1, precision=5, extension_degree=2,
                                            zeta=(0, 1))
    assert certificate['modes']
    assert check_geometry_point_modes(certificate)['valid']
    assert not check_point_modes(certificate)['valid']
    children = build_geometry_point_children(parent, certificate, (0,) * len(certificate['modes']))
    assert sum(child.network.edges for child in children) == 2 * parent.edges
    result = contract_geometry_point_expansion(parent, certificate)
    assert result['direct_oracle_matches'] and result['result'] == result['direct_oracle_result']
    assert not result['deterministic_trace_verified']
    assert not result['uniform_complexity_proven']


def test_geometry_snapshot_and_tampering_are_fail_closed():
    source, parent = source_and_parent()
    cert = make_geometry_point_modes(source, node=1, precision=5, extension_degree=2, zeta=(0, 1))
    source['row_labels']['0'][0] = 1
    assert check_geometry_point_modes(cert)['valid']
    forged = deepcopy(cert)
    forged['d3_certificate']['packets'][0]['occupied_slots'][0][0] = 1
    assert not check_geometry_point_modes(forged)['valid']
    with pytest.raises(ValueError):
        build_geometry_point_children(parent, forged, (0,) * len(forged['modes']))
    altered = deepcopy(cert)
    altered['modes'][0]['weight'] += 1
    assert not check_geometry_point_modes(altered)['valid']


def test_geometry_budgets_and_parent_mismatch_do_not_produce_values():
    source, parent = source_and_parent()
    with pytest.raises(ModeBudgetExceeded):
        make_geometry_point_modes(source, max_geometry_work=1)
    cert = make_geometry_point_modes(source, node=1, precision=5, extension_degree=2, zeta=(0, 1))
    assert check_geometry_point_modes(cert, max_geometry_work=1)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    with pytest.raises(ChildEvaluationBudgetExceeded):
        contract_geometry_point_expansion(parent, cert, max_work=1)
    bad_parent = describe_integer_network(from_cnf(CNF.from_lists(1, [[1]])),
                                          creation_precision=5, defining_polynomial=first_irreducible(2))
    with pytest.raises(ValueError):
        build_geometry_point_children(bad_parent, cert, (0,) * len(cert['modes']))


def test_signed_tensor_examples_match_independent_half_edge_oracle():
    source, _ = source_and_parent()
    rng = Random(20261102)
    for trial in range(12):
        factors = tuple(Factor((edge,), tuple(rng.randrange(-3, 4) for _ in range(2)),
                               f'{side}:{edge}')
                        for side in ('row', 'col') for edge in range(2))
        parent = describe_integer_network(TensorNetwork(2, factors), creation_precision=5,
                                          defining_polynomial=first_irreducible(2))
        point = (rng.randrange(32), rng.randrange(32))
        certificate = make_geometry_point_modes(source, node=(-1 if trial % 2 else 1),
                                                precision=5, extension_degree=2, zeta=point)
        result = contract_geometry_point_expansion(parent, certificate)
        assert result['result'] == result['direct_oracle_result']
        assert result['direct_oracle_matches']


def test_noncanonical_L8_hall_zero_and_complete_point_expansion(monkeypatch):
    # Both demanded modes touch only row 1 despite the group having two rows.
    source = {
        'schema': SPARSE_MODE_SCHEMA, 'claim': 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS',
        'r': 2, 'a': 3, 'L': 8, 'D': 64, 'M': 2, 'H_pad': 8,
        'edges': [[0, 0], [1, 1]], 'row_labels': {'0': [1, 0, 0], '1': [0, 0, 1]},
        'column_labels': {'0': [0, 1, 1], '1': [1, 1, 0]},
        'packets': [{'symbol_pairs': [[0, 1], [0, 1], [0, 1]], 'index': 0,
                     'occupied_slots': [[1, 0], [4, 1]]}],
    }
    parent = describe_integer_network(from_cnf(CNF.from_lists(2, [[1], [2]])),
                                      creation_precision=8, defining_polynomial=first_irreducible(2))
    cert = make_geometry_point_modes(source, node=2, precision=8, extension_degree=2, zeta=(1, 0))
    beta = (0, 0, 1, 1, 0, 0)
    assert len(cert['modes']) == 6
    hall = certify_geometry_point_matching_zero(cert, beta)
    assert hall['status'] == 'FINITE_STRUCTURAL_ZERO_CERTIFIED'
    assert hall['support_provenance_verified'] and not hall['deterministic_trace_verified']
    assert replay_geometry_point_matching_zero(cert, hall['certificate'])['valid']
    tampered = deepcopy(hall['certificate'])
    tampered['witness']['row_ids'] = []
    assert not replay_geometry_point_matching_zero(cert, tampered)['valid']
    direct = direct_geometry_tuple_contribution(parent, cert, beta)
    assert direct['result'] == ((0, 0),)
    full = contract_geometry_point_expansion(parent, cert, max_work=1_000_000, timeout_s=20)
    assert full['direct_oracle_matches']
    assert next(row['term'] for row in full['tuples'] if row['beta'] == beta) == direct['result']
    assert 'hall_pruned_tuples' not in full
    pruned = contract_geometry_point_expansion(parent, cert, max_work=1_000_000, timeout_s=20,
                                               enable_hall_pruning=True)
    assert pruned['result'] == full['result'] == pruned['direct_oracle_result']
    row = next(row for row in pruned['tuples'] if row['beta'] == beta)
    assert row['structurally_zero'] and not row['children'] and row['term'] == direct['result']
    assert row['hall_witness']['demand'] > row['hall_witness']['available_rows']
    assert pruned['hall_pruned_tuples'] >= 1 and pruned['hall_work_units'] > 0
    assert pruned['hall_work_units'] <= pruned['algorithm_work_units']
    with pytest.raises(ChildEvaluationBudgetExceeded):
        contract_geometry_point_expansion(parent, cert, max_work=1, enable_hall_pruning=True)
    from veritas.research.eth_recursive_contraction_v39 import point_children
    def fail_witness(*_args):
        raise ValueError('injected invalid witness')
    monkeypatch.setattr(point_children, '_verify_hall_witness', fail_witness)
    with pytest.raises(ValueError, match='injected invalid witness'):
        contract_geometry_point_expansion(parent, cert, max_work=1_000_000,
                                          enable_hall_pruning=True)
