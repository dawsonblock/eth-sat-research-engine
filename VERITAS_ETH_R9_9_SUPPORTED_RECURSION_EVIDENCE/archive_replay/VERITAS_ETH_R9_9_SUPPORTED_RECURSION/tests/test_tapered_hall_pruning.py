import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.independent_tuple_oracle import direct_tuple_contribution
from veritas.research.eth_recursive_contraction_v39.point_modes import check_point_modes, make_point_modes
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState, contract_recursive
from veritas.research.tapered_v4.budget import Inconclusive, WorkBudget
from veritas.research.tapered_v4.recursor import _hall_zero_witness
from veritas.research.tensor import from_cnf


def example():
    f = first_irreducible(3)
    network = describe_integer_network(from_cnf(CNF.from_lists(2, [[1, 2]])),
                                       creation_precision=3, defining_polynomial=f)
    return TaperedState(network, 0, 3, f, 1, network.edges)


def test_opt_in_matching_preserves_exact_count_and_charges_work():
    state = example()
    common = dict(allow_nonshrinking_leaf=True, verify_small_nodes=True,
                  max_certificate_bytes=8_000_000)
    baseline = contract_recursive(state, RecursionPolicy(**common))
    checked = contract_recursive(state, RecursionPolicy(**common, enable_hall_pruning=True))
    assert baseline['status'] == checked['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert baseline['result'] == checked['result'] == ((3, 0, 0),)
    assert baseline['ledger']['counters'].get('hall_matching_steps', 0) == 0
    assert checked['ledger']['counters']['hall_matching_steps'] > 0
    assert checked['ledger']['complete'] is False


def test_forged_hall_witness_never_produces_a_count(monkeypatch):
    from veritas.research.tapered_v4 import recursor

    def forged(*args, **kwargs):
        return {'status': 'ZERO_IF_SUPPLIED_SUPPORT_COMPLETE',
                'witness': {'packet': 0, 'target_group': 0, 'mode_indices': [0],
                            'row_ids': [], 'demand': 1, 'available_rows': 0}}

    monkeypatch.setattr(recursor, 'certify_structural_tuple_matching', forged)
    result = contract_recursive(example(), RecursionPolicy(allow_nonshrinking_leaf=True,
                                                             enable_hall_pruning=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'result' not in result and 'certificate' not in result


def test_matching_budget_failure_is_inconclusive(monkeypatch):
    original = WorkBudget.charge

    def stop_at_matching(self, name, amount=1):
        original(self, name, amount)
        if name == 'hall_matching_steps':
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'injected matching cap')

    monkeypatch.setattr(WorkBudget, 'charge', stop_at_matching)
    result = contract_recursive(example(), RecursionPolicy(allow_nonshrinking_leaf=True,
                                                             enable_hall_pruning=True))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result and 'certificate' not in result


def test_hall_policy_requires_boolean():
    with pytest.raises(ValueError):
        RecursionPolicy(enable_hall_pruning=1)


def test_replayed_hall_witness_matches_direct_tuple_oracle():
    parent = example().network
    source = implicit_mode_source(construct_implicit_packing(parent.bipartite_edges(), r=2, a=1))
    modes = make_point_modes(source, node=1, precision=5, extension_degree=3, zeta=(1, 0, 0))
    assert check_point_modes(modes)['valid']
    assert len(modes['modes']) == 1
    budget = WorkBudget(RecursionPolicy())
    witness = _hall_zero_witness(modes['modes'], (2,), budget)
    assert witness['demand'] == 2 and witness['available_rows'] == 1
    assert budget.counters['hall_zero_tuples'] == 1
    assert budget.counters['hall_witness_steps'] > 0
    assert direct_tuple_contribution(parent, modes, (2,))['result'] == ((0, 0, 0),)
