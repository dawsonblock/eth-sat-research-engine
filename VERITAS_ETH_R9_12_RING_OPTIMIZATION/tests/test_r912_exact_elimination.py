from dataclasses import replace
import importlib.util
from pathlib import Path
import random

import pytest

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.model import Budget, ParentCall, Semantics, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.tapered_v4.source_recipes import make_reference
from veritas.research.tapered_v4.source_state import SourceVertex
import veritas.research.parent_child_r912.elimination as elimination
from veritas.research.parent_child_r912.elimination import (
    EliminationBudget, call_scopes, eliminate, plan, plan_order, verify_order)
from veritas.research.parent_child_r912.routes import Classification, Route, contract_routed, select_route

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('interaction_probe', ROOT/'scripts/experiment_r912_interaction.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=1_000_000_000, max_seconds=600)
FLAGS = ('source_qualified', 'theorem_mode_enabled', 'theorem_aligned',
         'source_recursive_bound_evidence', 'subexponential_bound_evidence')


def random_call(seed, edges, *, rows=4, columns=4, ell=1, precision=24, degree=3, max_arity=3):
    """Dense jets with nonzero extension coordinates in every V coefficient."""
    rng = random.Random(seed)
    f, e = first_irreducible(degree), degree
    while True:
        owners = {side: [rng.randrange(count) for _ in range(edges)]
                  for side, count in (('row', rows), ('column', columns))}
        ports = {side: [tuple(x for x in range(edges) if owners[side][x] == v) for v in range(count)]
                 for side, count in (('row', rows), ('column', columns))}
        if all(1 <= len(p) <= max_arity for side in ports.values() for p in side):
            break
    vertices = []
    for side in ('row', 'column'):
        for v, scope in enumerate(ports[side]):
            data = [[[rng.randrange(-3, 4) % (1 << precision) for _ in range(e)] for _ in range(ell)]
                    for _ in range(1 << len(scope))]
            ref = make_reference(kind='dense', arity=len(scope), creation_precision=precision,
                                 defining_polynomial=f, jet_length=ell, data=data)
            vertices.append(SourceVertex(side, v, scope, ref))
    return ParentCall(max(16, 2*edges), 0, precision, f, edges, tuple(vertices), jet_length=ell)


def interaction_parent(tmp_path, n=32, offset=5):
    data = probe.graph(n, offset)
    source = tmp_path/f'input_{n}_{offset}.json'
    source.write_bytes(canonical(data))
    return data, load_input(source, max_extension_degree=12)


@pytest.mark.parametrize('seed,edges,ell', [(1, 6, 1), (2, 8, 1), (3, 7, 2), (4, 9, 3), (5, 10, 2), (6, 5, 4)])
def test_elimination_matches_exhaustive_leaf_in_jet_ring(seed, edges, ell):
    call = random_call(seed, edges, ell=ell)
    budget = EliminationBudget()
    for heuristic in ('min_fill', 'min_degree'):
        certificate = plan(call, replace(budget, heuristic=heuristic))
        assert certificate['fits']
        result, ledger = eliminate(call, certificate, replace(budget, heuristic=heuristic))
        assert result == leaf(call, Budget(POLICY))
        assert ledger['work_units'] == certificate['predicted_work']
    assert any(any(c) for c in result[1:]) or ell == 1


@pytest.mark.parametrize('n,offset', [(3, 2), (4, 2), (5, 2), (8, 3), (12, 5)])
def test_interaction_family_matches_independent_integer_oracle(tmp_path, n, offset):
    data, parent = interaction_parent(tmp_path, n, offset)
    report = contract_routed(parent, route=Route.ELIMINATION)
    assert report['status'] == 'PASS_EXACT_BOUNDED_WIDTH_ELIMINATION', report
    expected = probe.integer_elimination(data)['integer']
    assert report['result'][0][0] == expected % (1 << parent.precision) == expected
    assert not any(report['result'][0][1:])


@pytest.mark.parametrize('offset', [5, 2, 16, 31])
def test_96_wire_interacting_fixture_exact_via_elimination_route(tmp_path, offset):
    data, parent = interaction_parent(tmp_path, 32, offset)
    assert parent.edge_count == 96 and len(parent.vertices) == 64
    assert all(len(set(v['table'])) > 1 for v in data['vertices'])
    reference = probe.integer_elimination(data)
    report = contract_routed(parent, route=Route.AUTO)
    assert report['status'] == 'PASS_EXACT_BOUNDED_WIDTH_ELIMINATION', report
    assert report['result_classification'] == Classification.EXACT_ELIMINATION.value
    assert report['result'][0][0] == reference['integer']
    assert not any(report['result'][0][1:])
    assert report['elimination_width'] <= reference['max_frontier_bits']
    if offset == 5:
        assert report['elimination_width'] == 17
    assert report['recursive_route_used'] is False
    assert all(report[flag] is False for flag in FLAGS)


def test_ordering_verifier_recomputes_widths_and_rejects_bad_orders():
    call = random_call(7, 8)
    scopes, variables = call_scopes(call)
    budget = EliminationBudget()
    order = plan_order(scopes, variables)
    good = verify_order(scopes, variables, order, budget)
    with pytest.raises(ValueError, match='permutation'):
        verify_order(scopes, variables, order[:-1], budget)
    with pytest.raises(ValueError, match='permutation'):
        verify_order(scopes, variables, order[:-1] + order[:1], budget)
    forged = dict(good, steps=[[x, 0, k] for x, _, k in good['steps']])
    if forged['steps'] != good['steps']:
        with pytest.raises(ValueError, match='certificate mismatch'):
            eliminate(call, forged, budget)
    matching = verify_order(((0,), (1,), (0,), (1,)), (0, 1), (1, 0), budget)
    assert matching['width'] == 0 and matching['fits']


def test_width_budget_refuses_before_any_table_allocation(tmp_path, monkeypatch):
    _, parent = interaction_parent(tmp_path, 32, 5)

    def forbidden(*args, **kwargs):
        pytest.fail('table allocated before the ordering was admitted')
    monkeypatch.setattr(elimination, 'evaluate_compiled', forbidden)
    monkeypatch.setattr(elimination, '_index_maps', forbidden)
    tight = EliminationBudget(max_width=16)
    for budget in (tight, EliminationBudget(max_table_entries=1 << 16),
                   EliminationBudget(max_live_entries=1 << 16), EliminationBudget(max_work=1_000_000)):
        report = contract_routed(parent, route=Route.ELIMINATION, elimination_budget=budget)
        assert report['status'] == 'INCONCLUSIVE_ELIMINATION_BUDGET'
        assert 'result' not in report and report['result_classification'] is None
        assert all(report[flag] is False for flag in FLAGS)
    assert select_route(parent, Route.ELIMINATION, tight)['ordering']['width'] == 17


def test_runtime_overrun_never_returns_a_partial_count(monkeypatch):
    call = random_call(8, 10)
    clock = iter(range(10**9))
    monkeypatch.setattr(elimination, 'monotonic', lambda: next(clock) * 0.5)
    report = contract_routed(call, route=Route.ELIMINATION, elimination_budget=EliminationBudget(max_seconds=20))
    assert report['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'elimination time budget' in report['reason']
    assert 'result' not in report and report['result_classification'] is None


def test_auto_route_falls_back_to_unchanged_recursion_with_distinct_classification():
    from veritas.research.parent_child_r910.engine import contract
    call = random_call(9, 3, rows=3, columns=3, max_arity=1)
    direct = contract(call, policy=POLICY)
    routed = contract_routed(call, route=Route.AUTO, elimination_budget=EliminationBudget(max_width=1, max_work=1),
                             policy=POLICY)
    assert routed['route_selection']['route'] == Route.RECURSIVE.value
    assert 'elimination refused before allocation' in routed['route_selection']['reason']
    assert routed['status'] == direct['status']
    assert routed['result'] == direct['result']
    assert routed['result_classification'] == Classification.RECURSIVE.value
    explicit = contract_routed(call, route=Route.RECURSIVE, policy=POLICY)
    assert explicit['route_selection']['ordering'] is None
    eliminated = contract_routed(call, route=Route.ELIMINATION)
    assert eliminated['result'] == direct['result']
    assert eliminated['result_classification'] == Classification.EXACT_ELIMINATION.value
    assert eliminated['result_classification'] != routed['result_classification']
    for report in (routed, explicit, eliminated):
        assert all(report[flag] is False for flag in FLAGS)


def test_elimination_route_is_finite_only():
    call = random_call(10, 4)
    source = replace(call, semantics=Semantics.FINITE_BOUNDARY_EXACT)
    report = contract_routed(source, route=Route.ELIMINATION)
    assert report['status'] == 'INCONCLUSIVE_SOURCE_REFINEMENT' and 'result' not in report
    with pytest.raises(TypeError):
        select_route(call, 'elimination')


def test_budget_fields_are_validated():
    for field, value in (('max_width', 0), ('max_width', 31), ('max_work', -1), ('heuristic', 'random')):
        with pytest.raises(ValueError):
            EliminationBudget(**{field: value})
