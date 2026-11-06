import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.lazy_children import (
    ChildEvaluationBudgetExceeded, _Budget,
)
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState
from veritas.research.tapered_v4.budget import Inconclusive, WorkBudget
from veritas.research.tapered_v4.recursor import _run_leaf
from veritas.research.tensor import from_cnf


@pytest.mark.parametrize('oracle', [False, True])
def test_interrupted_leaf_records_observed_subcall_work(oracle):
    network = describe_integer_network(from_cnf(CNF.from_lists(3, [[1], [2], [3]])),
                                       creation_precision=4, defining_polynomial=0b11)
    state = TaperedState(network, 0, 4, 0b11, 1, network.edges)
    budget = WorkBudget(RecursionPolicy(max_work=5))
    ring = JetRing(ExtensionRing(4, 0b11), 1)
    with pytest.raises(Inconclusive) as failure:
        _run_leaf(state, ring, budget, oracle=oracle)
    assert failure.value.status == 'INCONCLUSIVE_RESOURCE_LIMIT'
    counter = 'oracle_failed_leaf_work' if oracle else 'algorithm_failed_leaf_work'
    assert budget.counters[counter] == 5
    assert budget.used == 5


def test_interrupted_child_work_is_reported_at_its_cooperative_cap():
    budget = _Budget(2, 5)
    budget.tick(2)
    with pytest.raises(ChildEvaluationBudgetExceeded) as failure:
        budget.tick()
    assert failure.value.work_units == 2
