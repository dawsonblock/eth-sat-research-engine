import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples
from veritas.research.tensor import from_cnf
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState, contract_recursive
from veritas.research.tapered_v4.budget import Inconclusive, WorkBudget


def state_for_one_wire():
    f = first_irreducible(3)
    network = describe_integer_network(from_cnf(CNF.from_lists(1, [[1]])),
                                       creation_precision=2, defining_polynomial=f)
    return TaperedState(network, 0, 2, f, 1, network.edges)


def test_structural_tuple_callback_preserves_tuples_and_can_interrupt_before_yield():
    modes = [{'weight': 1, 'packet': 0, 'target_group': 0,
              'rows': [[0, [[1]]], [1, [[1]]]]} for _ in range(2)]
    expected = list(structural_tuples(modes, 3))
    steps = []
    assert list(structural_tuples(modes, 3, _on_step=lambda: steps.append(1))) == expected
    assert len(steps) > len(expected)

    def stop():
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'test deadline')
    with pytest.raises(Inconclusive):
        next(structural_tuples(modes, 3, _on_step=stop))


def test_recursive_ledger_accounts_for_all_tuple_traversals():
    result = contract_recursive(state_for_one_wire(), RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((1, 0, 0),)
    for name in ('mode_precount_steps', 'mode_replay_precount_steps', 'tuple_execution_steps'):
        assert result['ledger']['counters'][name] > 0
    assert result['ledger']['complete'] is False


@pytest.mark.parametrize('phase', ['mode_precount_steps', 'mode_replay_precount_steps',
                                  'tuple_execution_steps'])
def test_tuple_work_exhaustion_returns_no_partial_count(monkeypatch, phase):
    original = WorkBudget.charge

    def charge_then_stop(self, name, amount=1):
        original(self, name, amount)
        if name == phase:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'injected tuple work exhaustion')

    monkeypatch.setattr(WorkBudget, 'charge', charge_then_stop)
    result = contract_recursive(state_for_one_wire(), RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert result['ledger']['counters'][phase] == 1
    assert 'result' not in result and 'certificate' not in result
