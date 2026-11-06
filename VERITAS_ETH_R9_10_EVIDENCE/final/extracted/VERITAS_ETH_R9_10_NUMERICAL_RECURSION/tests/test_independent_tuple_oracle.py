import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_sparse_mode_source
from veritas.research.eth_recursive_contraction_v39.described_network import (
    contract_described_network, describe_integer_network,
)
from veritas.research.eth_recursive_contraction_v39.independent_tuple_oracle import direct_tuple_contribution
from veritas.research.eth_recursive_contraction_v39.point_children import _ring_for, build_point_children
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples


def test_each_retained_tuple_matches_independent_row_selection_oracle():
    network = from_cnf(CNF.from_lists(2, [[1, 2]]))
    parent = describe_integer_network(network, creation_precision=3,
                                      defining_polynomial=first_irreducible(3))
    packing = construct_implicit_packing(parent.bipartite_edges(), r=2, a=1)
    modes = make_point_modes(implicit_sparse_mode_source(packing), node=1, precision=5,
                             extension_degree=3, zeta=(1, 0, 0))
    ring, _ = _ring_for(parent, modes)
    tuples = tuple(structural_tuples(modes['modes'], 5))
    assert len(tuples) > 1
    for beta in tuples:
        product_value = ring.one
        for child in build_point_children(parent, modes, beta):
            value = contract_described_network(child.network, ring, max_edges=12)['result']
            product_value = ring.mul(product_value, value)
        direct = direct_tuple_contribution(parent, modes, beta)
        assert direct['result'] == product_value
        assert direct['work_units'] > 0
    with pytest.raises(ValueError, match='weighted-tuple'):
        direct_tuple_contribution(parent, modes, (5,) + (0,) * (len(modes['modes']) - 1))
