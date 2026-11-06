from dataclasses import replace
from itertools import product
from random import Random

import pytest

from veritas.core.cnf import CNF
from veritas.research.source_cnf import source_cnf_network
from veritas.research.source_cnf_check import check_source_cnf_network
from veritas.research.tensor import Factor, TensorNetwork, brute_contract
from veritas.research.minfill_contract import minfill_contract
from veritas.research.math_exact import exhaustive_count
from veritas.research.tapered_v4 import RecursionPolicy, count_source_cnf_finite


def test_exhaustive_small_formulas_encoding_and_model_count():
    literals = (-2, -1, 1, 2)
    clauses = [()] + [(x,) for x in literals] + list(product(literals, repeat=2))
    for chosen in [()] + [(x,) for x in clauses] + list(product(clauses, repeat=2)):
        cnf = CNF(2, chosen)
        source = source_cnf_network(cnf)
        assert check_source_cnf_network(cnf, source)['valid']
        assert brute_contract(source.network, max_edges=16) * 2**len(source.unused_variables) == exhaustive_count(cnf)


def test_random_formulas_tree_structure_and_counts():
    rng = Random(20261102)
    for _ in range(180):
        n = rng.randrange(1, 6)
        clauses = [[rng.choice((-1, 1))*rng.randrange(1, n+1)
                    for _ in range(rng.randrange(4))]
                   for _ in range(rng.randrange(8))]
        cnf = CNF.from_lists(n, clauses)
        encoded = source_cnf_network(cnf, max_wires=200)
        assert check_source_cnf_network(cnf, encoded)['valid']
        count, _ = minfill_contract(encoded.network, max_table_entries=4096)
        assert count * (1 << len(encoded.unused_variables)) == exhaustive_count(cnf)
        assert max((len(f.ports) for f in encoded.network.factors), default=0) <= 3
        assert encoded.network.edges == 2*encoded.original_edges


def test_normalization_tree_and_negative_graph_tampering():
    cnf = CNF.from_lists(4, [[1, 1], [2, -2], [1], [1], [1], [1], [-3]])
    encoded = source_cnf_network(cnf)
    assert encoded.dropped_tautologies == (1,)
    assert encoded.unused_variables == (2, 4)
    assert encoded.normalized_cnf.clauses[0] == (1,)
    assert check_source_cnf_network(cnf, encoded)['valid']
    damaged = list(encoded.network.factors)
    col = next(i for i, f in enumerate(damaged) if f.label.startswith('col:'))
    f = damaged[col]
    damaged[col] = Factor(f.ports, (1, 1, 1, 1), f.label)
    forged = replace(encoded, network=TensorNetwork(encoded.network.edges, damaged))
    assert not check_source_cnf_network(cnf, forged)['valid']
    assert not check_source_cnf_network(cnf, replace(encoded, unused_variables=()))['valid']
    assert not check_source_cnf_network(CNF.from_lists(4, [[1]]), encoded)['valid']
    assert check_source_cnf_network(cnf, encoded, max_wires=0)['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    with pytest.raises(ValueError): source_cnf_network(cnf, max_wires=2)
    with pytest.raises(ValueError): source_cnf_network(cnf, max_factors=1)


@pytest.mark.parametrize('n,clauses,expected', [
    (2, [[1]], 2), (2, [[1, 2]], 3), (2, [[1], [-1]], 0),
    (3, [[1, -1]], 8), (2, [[]], 0), (0, [], 1),
])
def test_source_encoding_runs_finite_recursion_and_checks_oracle(n, clauses, expected):
    policy = RecursionPolicy(leaf_edge_limit=1, allow_nonshrinking_leaf=True,
                             verify_small_nodes=True)
    got = count_source_cnf_finite(CNF.from_lists(n, clauses), policy, verify_exhaustive=True)
    assert got['status'] == 'EXACT_COUNT_FINITE'
    assert got['count'] == expected
    assert got['independent_structure_checked'] and got['independent_exhaustive_oracle_used']
    assert got['subexponential_runtime_proven'] is False
    if got['network_edges'] > 1:
        assert got['ledger']['maximum_depth'] >= 1
        assert got['ledger']['counters']['nonshrinking_children'] > 0


def test_strict_recursion_fails_closed_and_oracle_tampering_detected(monkeypatch):
    cnf = CNF.from_lists(1, [[1]])
    strict = count_source_cnf_finite(cnf, RecursionPolicy(leaf_edge_limit=1))
    assert strict['status'] == 'INCONCLUSIVE_NONSHRINKING_CHILD'
    assert 'count' not in strict
    theorem = count_source_cnf_finite(cnf, RecursionPolicy(mode='theorem'))
    assert theorem['status'] == 'INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED'
    assert 'count' not in theorem
    cap = count_source_cnf_finite(cnf, RecursionPolicy(), verify_exhaustive=True, oracle_max_work=1)
    assert cap['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in cap
    import veritas.research.tapered_v4.cnf_count as module
    monkeypatch.setattr(module, 'exhaustive_count', lambda *a, **kw: 0)
    bad = count_source_cnf_finite(cnf, RecursionPolicy(leaf_edge_limit=2), verify_exhaustive=True)
    assert bad['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE' and 'count' not in bad


def test_every_active_point_checked_against_half_edge_sum(monkeypatch):
    from veritas.research.eth_recursive_contraction_v39 import point_children
    cnf = CNF.from_lists(1, [[1]])
    policy = RecursionPolicy(leaf_edge_limit=1, allow_nonshrinking_leaf=True,
                             verify_point_identities=True)
    result = count_source_cnf_finite(cnf, policy, extension_degree=3, verify_exhaustive=True)
    assert result['status'] == 'EXACT_COUNT_FINITE' and result['count'] == 1
    assert result['ledger']['counters']['oracle_point_checks'] == result['ledger']['counters']['point_evaluations']
    assert result['ledger']['counters']['oracle_point_work'] > 0
    assert any(event['payload']['kind'] == 'point_identity_checked'
               for event in result['certificate']['events'])
    original = point_children._direct_point_oracle
    def corrupt(parent, source, node, zeta, ring, budget):
        return ring.add(original(parent, source, node, zeta, ring, budget), ring.one)
    monkeypatch.setattr(point_children, '_direct_point_oracle', corrupt)
    bad = count_source_cnf_finite(cnf, policy, extension_degree=3)
    assert bad['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE' and 'count' not in bad
    assert 'point oracle disagrees' in bad['reason']


def test_point_oracle_cap_and_budget_fail_closed():
    cnf = CNF.from_lists(2, [[1, 2]])
    policy = RecursionPolicy(leaf_edge_limit=1, allow_nonshrinking_leaf=True,
                             verify_point_identities=True, point_oracle_edge_limit=2)
    got = count_source_cnf_finite(cnf, policy)
    assert got['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in got
    assert 'point identity oracle edge cap' in got['reason']
    cnf = CNF.from_lists(1, [[1]])
    policy = RecursionPolicy(leaf_edge_limit=1, allow_nonshrinking_leaf=True,
                             verify_point_identities=True, max_work=1)
    got = count_source_cnf_finite(cnf, policy)
    assert got['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and 'count' not in got


def test_structure_checker_rejects_cross_variable_rewiring():
    cnf = CNF.from_lists(2, [[1], [2]])
    encoded = source_cnf_network(cnf)
    factors = list(encoded.network.factors)
    first = next(i for i, f in enumerate(factors) if f.label == 'row:clause:0')
    second = next(i for i, f in enumerate(factors) if f.label == 'row:clause:1')
    a, b = factors[first], factors[second]
    factors[first] = Factor(b.ports, a.table, a.label)
    factors[second] = Factor(a.ports, b.table, b.label)
    forged = replace(encoded, network=TensorNetwork(encoded.network.edges, factors))
    assert check_source_cnf_network(cnf, forged)['status'] == 'INVALID_SOURCE_CNF_NETWORK'


def test_active_packing_lower_bound_rules_out_explicit_graph_cap():
    from veritas.research.tapered_v4.parameters import inspect_active_theorem_capacity
    minimum = 2 * (64**4)**2 * 8
    assert minimum == 2**52
    assert inspect_active_theorem_capacity(64)['status'] == 'ACTIVE_CALL_IMPOSSIBLE_AT_CAP'
    assert inspect_active_theorem_capacity(minimum-1)['status'] == 'ACTIVE_CALL_IMPOSSIBLE_AT_CAP'
    at_boundary = inspect_active_theorem_capacity(minimum)
    assert at_boundary['status'] == 'ACTIVE_CALL_NOT_RULED_OUT_BY_THIS_BOUND'
    assert not at_boundary['theorem_path_implemented']
    with pytest.raises(ValueError): inspect_active_theorem_capacity(True)


def test_four_wire_recursion_checks_all_points_and_certificate_replay():
    from copy import deepcopy
    from veritas.research.eth_arithmetic.gf2 import first_irreducible
    from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
    from veritas.research.tapered_v4 import TaperedState, replay_certificate
    cnf = CNF.from_lists(2, [[1, 2]])
    policy = RecursionPolicy(leaf_edge_limit=1, allow_nonshrinking_leaf=True,
                             verify_point_identities=True, point_oracle_edge_limit=4)
    result = count_source_cnf_finite(cnf, policy, extension_degree=5, verify_exhaustive=True)
    assert result['status'] == 'EXACT_COUNT_FINITE' and result['count'] == 3
    assert result['point_identities_checked'] == 26
    assert result['ledger']['counters']['nonshrinking_children'] > 0
    encoded = source_cnf_network(cnf)
    poly = first_irreducible(5)
    network = describe_integer_network(encoded.network, creation_precision=3, defining_polynomial=poly)
    state = TaperedState(network, 0, 3, poly, 1, network.edges)
    assert replay_certificate(state, policy, result['certificate'])['valid']
    damaged = deepcopy(result['certificate'])
    event = next(e for e in damaged['events'] if e['payload']['kind'] == 'point_identity_checked')
    event['payload']['point_index'] += 1
    assert not replay_certificate(state, policy, damaged)['valid']
