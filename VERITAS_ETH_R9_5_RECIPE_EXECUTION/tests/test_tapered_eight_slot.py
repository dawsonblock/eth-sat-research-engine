import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState, contract_recursive
from veritas.research.tensor import from_cnf


def test_eight_slot_sixty_four_group_finite_recursion_matches_direct_oracle():
    f = first_irreducible(4)
    network = describe_integer_network(from_cnf(CNF.from_lists(1, [[1]])),
                                       creation_precision=2, defining_polynomial=f)
    state = TaperedState(network, 0, 2, f, 1, network.edges)
    policy = RecursionPolicy(allow_nonshrinking_leaf=True, finite_parameters=(3, 1, 64),
                             verify_small_nodes=True, max_seconds=90,
                             max_work=4_000_000, max_certificate_bytes=20_000_000)
    result = contract_recursive(state, policy)
    assert result['status'] == 'EXACT_MODULAR_CONTRACTION_FINITE'
    assert result['result'] == ((1, 0, 0, 0),)
    assert result['ledger']['counters']['point_evaluations'] == 128
    assert result['ledger']['counters']['oracle_leaf_calls'] == 1
    assert result['ledger']['counters']['nonshrinking_children'] > 0
    assert not result['subexponential_runtime_proven']


@pytest.mark.parametrize('parameters', [(4, 1, 2), (3, 4, 2), (3, 1, 65)])
def test_finite_eight_slot_schedule_still_enforces_caps(parameters):
    with pytest.raises(ValueError):
        RecursionPolicy(finite_parameters=parameters)
