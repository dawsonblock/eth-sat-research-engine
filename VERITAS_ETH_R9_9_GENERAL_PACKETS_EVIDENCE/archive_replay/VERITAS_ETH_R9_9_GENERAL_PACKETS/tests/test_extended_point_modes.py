"""Finite higher-packet/radix tests; no theorem-scale complexity claim."""
from copy import deepcopy

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_sparse_mode_source,
)
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_children import contract_point_child_expansion
from veritas.research.eth_recursive_contraction_v39.point_modes import check_point_modes, make_point_modes


@pytest.mark.parametrize('radix', [2, 8, 64])
@pytest.mark.parametrize('node', [-1, 1])
def test_eight_slot_modes_reconstruct_and_contract_against_direct_oracle(radix, node):
    network = from_cnf(CNF.from_lists(3, [[1, 2], [1, 3], [-2]]))
    parent = describe_integer_network(network, creation_precision=3,
                                      defining_polynomial=first_irreducible(3))
    packing = construct_implicit_packing(parent.bipartite_edges(), r=radix, a=3)
    source = implicit_sparse_mode_source(packing)
    modes = make_point_modes(source, node=node, precision=5,
                             extension_degree=3, zeta=(1, 1, 0))
    assert source['L'] == 8
    assert modes['cross_pairs'] and modes['modes']
    assert check_point_modes(modes)['valid']
    result = contract_point_child_expansion(parent, modes, max_work=1_000_000, timeout_s=25)
    assert result['direct_oracle_matches']
    assert result['result'] == result['direct_oracle_result']
    assert not result['subexponential_runtime_proven']
    altered = deepcopy(modes)
    altered['modes'][0]['weight'] += 1
    assert not check_point_modes(altered)['valid']


@pytest.mark.parametrize(('edges', 'node', 'limit'), [
    ([(0, 2), (0, 1), (3, 3), (3, 1), (0, 0), (0, 2)], 2, 6),
    ([(0, 2), (1, 2), (1, 1), (1, 2), (1, 0), (2, 3), (1, 2), (1, 3)], 4, 8),
])
def test_eight_slot_higher_valuation_coordinates_have_nontrivial_cross_modes(edges, node, limit):
    source = implicit_sparse_mode_source(construct_implicit_packing(edges, r=2, a=3))
    modes = make_point_modes(source, node=node, precision=5, extension_degree=3,
                             zeta=(1, 1, 0), max_parent_wires=limit)
    assert modes['cross_pairs'] and modes['modes']
    # This separately rebuilds W from exact rational shifted polynomials and
    # checks every reconstructed entry, not just the generated mode count.
    assert check_point_modes(modes, max_parent_wires=limit)['valid']


def test_point_mode_parent_wire_guard_remains_explicit():
    source = implicit_sparse_mode_source(construct_implicit_packing([(i, i) for i in range(9)], r=2, a=3))
    with pytest.raises(ValueError):
        make_point_modes(source, node=1, precision=5, extension_degree=3, max_parent_wires=8)
    with pytest.raises(ValueError):
        make_point_modes(source, node=1, precision=5, extension_degree=3, max_parent_wires=9)
