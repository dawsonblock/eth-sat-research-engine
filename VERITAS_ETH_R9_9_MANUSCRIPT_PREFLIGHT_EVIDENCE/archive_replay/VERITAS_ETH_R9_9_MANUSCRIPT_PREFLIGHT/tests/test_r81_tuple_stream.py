"""Independent completeness checks for the finite weighted tuple stream."""
from itertools import product
from random import Random

import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples
from veritas.research.eth_recursive_contraction_v39.tuple_stream_check import (
    TupleStreamVerifier, independently_valid_tuple, independent_weighted_tuple_count, tuple_constraints,
)
from veritas.research.tensor import from_cnf
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState, contract_recursive


def mode(packet, group, weight, rows):
    return {'packet': packet, 'target_group': group, 'weight': weight,
            'rows': [[row, []] for row in rows]}


def independent_cartesian(modes, precision):
    capacities = {}
    for m in modes:
        capacities.setdefault((m['packet'], m['target_group']), set()).update(r[0] for r in m['rows'])
    out = []
    for beta in product(*(range(len(m['rows'])+1) for m in modes)):
        if sum(b*m['weight'] for b, m in zip(beta, modes)) >= precision:
            continue
        if any(sum(b for b, m in zip(beta, modes) if (m['packet'], m['target_group']) == g) > len(rows)
               for g, rows in capacities.items()):
            continue
        out.append(beta)
    return out


def test_independent_polynomial_count_matches_brute_force_for_overlapping_groups():
    rng = Random(81012026)
    for _ in range(250):
        modes = [mode(rng.randrange(3), rng.randrange(2), rng.randrange(1, 6),
                      [r for r in range(4) if rng.randrange(2)]) for _ in range(rng.randrange(6))]
        precision = rng.randrange(1, 8)
        expected = independent_cartesian(modes, precision)
        constraints = tuple_constraints(modes, precision)
        assert independent_weighted_tuple_count(constraints) == len(expected)
        assert independent_weighted_tuple_count(modes, precision) == len(expected)
        stream = list(structural_tuples(modes, precision))
        assert stream == expected
        assert all(independently_valid_tuple(beta, constraints) for beta in stream)
        assert all(independently_valid_tuple(beta, modes, precision) for beta in stream)
        verifier = TupleStreamVerifier(modes, precision)
        for beta in stream: verifier.accept(beta)
        assert verifier.finish() == len(expected)


def test_tuple_checker_rejects_duplicates_reordering_substitution_and_omission():
    modes = [mode(0, 0, 1, (0, 1)), mode(0, 0, 2, (1, 2)), mode(1, 1, 1, (4,))]
    expected = independent_cartesian(modes, 5)
    assert len(expected) > 3
    mutations = [expected[:-1] + expected[-2:-1], list(reversed(expected)),
                 expected[:-1] + [(99, 0, 0)], expected[:-1]]
    for observed in mutations:
        verifier = TupleStreamVerifier(modes, 5)
        with pytest.raises(ValueError):
            for beta in observed: verifier.accept(beta)
            verifier.finish()
    constraints = tuple_constraints(modes, 5)
    assert not independently_valid_tuple((True, 0, 0), constraints)
    assert not independently_valid_tuple((0, 0), constraints)
    assert not independently_valid_tuple((2, 2, 0), constraints)


def test_independent_count_and_state_caps_fail_closed():
    constraints = tuple_constraints([mode(0, 0, 1, (0, 1, 2))], 5)
    with pytest.raises(ModeBudgetExceeded):
        independent_weighted_tuple_count(constraints, max_tuples=1)
    with pytest.raises(ModeBudgetExceeded):
        independent_weighted_tuple_count(constraints, max_states=1)
    assert independent_weighted_tuple_count(tuple_constraints([], 1)) == 1
    with pytest.raises(ValueError): tuple_constraints([mode(0, 0, 1, (1, 1))], 3)


def state():
    f = first_irreducible(3)
    network = describe_integer_network(from_cnf(CNF.from_lists(2, [[1, 2]])),
                                       creation_precision=3, defining_polynomial=f)
    return TaperedState(network, 0, 3, f, 1, network.edges)


@pytest.mark.parametrize('mutation', ['duplicate', 'substitution', 'reverse', 'invalid', 'omit'])
@pytest.mark.parametrize('tuple_oracle', [False, True])
def test_recursor_rejects_mutated_stream_with_no_partial_result(monkeypatch, mutation, tuple_oracle):
    from veritas.research.tapered_v4 import recursor
    original = recursor.structural_tuples
    touched = []
    def mutate(*args, **kwargs):
        values = list(original(*args, **kwargs))
        if len(values) > 1:
            touched.append(True)
            if mutation == 'duplicate': values[-1] = values[-2]
            if mutation == 'substitution': values[0] = values[1]
            if mutation == 'reverse': values.reverse()
            if mutation == 'invalid': values[-1] = (99,) + values[-1][1:]
            if mutation == 'omit': values.pop()
        yield from values
    monkeypatch.setattr(recursor, 'structural_tuples', mutate)
    result = contract_recursive(state(), RecursionPolicy(allow_nonshrinking_leaf=True,
                                                         verify_tuple_identities=tuple_oracle))
    assert touched
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'result' not in result and 'certificate' not in result


def test_generator_and_precount_corruption_cannot_hide_duplicate(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    from veritas.research.eth_recursive_contraction_v39 import point_modes
    original = recursor.structural_tuples
    def duplicate(*args, **kwargs):
        values = list(original(*args, **kwargs))
        if len(values) > 1: values[-1] = values[-2]
        yield from values
    monkeypatch.setattr(recursor, 'structural_tuples', duplicate)
    monkeypatch.setattr(point_modes, 'structural_tuples', duplicate)
    result = contract_recursive(state(), RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'duplicate or out-of-order' in result['reason'] and 'result' not in result


def test_standalone_expansion_rejects_same_count_substitution(monkeypatch):
    from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
    from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
    from veritas.research.eth_recursive_contraction_v39 import point_children
    parent = state().network
    source = implicit_mode_source(construct_implicit_packing(parent.bipartite_edges(), r=2, a=1))
    modes = make_point_modes(source, node=1, precision=5, extension_degree=3, zeta=(1,0,0))
    original = point_children.structural_tuples
    def duplicate(*args, **kwargs):
        values = list(original(*args, **kwargs))
        if len(values)>1: values[-1]=values[-2]
        yield from values
    monkeypatch.setattr(point_children, 'structural_tuples', duplicate)
    with pytest.raises(ValueError, match='duplicate or out-of-order'):
        point_children.contract_point_child_expansion(parent, modes)


def test_independent_checker_budget_failure_is_inconclusive(monkeypatch):
    from veritas.research.tapered_v4.budget import Inconclusive, WorkBudget
    original = WorkBudget.charge
    def stop(self, name, amount=1):
        original(self, name, amount)
        if name == 'independent_tuple_check_steps':
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'injected checker limit')
    monkeypatch.setattr(WorkBudget, 'charge', stop)
    result = contract_recursive(state(), RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result and 'certificate' not in result


def test_default_small_point_oracle_runs_and_detects_disagreement(monkeypatch):
    from veritas.research.eth_recursive_contraction_v39 import point_children
    policy = RecursionPolicy(allow_nonshrinking_leaf=True)
    result = contract_recursive(state(), policy)
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((3, 0, 0),)
    assert result['point_identity_coverage'] == 'ALL_ACTIVE_POINTS_CHECKED'
    assert result['ledger']['counters']['oracle_point_checks'] == result['ledger']['counters']['point_evaluations']
    assert result['ledger']['counters']['independent_tuple_count_checks'] > 0
    original = point_children._direct_point_oracle
    def corrupt(parent, source, node, zeta, ring, budget):
        return ring.add(original(parent, source, node, zeta, ring, budget), ring.one)
    monkeypatch.setattr(point_children, '_direct_point_oracle', corrupt)
    damaged = contract_recursive(state(), policy)
    assert damaged['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'point oracle disagrees' in damaged['reason'] and 'result' not in damaged


def test_small_point_oracle_cannot_be_disabled_for_new_results():
    for invalid in (0, 1, True):
        with pytest.raises(ValueError):
            RecursionPolicy(auto_point_oracle_edges=invalid)


def test_point_oracle_conflicting_caps_fail_closed():
    result = contract_recursive(state(), RecursionPolicy(allow_nonshrinking_leaf=True,
                                   auto_point_oracle_edges=2, point_oracle_edge_limit=1))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and 'result' not in result


def test_independent_dp_detects_common_omission_in_generator_and_precount(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    from veritas.research.eth_recursive_contraction_v39 import point_modes
    original = recursor.structural_tuples
    touched = []
    def omit(*args, **kwargs):
        values = list(original(*args, **kwargs))
        if len(values) > 1:
            touched.append(True)
            values.pop()
        yield from values
    monkeypatch.setattr(recursor, 'structural_tuples', omit)
    monkeypatch.setattr(point_modes, 'structural_tuples', omit)
    result = contract_recursive(state(), RecursionPolicy(allow_nonshrinking_leaf=True))
    assert touched and result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'independent structural tuple count' in result['reason']
    assert 'result' not in result and 'certificate' not in result


def test_legacy_v1_transcript_replays_with_fresh_stream_checker():
    from copy import deepcopy
    from veritas.research.tapered_v4 import replay_certificate
    from veritas.research.tapered_v4.recursor import LEGACY_SCHEMA, SCHEMA_V2, _execute_recursive
    policy = RecursionPolicy(allow_nonshrinking_leaf=True)
    result = _execute_recursive(state(), policy, transcript_version=2)
    assert result['certificate']['schema'] == SCHEMA_V2
    assert replay_certificate(state(), policy, result['certificate'])['legacy_v2_replay']
    legacy_source = _execute_recursive(state(), policy, legacy_point_policy=True,
                                       transcript_version=2)
    legacy = deepcopy(legacy_source['certificate'])
    legacy['schema'] = LEGACY_SCHEMA
    del legacy['policy']['auto_point_oracle_edges']
    replay = replay_certificate(state(), RecursionPolicy(allow_nonshrinking_leaf=True), legacy)
    assert replay['valid'] and replay['legacy_v1_replay'] and not replay['independent_proof']
    legacy['policy']['auto_point_oracle_edges'] = 2
    assert not replay_certificate(state(), policy, legacy)['valid']
