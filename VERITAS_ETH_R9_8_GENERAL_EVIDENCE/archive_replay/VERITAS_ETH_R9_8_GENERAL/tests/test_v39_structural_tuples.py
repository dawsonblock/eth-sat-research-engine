from itertools import product

import pytest

from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import make_point_modes, check_point_modes


def test_structural_tuple_stream_matches_independent_exhaustive_filter():
    modes = [
        {'weight': 1, 'packet': 0, 'target_group': 0, 'rows': [[0, []]]},
        {'weight': 2, 'packet': 0, 'target_group': 0, 'rows': [[0, []], [1, []]]},
        {'weight': 1, 'packet': 1, 'target_group': 0, 'rows': [[2, []]]},
    ]
    expected = {beta for beta in product(range(5), repeat=3)
                if beta[0] + 2 * beta[1] + beta[2] < 5
                and beta[0] <= 1 and beta[1] <= 2 and beta[2] <= 1
                and beta[0] + beta[1] <= 2}
    assert set(structural_tuples(modes, 5)) == expected
    with pytest.raises(ModeBudgetExceeded):
        list(structural_tuples(modes, 5, max_tuples=1))


def test_structural_budget_does_not_reject_nominally_large_zero_family():
    net = from_cnf(CNF.from_lists(2, [[1, 2]]))
    source = implicit_mode_source(construct_implicit_packing(make_bipartite_edges(net), r=2, a=1))
    cert = make_point_modes(source, node=1, precision=7, extension_degree=3,
                            zeta=(1, 0, 0), max_tuples=2)
    assert cert['mode_tuple_count'] == 7
    assert cert['structural_tuple_count'] == 2
    assert check_point_modes(cert)['valid']
