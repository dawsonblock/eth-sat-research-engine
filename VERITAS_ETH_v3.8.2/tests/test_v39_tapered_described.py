import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39 import (
    describe_integer_network, contract_tapered_finite, run_tapered_finite,
)
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedDenseTensor, DescribedNetwork, DescribedVertex,
)


def test_tapered_recovery_uses_creation_residues_and_checks_exact_count():
    net = TensorNetwork(1, (Factor((0,), (-1, 2), 'row:0'),
                            Factor((0,), (3, -2), 'col:0')))
    described = describe_integer_network(net, creation_precision=3,
                                         defining_polynomial=first_irreducible(3),
                                         jet_length=2)
    result = contract_tapered_finite(described, target_precision=5,
                                      max_recursive_levels=2, max_work=2_000_000)
    # The creation residues are (7,2) and (3,6): 7*3 + 2*6 = 33.
    assert result['result'] == ((1, 0, 0), (0, 0, 0))
    assert result['status'] == 'FINITE_TAPERED_CHILD_RECOVERY_VERIFIED'
    assert {node['precision'] for node in result['nodes']} == {69}
    assert result['recursive_levels_exercised'] == 2
    assert result['nested_calls'] > 0
    assert result['maximum_precision_bits'] == 197
    assert not result['ledger_complete']
    assert not result['subexponential_runtime_proven']


def test_tapered_recovery_rejects_exhausted_budget_without_a_count():
    net = TensorNetwork(1, (Factor((0,), (1, 1), 'row:0'),
                            Factor((0,), (1, 1), 'col:0')))
    described = describe_integer_network(net, creation_precision=3,
                                         defining_polynomial=first_irreducible(3))
    with pytest.raises((ValueError, RuntimeError)):
        contract_tapered_finite(described, target_precision=5, max_work=1)
    result = run_tapered_finite(described, target_precision=5, max_work=1)
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result


def test_tapered_recovery_handles_cross_group_modes_at_nonzero_points():
    net = from_cnf(CNF.from_lists(2, [[1, 2]]))
    described = describe_integer_network(net, creation_precision=3,
                                         defining_polynomial=first_irreducible(3))
    result = contract_tapered_finite(described, target_precision=3, max_work=2_000_000)
    assert result['result'] == ((3, 0, 0),)
    assert result['maximum_precision_bits'] == 131
    assert result['point_modes_generated'] > 0
    assert result['structurally_zero_tuples'] > 0
    charged = result['algorithm_work_units'] + result['independent_oracle_work_units']
    assert run_tapered_finite(described, target_precision=3, max_work=charged)['status'] == result['status']
    exhausted = run_tapered_finite(described, target_precision=3, max_work=charged - 1)
    assert exhausted['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in exhausted


def test_interpolation_point_limit_returns_inconclusive_without_a_count():
    net = from_cnf(CNF.from_lists(2, [[1, 2], [-1, -2]]))
    described = describe_integer_network(net, creation_precision=3,
                                         defining_polynomial=first_irreducible(3))
    result = run_tapered_finite(described, target_precision=5, max_points=1)
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'result' not in result


def test_two_levels_preserve_extension_and_truncated_polynomial_coordinates():
    f = first_irreducible(3)
    assert f == 0b1011  # U^3 = -U-1 in the lifted extension ring.
    ring = JetRing(ExtensionRing(3, f), 2)
    row = (ring.elem([[1, 1], [0, 1]]), ring.elem([[2], [1]]))
    col = (ring.elem([[2, 0, 1], [1]]), ring.elem([[1, 1], [0, 0, 1]]))
    network = DescribedNetwork(1, (
        DescribedVertex('row', 'row:0', (0,), CreatedDenseTensor(
            1, tuple(CreationJetEntry.capture(ring, value) for value in row))),
        DescribedVertex('column', 'col:0', (0,), CreatedDenseTensor(
            1, tuple(CreationJetEntry.capture(ring, value) for value in col))),
    ))
    result = contract_tapered_finite(network, target_precision=5,
                                      max_recursive_levels=2, max_work=2_000_000)
    assert result['recursive_levels_exercised'] == 2
    assert result['result'] == ((3, 3, 1), (1, 3, 2))


def test_two_scaled_levels_can_use_different_packet_exponents():
    net = TensorNetwork(1, (Factor((0,), (-1, 2), 'row:0'),
                            Factor((0,), (3, -2), 'col:0')))
    described = describe_integer_network(net, creation_precision=3,
                                         defining_polynomial=first_irreducible(4))
    levels = ((1, 1, 2), (2, 1, 2))
    result = contract_tapered_finite(described, target_precision=5,
                                    max_recursive_levels=2,
                                    experimental_level_parameters=levels,
                                    max_work=2_000_000)
    assert result['result'] == ((1, 0, 0, 0),)
    assert result['recursive_levels_exercised'] == 2
    assert result['experimental_level_parameters'] == levels
    assert result['maximum_precision_bits'] == 309
