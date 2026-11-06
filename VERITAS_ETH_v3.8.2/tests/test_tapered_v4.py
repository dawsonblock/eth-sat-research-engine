from copy import deepcopy
from itertools import product
import json
from random import Random

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork, from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_mode_source,
)
from veritas.research.tapered_v4 import (
    RecursionPolicy, TaperedState, contract_recursive, replay_certificate, inspect_finite_schedule,
    build_finite_child_size_certificate, check_finite_child_size_certificate,
)


def state_for_cnf(n, clauses, *, degree=5, precision=None):
    p = n + 1 if precision is None else precision
    f = first_irreducible(degree)
    network = describe_integer_network(from_cnf(CNF.from_lists(n, clauses)),
                                       creation_precision=p, defining_polynomial=f)
    return TaperedState(network, 0, p, f, 1, network.edges)


@pytest.mark.parametrize('n,clauses,count', [
    (0, [], 1), (0, [[]], 0), (3, [], 8), (3, [[]], 0),
])
def test_zero_wire_formula_semantics(n, clauses, count):
    state = state_for_cnf(n, clauses)
    result = contract_recursive(state, RecursionPolicy())
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((count, 0, 0, 0, 0),)
    assert result['ledger']['maximum_depth'] == 0
    assert result['ledger']['counters']['algorithm_leaf_calls'] == 1


@pytest.mark.parametrize('wires', [8, 10, 12, 14, 16])
def test_bounded_eight_to_sixteen_wire_direct_leaf(wires):
    # Four dense factors over two disjoint halves force every wire to one.
    # The independent count is exactly one, without using the leaf algorithm.
    mid = wires // 2
    factors = []
    for side in ('row', 'col'):
        for index, ports in enumerate((tuple(range(mid)), tuple(range(mid, wires)))):
            table = (0,) * ((1 << len(ports)) - 1) + (1,)
            factors.append(Factor(ports, table, f'{side}:{index}'))
    f = first_irreducible(1)
    network = describe_integer_network(TensorNetwork(wires, tuple(factors)),
                                       creation_precision=2, defining_polynomial=f)
    state = TaperedState(network, 0, 2, f, 1, wires)
    result = contract_recursive(state, RecursionPolicy(leaf_edge_limit=16))
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((1,),)
    assert result['ledger']['counters']['algorithm_leaf_calls'] == 1
    assert result['ledger']['counters'].get('point_evaluations', 0) == 0
    assert not result['subexponential_runtime_proven']


@pytest.mark.parametrize('wires', [8, 10, 12, 14, 16])
def test_seeded_eight_to_sixteen_wire_cnf_matches_independent_assignments(wires):
    rng = Random(20261101 + wires)
    n = 5
    remaining = wires
    clauses = []
    while remaining:
        width = min(3, remaining)
        clauses.append([rng.choice((-1, 1)) * rng.randrange(1, n + 1)
                        for _ in range(width)])
        remaining -= width
    expected = sum(all(any(values[abs(literal)-1] if literal > 0 else not values[abs(literal)-1]
                           for literal in clause) for clause in clauses)
                   for values in product((False, True), repeat=n))
    state = state_for_cnf(n, clauses, degree=1)
    assert state.network.edges == wires
    result = contract_recursive(state, RecursionPolicy(leaf_edge_limit=16))
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((expected,),)


def test_two_level_hybrid_recursion_uses_required_point_oracle(monkeypatch):
    from veritas.research.eth_recursive_contraction_v39 import point_children

    original = point_children._direct_point_oracle
    calls = []
    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(point_children, '_direct_point_oracle', observed)
    state = state_for_cnf(2, [[1, 2]])
    policy = RecursionPolicy(max_depth=8, allow_nonshrinking_leaf=True,
                             max_certificate_bytes=8_000_000)
    result = contract_recursive(state, policy)
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((3, 0, 0, 0, 0),)
    assert result['ledger']['maximum_depth'] >= 2
    assert result['ledger']['maximum_child_edges'] >= state.network.edges
    assert result['ledger']['counters']['nonshrinking_children'] > 0
    assert calls and result['ledger']['counters']['oracle_point_checks'] > 0
    assert result['ledger']['counters'].get('oracle_leaf_work', 0) == 0
    assert result['ledger']['counters']['packing_work'] > 0
    assert not result['ledger']['complete']
    assert result['ledger']['accumulator_operand_bits'] > 0
    assert result['ledger']['counters']['finite_multiplicity_checks'] > 0
    assert any(event['payload'].get('reason') == 'NONSHRINKING_FINITE_FALLBACK'
               for event in result['certificate']['events'])


def test_reference_oracle_is_explicit_and_separately_charged():
    state = state_for_cnf(1, [[1]], degree=3)
    policy = RecursionPolicy(allow_nonshrinking_leaf=True, verify_small_nodes=True)
    result = contract_recursive(state, policy)
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['ledger']['counters']['oracle_leaf_calls'] > 0
    assert result['ledger']['counters']['oracle_leaf_work'] > 0
    assert result['independent_oracle_enabled']


def test_recursive_nonconstant_extension_jets_match_direct_ring_sum():
    from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
    from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
    from veritas.research.eth_arithmetic.jets import JetRing
    from veritas.research.eth_recursive_contraction_v39.described_network import (
        CreatedDenseTensor, DescribedNetwork, DescribedVertex,
    )
    f = first_irreducible(3)
    ring = JetRing(ExtensionRing(2, f), 2)
    left = (ring.elem([[1, 1], [2]]), ring.elem([[3], [1, 1]]))
    right = (ring.elem([[2, 1], [1]]), ring.elem([[1, 0, 1], [3]]))
    def tensor(entries):
        return CreatedDenseTensor(1, tuple(CreationJetEntry.capture(ring, value)
                                           for value in entries))
    network = DescribedNetwork(1, (DescribedVertex('row', 'row', (0,), tensor(left)),
                                    DescribedVertex('column', 'column', (0,), tensor(right))))
    state = TaperedState(network, 0, 2, f, 2, 1)
    expected = ring.add(ring.mul(left[0], right[0]), ring.mul(left[1], right[1]))
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True,
                                                       verify_small_nodes=True))
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == expected
    assert result['ledger']['counters']['oracle_leaf_work'] > 0


def test_transcript_round_trip_and_tampering():
    state = state_for_cnf(1, [[1]], degree=3)
    policy = RecursionPolicy(allow_nonshrinking_leaf=True)
    result = contract_recursive(state, policy)
    encoded = json.dumps(result['certificate'], sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
    assert len(encoded) == result['ledger']['serialized_certificate_bytes']
    assert len(encoded) <= policy.max_certificate_bytes
    cert = json.loads(json.dumps(result['certificate']))
    assert replay_certificate(state, policy, cert)['valid']
    for corrupt in ('result', 'event', 'hash', 'extra'):
        altered = deepcopy(cert)
        if corrupt == 'result':
            altered['result'][0][0] ^= 1
        elif corrupt == 'event':
            altered['events'][0]['payload']['edges'] += 1
        elif corrupt == 'hash':
            altered['transcript_sha256'] = '0' * 64
        else:
            altered['universal_proof'] = True
        assert not replay_certificate(state, policy, altered)['valid']


def test_fail_closed_on_depth_work_memory_and_theorem_claims():
    state = state_for_cnf(1, [[1]], degree=3)
    policies = [
        RecursionPolicy(max_depth=0),
        RecursionPolicy(max_work=1),
        RecursionPolicy(max_memory_bytes=1_000_000),
        RecursionPolicy(require_complete_accounting=True),
        RecursionPolicy(mode='theorem'),
        RecursionPolicy(require_one_eighth_shrink=True),
        RecursionPolicy(max_vertex_degree=0),
        RecursionPolicy(max_certificate_bytes=1),
    ]
    for policy in policies:
        result = contract_recursive(state, policy)
        assert result['status'].startswith('INCONCLUSIVE_')
        assert 'result' not in result and 'certificate' not in result
    assert contract_recursive(state, RecursionPolicy(mode='theorem'))['status'] == 'INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED'
    assert contract_recursive(state, RecursionPolicy(require_one_eighth_shrink=True))['status'] == 'INCONCLUSIVE_CHILD_SIZE_INVARIANT'
    assert contract_recursive(state, RecursionPolicy(max_vertex_degree=0))['status'] == 'INCONCLUSIVE_DEGREE_INVARIANT'


def test_nonshrinking_branch_is_never_silently_recursed():
    state = state_for_cnf(1, [[1]], degree=3)
    result = contract_recursive(state, RecursionPolicy())
    assert result['status'] == 'INCONCLUSIVE_NONSHRINKING_CHILD'
    assert 'result' not in result


def test_depth_cap_is_global_across_children():
    state = state_for_cnf(2, [[1, 2]])
    policy = RecursionPolicy(max_depth=1, allow_nonshrinking_leaf=True)
    result = contract_recursive(state, policy)
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result


def test_generated_child_degree_is_checked_before_execution():
    state = state_for_cnf(2, [[1], [2]])
    assert max(len(vertex.ports) for vertex in state.network.vertices) == 1
    result = contract_recursive(state, RecursionPolicy(max_vertex_degree=1,
                                                       allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_DEGREE_INVARIANT'
    assert result['ledger']['maximum_child_degree'] > 1
    assert 'result' not in result


def test_forged_generated_modes_are_rejected_before_a_count(monkeypatch):
    from veritas.research.tapered_v4 import recursor

    original = recursor.make_point_modes

    def corrupt(*args, **kwargs):
        certificate = original(*args, **kwargs)
        if certificate['modes']:
            certificate['modes'][0]['weight'] += 1
        else:
            certificate['structural_tuple_count'] += 1
        return certificate

    monkeypatch.setattr(recursor, 'make_point_modes', corrupt)
    result = contract_recursive(state_for_cnf(2, [[1, 2]]),
                                RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'result' not in result


def test_recursive_child_partition_is_checked_before_contraction(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    original = recursor._build_point_children_checked

    def omit_child(*args, **kwargs):
        return original(*args, **kwargs)[1:]

    monkeypatch.setattr(recursor, '_build_point_children_checked', omit_child)
    result = contract_recursive(state_for_cnf(1, [[1]], degree=3),
                                RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'result' not in result


def test_invalid_creation_precision_and_inherited_polynomial_are_rejected():
    state = state_for_cnf(1, [[1]], degree=3)
    smaller = TaperedState(state.network, 0, 1, state.extension_polynomial, 1, state.root_size)
    assert contract_recursive(smaller, RecursionPolicy(leaf_edge_limit=1))['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    other = first_irreducible(2)
    changed = TaperedState(state.network, 0, 2, other, 1, state.root_size)
    assert contract_recursive(changed, RecursionPolicy(leaf_edge_limit=1))['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'


def test_forged_root_size_and_packing_assertion_fail_closed(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    state = state_for_cnf(1, [[1]], degree=3)
    forged = TaperedState(state.network, 0, state.target_precision,
                          state.extension_polynomial, state.jet_length, state.root_size + 1)
    result = contract_recursive(forged, RecursionPolicy(leaf_edge_limit=1))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'result' not in result

    def broken(*args, **kwargs):
        raise AssertionError('inconsistent packing score')

    monkeypatch.setattr(recursor, 'construct_implicit_packing', broken)
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'result' not in result


def test_extension_degree_is_capped_before_irreducibility_check(monkeypatch):
    from veritas.research.eth_arithmetic import extension_ring
    state = state_for_cnf(1, [[1]], degree=3)
    def forbidden(*args):
        raise AssertionError('irreducibility test should not run')
    monkeypatch.setattr(extension_ring, 'is_irreducible', forbidden)
    with pytest.raises(ValueError, match='extension degree'):
        TaperedState(state.network, 0, state.target_precision, (1 << 10000) | 1,
                     state.jet_length, state.root_size)

def test_packing_uses_shared_run_budget(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    state = state_for_cnf(1, [[1]], degree=3)

    def exhaust(*args, **kwargs):
        kwargs['_budget'].tick(kwargs['max_work'] + 1)
        raise AssertionError('budget should have interrupted packing')

    monkeypatch.setattr(recursor, 'construct_implicit_packing', exhaust)
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result


def test_verifier_resource_limits_propagate(monkeypatch):
    from veritas.research.eth_packing_v26 import implicit
    from veritas.research.eth_packing_v26.expectation import PackingBudgetExceeded
    from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
    from veritas.research.eth_recursive_contraction_v39 import point_modes, point_children

    def packing_limit(*args, **kwargs):
        raise PackingBudgetExceeded('packing replay limit')

    monkeypatch.setattr(implicit, 'construct_implicit_packing', packing_limit)
    source = {'schema': implicit.SPARSE_MODE_SCHEMA,
              'claim': 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS',
              'edges': [], 'r': 2, 'a': 1}
    assert implicit.check_implicit_mode_source(source)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    monkeypatch.setattr(implicit, 'check_implicit_packing',
                        lambda *args, **kwargs: {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'})
    with pytest.raises(PackingBudgetExceeded):
        implicit.sparse_active_packet_view(object())

    def mode_limit(*args, **kwargs):
        raise ModeBudgetExceeded('mode replay limit')

    monkeypatch.setattr(point_modes, '_source_check', mode_limit)
    cert = {'schema': point_modes.SCHEMA, 'claim': point_modes.CLAIM,
            'scope': point_modes.SCOPE, 'jet_length': 1,
            'd3_certificate': {}, 'node': 1, 'precision': 2,
            'extension_degree': 1, 'zeta': [0]}
    assert point_modes.check_point_modes(cert)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'

    monkeypatch.setattr(point_children, 'check_point_modes',
                        lambda *args, **kwargs: {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'})
    state = state_for_cnf(1, [[1]], degree=3)
    with pytest.raises(ModeBudgetExceeded):
        point_children._ring_for(state.network, {'schema': point_modes.SCHEMA})


def test_small_extension_or_precision_cap_fails_without_a_count():
    state = state_for_cnf(2, [[1, 2]], degree=1)
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result
    state = state_for_cnf(1, [[1]], degree=3)
    result = contract_recursive(state, RecursionPolicy(max_precision_bits=4, allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result
    oversized = TaperedState(state.network, 0, 1025, state.extension_polynomial, 1, state.root_size)
    result = contract_recursive(oversized, RecursionPolicy(leaf_edge_limit=1))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result
    result = contract_recursive(state, RecursionPolicy(leaf_edge_limit=1, max_extension_degree=2))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result


def test_eight_wire_mode_adapter_requires_explicit_limit_and_replays():
    from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
    from veritas.research.eth_recursive_contraction_v39 import make_point_modes, check_point_modes
    from veritas.research.eth_recursive_contraction_v39 import audit_point_mode_multiplicity

    state = state_for_cnf(8, [[i] for i in range(1, 9)])
    source = implicit_mode_source(construct_implicit_packing(state.network.bipartite_edges(), r=4, a=1))
    with pytest.raises(ValueError, match='parameter limit'):
        make_point_modes(source, node=1, precision=5, extension_degree=5)
    certificate = make_point_modes(source, node=1, precision=10, extension_degree=5,
                                   zeta=(1, 0, 0, 0, 0), max_parent_wires=8)
    assert check_point_modes(certificate, max_parent_wires=8)['valid']
    from veritas.research.eth_recursive_contraction_v39.point_children import build_point_children
    children = build_point_children(state.network, certificate,
                                    (0,) * len(certificate['modes']), max_parent_wires=8)
    assert sum(child.network.edges for child in children) == 16
    assert not check_point_modes(certificate)['valid']
    audit = audit_point_mode_multiplicity(certificate, max_parent_wires=8)
    assert audit['status'] in ('FINITE_MULTIPLICITY_BOUND_CHECKED', 'MULTIPLICITY_HYPOTHESIS_NOT_MET')
    forged = deepcopy(certificate)
    forged['structural_tuple_count'] += 1
    assert not check_point_modes(forged, max_parent_wires=8)['valid']


def test_eight_wire_tapered_step_matches_an_independent_node_oracle():
    # Every declared variable is forced true, so the independent count is 1.
    state = state_for_cnf(8, [[i] for i in range(1, 9)])
    policy = RecursionPolicy(max_active_wires=8, leaf_edge_limit=7,
                             finite_parameters=(1, 1, 4), max_depth=4,
                             max_certificate_bytes=30_000_000,
                             verify_small_nodes=True, oracle_edge_limit=8,
                             max_seconds=120, max_work=4_000_000)
    result = contract_recursive(state, policy)
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((1, 0, 0, 0, 0),)
    assert result['ledger']['counters']['point_evaluations'] > 0
    assert result['ledger']['maximum_child_edges'] < 8
    assert result['ledger']['counters'].get('nonshrinking_children', 0) == 0
    assert result['ledger']['counters']['oracle_leaf_work'] > 0
    assert not result['subexponential_runtime_proven']
    assert replay_certificate(state, policy, result['certificate'])['valid']
    strict = contract_recursive(state, RecursionPolicy(max_active_wires=8, leaf_edge_limit=7,
                                                        finite_parameters=(1, 1, 4),
                                                        require_one_eighth_shrink=True,
                                                        max_seconds=120))
    assert strict['status'] == 'INCONCLUSIVE_CHILD_SIZE_INVARIANT'
    assert 'result' not in strict


def test_finite_child_audit_accounts_for_all_half_wires_and_rejects_theorem_claims():
    state = state_for_cnf(8, [[i] for i in range(1, 9)])
    packing = construct_implicit_packing(state.network.bipartite_edges(), r=4, a=1)
    source = implicit_mode_source(packing)
    mode_certificate = make_point_modes(
        source, node=-1, precision=521, extension_degree=5,
        zeta=(0, 0, 0, 0, 0), max_parent_wires=8)

    audit = build_finite_child_size_certificate(state.network, mode_certificate, ())
    assert audit['parent_edges'] == 8
    assert audit['child_edges'] == 6
    assert audit['shrink_ratio'] == {'numerator': 3, 'denominator': 4, 'decimal': 0.75}
    assert audit['target_ratio'] == {'numerator': 1, 'denominator': 8, 'relation': '<'}
    assert audit['theorem_target_ratio'] == {'numerator': 3, 'denominator': 32,
                                             'relation': '<='}
    assert audit['sum_child_edges'] == audit['expected_sum_child_edges'] == 16
    assert audit['all_parent_half_edges_partitioned_once']
    assert audit['introduced_boolean_wire_edges'] == 0
    assert audit['introduced_packet_factor_ports'] == audit['sum_child_edges']
    witness = next(row for row in audit['children'] if row['group'] == 0)
    assert (witness['row_half_edge_count'], witness['column_half_edge_count']) == (4, 2)
    assert len(witness['inherited_port_map']) == 6
    assert len(witness['packet_port_map']) == 6
    assert audit['coordinate_symbol_loads']['all_sides_meet_per_side_bound']
    hypotheses = audit['finite_hypothesis_arithmetic']
    assert hypotheses['D'] == 16 and hypotheses['H'] == 2 and hypotheses['delta'] == 1
    assert hypotheses['M_at_least_2_D_squared_delta'] == {
        'left': 8, 'right': 512, 'holds': False}
    assert hypotheses['M_at_least_L_D'] == {'left': 8, 'right': 32, 'holds': False}
    assert hypotheses['2_L_at_most_delta'] == {'left': 4, 'right': 1, 'holds': False}
    assert hypotheses['D_H_at_most_3_M'] == {'left': 32, 'right': 24, 'holds': False}
    assert not hypotheses['all_reported_conditions_hold']
    assert audit['all_children_meet_finite_six_M_over_r']
    assert not audit['all_children_meet_strict_one_eighth']
    assert not audit['all_children_meet_three_over_32']
    assert audit['finite_packing_checks']['symbol_port_bound']
    assert not audit['finite_packing_checks']['d3_numeric_preconditions']
    assert not audit['theorem_premises_verified']
    assert not audit['uniform_shrink_verified']
    assert audit['result'] == 'FINITE_EXPERIMENT_ONLY'
    assert check_finite_child_size_certificate(
        state.network, mode_certificate, (), audit)['valid']

    altered = deepcopy(audit)
    altered['children'][0]['child_edges'] += 1
    assert not check_finite_child_size_certificate(
        state.network, mode_certificate, (), altered)['valid']
    altered = deepcopy(audit)
    altered['children'][0]['inherited_port_map'][0]['parent_vertex_index'] += 1
    assert not check_finite_child_size_certificate(
        state.network, mode_certificate, (), altered)['valid']
    altered = deepcopy(audit)
    altered['children'][0]['packet_port_map'][0]['child_wire_port'] += 1
    assert not check_finite_child_size_certificate(
        state.network, mode_certificate, (), altered)['valid']
    altered = deepcopy(audit)
    altered['theorem_premises_verified'] = True
    assert not check_finite_child_size_certificate(
        state.network, mode_certificate, (), altered)['valid']


@pytest.mark.parametrize('wires,points,degree', [(8,25,5), (10,31,5),
                                                  (12,37,6), (14,43,6), (16,49,6)])
def test_schedule_preflight_counts_points_and_extension_degree(wires, points, degree):
    report = inspect_finite_schedule(wires, 1, 1, wires + 1)
    assert report['degree_bound'] == 3 * wires
    assert report['interpolation_points'] == points
    assert report['minimum_extension_degree'] == degree
    assert not report['theorem_schedule_verified']


def test_sixteen_wire_precision_is_reported_without_truncation():
    report = inspect_finite_schedule(16, 1, 1, 17, max_precision_bits=1024)
    assert report['maximum_required_precision_bits'] == 17 + 1024
    assert not report['precision_within_cap']
