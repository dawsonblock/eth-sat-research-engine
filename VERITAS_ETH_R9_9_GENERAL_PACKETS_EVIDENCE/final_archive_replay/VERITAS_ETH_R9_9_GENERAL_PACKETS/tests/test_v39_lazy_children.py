from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_mode_source,
)
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_recursive_contraction_v39 import (
    build_group_children, contract_child_expansion,
    check_child_expansion_certificate,
)
import pytest


def _fixture():
    net = from_cnf(CNF.from_lists(2, [[1, 2]]))
    packing = construct_implicit_packing(make_bipartite_edges(net), r=2, a=1)
    source = implicit_mode_source(packing)
    modes = make_jet_tile_modes(source, node=1, precision=5, jet_length=2)
    return net, modes


def test_lazy_group_children_reconstruct_the_finite_parent_identity():
    net, modes = _fixture()
    beta = (0,) * len(modes['modes'])
    children = build_group_children(net, modes, beta)
    assert children
    assert sum(child.edge_count for child in children) == 2 * net.edges
    for child in children:
        assert child.maximum_degree == max(
            [len(f.ports) for f in child.original_vertices] +
            [len(f.ports) for f in child.packet_tensors] + [0]
        )

    certificate = contract_child_expansion(net, modes, max_work=250_000)
    assert certificate['direct_oracle_matches']
    assert certificate['recursive_child_networks'] is False
    assert check_child_expansion_certificate(certificate)['valid']


def test_lazy_child_builder_rejects_bad_tuple_and_failed_budget():
    net, modes = _fixture()
    with pytest.raises(ValueError, match='beta'):
        build_group_children(net, modes, (0,)) if len(modes['modes']) != 1 else build_group_children(net, modes, (-1,))
    with pytest.raises(ValueError, match='retained'):
        build_group_children(net, modes, (modes['precision'],) + (0,) * (len(modes['modes']) - 1))

    certificate = contract_child_expansion(net, modes, max_work=250_000)
    assert not check_child_expansion_certificate(certificate, max_work=1)['valid']


def test_child_description_does_not_share_mutable_mode_coefficients():
    from copy import deepcopy

    net, modes = _fixture()
    children = build_group_children(net, modes, (0,) * len(modes['modes']))
    snapshot = deepcopy(children)
    assert modes['local']
    modes['local'][0][2][1][0] ^= 1
    assert children == snapshot


@pytest.mark.parametrize('variables, clauses', [
    (2, [[1, 2], [-1, -2]]),
    (2, [[1, -2], [2]]),
    (3, [[1, 2, 3]]),
    (3, [[1, -2], [-1, 3], [2, -3]]),
    (3, [[1]]),  # isolated variables contribute zero-port constant factors
])
def test_child_networks_cover_more_packet_and_group_patterns(variables, clauses):
    net = from_cnf(CNF.from_lists(variables, clauses))
    packing = construct_implicit_packing(make_bipartite_edges(net), r=2, a=1)
    modes = make_jet_tile_modes(implicit_mode_source(packing), node=1,
                                precision=6, jet_length=2)
    certificate = contract_child_expansion(net, modes, max_work=250_000)
    assert certificate['direct_oracle_matches']
    assert certificate['retained_tuple_count'] == len(certificate['tuples'])
    assert all(sum(child['edge_count'] for child in row['children']) == 2 * net.edges
               for row in certificate['tuples'])
