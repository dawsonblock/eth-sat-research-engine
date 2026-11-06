"""Independent replay of actual finite packet recipes and half-wire loads."""
from copy import deepcopy
from dataclasses import replace

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_recursive_contraction_v39.point_children import build_point_children, _ring_for
from veritas.research.tapered_v4.child_partition import verify_constructed_child_partition
from veritas.research.tapered_v4.child_recipe_check import verify_constructed_child_recipes
from veritas.research.tapered_v4.actual_child_certificate import certify_actual_point_children
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState, contract_recursive


def fixture():
    parent = describe_integer_network(from_cnf(CNF.from_lists(2, [[1, 2]])),
                                      creation_precision=3, defining_polynomial=first_irreducible(3))
    source = implicit_mode_source(construct_implicit_packing(parent.bipartite_edges(), r=2, a=1))
    modes = make_point_modes(source, node=1, precision=5, extension_degree=3, zeta=(1, 0, 0))
    beta = (1,) * len(modes['modes'])
    assert len(beta) == 1
    children = build_point_children(parent, modes, beta)
    ring, checked_source = _ring_for(parent, modes)
    return parent, checked_source, modes, beta, children, ring


def forge(children, kind):
    result = list(children)
    for ci, child in enumerate(result):
        vertices = list(child.network.vertices)
        for vi, vertex in enumerate(vertices):
            if vertex.side != 'column':
                continue
            tensor, recipe = vertex.tensor, vertex.tensor.recipe
            if kind == 'local' and recipe.rows and recipe.rows[0][1]:
                rows = list(recipe.rows)
                rid, terms = rows[0]
                terms = list(terms)
                cid, coefficient = terms[0]
                terms[0] = (cid, ((coefficient[0][0] ^ 1,) + coefficient[0][1:],))
                rows[0] = (rid, tuple(terms))
                recipe = replace(recipe, rows=tuple(rows))
            elif kind in ('target_exponent', 'target_coefficient', 'target_omitted') and recipe.target_modes:
                mid, exponent, entries = recipe.target_modes[0]
                if kind == 'target_omitted':
                    changed = ()
                elif kind == 'target_exponent':
                    changed = ((mid, exponent + 1, entries),)
                else:
                    rid, coefficient = entries[0]
                    changed = ((mid, exponent, ((rid, ((coefficient[0][0] ^ 1,) + coefficient[0][1:],)),)),)
                recipe = replace(recipe, target_modes=changed)
            elif kind in ('source_exponent', 'source_coefficient', 'source_omitted') and recipe.source_modes:
                mid, exponent, entries = recipe.source_modes[0]
                if kind == 'source_omitted':
                    changed = ()
                elif kind == 'source_exponent':
                    changed = ((mid, exponent + 1, entries),)
                else:
                    cid, coefficient = entries[0]
                    changed = ((mid, exponent, ((cid, coefficient + 1),)),)
                recipe = replace(recipe, source_modes=changed)
            elif kind == 'precision':
                tensor = replace(tensor, creation_precision=tensor.creation_precision - 1)
            else:
                continue
            vertices[vi] = replace(vertex, tensor=replace(tensor, recipe=recipe))
            result[ci] = replace(child, network=replace(child.network, vertices=tuple(vertices)))
            return tuple(result)
    raise AssertionError('fixture does not contain requested recipe component')


def test_actual_recipe_and_port_checks_with_independent_tuple_oracle():
    parent, source, modes, beta, children, ring = fixture()
    report = verify_constructed_child_recipes(parent, source, modes, beta, children, ring)
    assert report['status'] == 'FINITE_CHILD_RECIPES_AND_ACTUAL_LOADS_CHECKED'
    assert sum(x['row_ports'] for x in report['groups']) == parent.edges
    assert sum(x['column_ports'] for x in report['groups']) == parent.edges
    assert all(x['child_edges'] == x['row_ports'] + x['column_ports'] for x in report['groups'])
    cert = certify_actual_point_children(parent, modes, beta, children, verify_tuple_identity=True)
    assert cert['status'] == 'FINITE_ACTUAL_POINT_CHILDREN_CHECKED'
    assert cert['certificate']['tuple_identity_checked']
    assert not cert['certificate']['all_tuples_checked']


@pytest.mark.parametrize('kind', ['local', 'target_exponent', 'target_coefficient', 'target_omitted',
                                  'source_exponent', 'source_coefficient', 'source_omitted', 'precision'])
def test_coefficient_and_creation_tampering_rejected_without_topology_change(kind):
    parent, source, modes, beta, children, ring = fixture()
    altered = forge(children, kind)
    assert verify_constructed_child_partition(parent, source, 0, altered)
    with pytest.raises(ValueError):
        verify_constructed_child_recipes(parent, source, modes, beta, altered, ring)
    assert certify_actual_point_children(parent, modes, beta, altered)['status'] == 'INVALID_ACTUAL_POINT_CHILDREN'


def test_invalid_mode_tuple_fails_closed():
    parent, source, modes, beta, children, ring = fixture()
    for invalid in ((), (True,), (-1,), (ring.base.p,)):
        with pytest.raises(ValueError):
            verify_constructed_child_recipes(parent, source, modes, invalid, children, ring)


def test_recursor_rejects_altered_child_coefficient_without_oracle(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    parent, _, _, _, _, _ = fixture()
    original = recursor._build_point_children_checked
    observed = []
    def corrupt(*args):
        children = original(*args)
        try:
            altered = forge(children, 'local')
        except AssertionError:
            return children
        observed.append(True)
        return altered
    monkeypatch.setattr(recursor, '_build_point_children_checked', corrupt)
    state = TaperedState(parent, 0, 3, first_irreducible(3), 1, parent.edges)
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True))
    assert observed
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'result' not in result and 'certificate' not in result
    assert 'coefficients' in result['reason']


def test_every_emitted_tuple_matches_independent_oracle_and_replays():
    from veritas.research.tapered_v4 import replay_certificate
    parent, _, _, _, _, _ = fixture()
    state = TaperedState(parent, 0, 3, first_irreducible(3), 1, parent.edges)
    policy = RecursionPolicy(allow_nonshrinking_leaf=True, verify_tuple_identities=True,
                             verify_point_identities=True)
    result = contract_recursive(state, policy)
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((3, 0, 0),)
    ledger = result['ledger']['counters']
    assert ledger['oracle_tuple_checks'] == ledger['retained_tuples'] > 1
    assert ledger['oracle_point_checks'] == ledger['point_evaluations'] > 1
    assert ledger['oracle_tuple_work'] > 0 and ledger['child_recipe_replay_steps'] > 0
    assert any(event['payload']['kind'] == 'tuple_identity_checked'
               for event in result['certificate']['events'])
    assert replay_certificate(state, policy, result['certificate'])['valid']
    altered = deepcopy(result['certificate'])
    event = next(event for event in altered['events']
                 if event['payload']['kind'] == 'tuple_identity_checked')
    event['payload']['point_index'] += 1
    assert not replay_certificate(state, policy, altered)['valid']


def test_corrupted_tuple_oracle_and_insufficient_caps_fail_closed(monkeypatch):
    from veritas.research.eth_recursive_contraction_v39 import independent_tuple_oracle
    parent, _, _, _, _, _ = fixture()
    state = TaperedState(parent, 0, 3, first_irreducible(3), 1, parent.edges)
    limited = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True,
                                  verify_tuple_identities=True, tuple_oracle_edge_limit=1))
    assert limited['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT' and 'result' not in limited
    original = independent_tuple_oracle.direct_tuple_contribution
    def corrupt(*args, **kwargs):
        value = original(*args, **kwargs)
        value['result'] = ((value['result'][0][0] ^ 1,) + value['result'][0][1:],)
        return value
    monkeypatch.setattr(independent_tuple_oracle, 'direct_tuple_contribution', corrupt)
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True,
                                                        verify_tuple_identities=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE' and 'result' not in result
    assert 'tuple oracle disagrees' in result['reason']


def test_actual_port_loads_report_rejected_64_group_example():
    parent = describe_integer_network(from_cnf(CNF.from_lists(2, [[1, 2]])),
                                      creation_precision=3, defining_polynomial=first_irreducible(3))
    source = implicit_mode_source(construct_implicit_packing(parent.bipartite_edges(), r=64, a=1))
    modes = make_point_modes(source, node=1, precision=5, extension_degree=3, zeta=(1, 0, 0))
    beta = (0,) * len(modes['modes'])
    children = build_point_children(parent, modes, beta)
    ring, source = _ring_for(parent, modes)
    report = verify_constructed_child_recipes(parent, source, modes, beta, children, ring)
    assert not report['all_sides_meet_port_bound']
    assert any(64*row['row_ports'] > 3*parent.edges or 64*row['column_ports'] > 3*parent.edges
               for row in report['groups'])
    state = TaperedState(parent, 0, 3, first_irreducible(3), 1, parent.edges)
    strict = contract_recursive(state, RecursionPolicy(finite_parameters=(1,1,64),
                                require_one_eighth_shrink=True))
    assert strict['status'] == 'INCONCLUSIVE_CHILD_SIZE_INVARIANT' and 'result' not in strict


def test_omitted_retained_tuple_is_rejected_before_recovery(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    parent, _, _, _, _, _ = fixture()
    state = TaperedState(parent, 0, 3, first_irreducible(3), 1, parent.edges)
    original = recursor.structural_tuples
    def omit_first(*args, **kwargs):
        iterator = iter(original(*args, **kwargs))
        next(iterator, None)
        yield from iterator
    monkeypatch.setattr(recursor, 'structural_tuples', omit_first)
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'tuple stream differs' in result['reason']
    assert 'result' not in result and 'certificate' not in result
