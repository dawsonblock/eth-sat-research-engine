from itertools import product

import pytest

from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_modes_v31 import make_jet_tile_modes, check_jet_tile_modes
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_recursive_contraction_v39 import (
    build_group_children, contract_group_child, describe_group_child,
    contract_described_network, contract_point_child_expansion,
    make_point_modes, check_point_modes,
)
from veritas.research.eth_recursive_contraction_v39.lazy_children import PacketTensorEntry, _Budget
from veritas.research.eth_recursive_contraction_v39.described_network import CreatedPacketTensor


def test_packet_recipe_is_evaluated_at_creation_precision_before_lifting():
    # At precision 3, 1 - 7 = 2 modulo 8.  Recomputing at precision 5
    # with the same stored coefficient would give 26 instead.
    recipe = PacketTensorEntry(0, (0, 1), (('Y', 0), ('X', 0)),
                               ((0, ((0, ((7,),)),)),), (), ())
    tensor = CreatedPacketTensor(recipe, 3, 0b11, 1)
    target = JetRing(ExtensionRing(5, 0b11), 1)
    assert tensor.evaluate((0, 1), target, _Budget(100, 5)) == target.elem([[2]])
    assert recipe.evaluate((0, 1), target, _Budget(100, 5)) == target.elem([[26]])
    with pytest.raises(ValueError, match='decreased precision'):
        tensor.evaluate((0, 1), JetRing(ExtensionRing(2, 0b11), 1), _Budget(100, 5))


def test_child_description_preserves_original_residues_and_can_be_repacked():
    net = TensorNetwork(2, (
        Factor((0, 1), (-1, 2, -3, 4), 'row:0'),
        Factor((0,), (-1, 2), 'col:0'),
        Factor((1,), (3, -4), 'col:1'),
    ))
    reduced = TensorNetwork(net.edges, tuple(
        Factor(f.ports, tuple(value % 8 for value in f.table), f.label)
        for f in net.factors))
    packing = construct_implicit_packing(make_bipartite_edges(net), r=2, a=1)
    modes = make_jet_tile_modes(implicit_mode_source(packing), node=1,
                                precision=5, jet_length=2)
    beta = (0,) * len(modes['modes'])
    children = build_group_children(net, modes, beta)
    expected_children = {c.group: c for c in build_group_children(reduced, modes, beta)}
    creation_ring = JetRing(ExtensionRing(5, modes['irreducible_polynomial']), 2)
    higher_ring = JetRing(ExtensionRing(7, modes['irreducible_polynomial']), 2)

    for child in children:
        described = describe_group_child(
            child, modes, original_creation_precisions=(3,) * len(child.original_vertices))
        result = contract_described_network(described, creation_ring)
        expected = contract_group_child(expected_children[child.group], modes)
        assert result['result'] == creation_ring.elem(expected['result'])

        # Re-evaluate each stored recipe at its own creation precision, lift
        # its coordinates, then independently enumerate the child graph.
        manual = higher_ring.zero
        for bits in product((0, 1), repeat=described.edges):
            term = higher_ring.one
            for vertex in described.vertices:
                entry = vertex.tensor.evaluate(tuple(bits[p] for p in vertex.ports),
                                               higher_ring, _Budget(10000, 5))
                term = higher_ring.mul(term, entry)
            manual = higher_ring.add(manual, term)
        assert contract_described_network(described, higher_ring)['result'] == manual

        if 0 < described.edges <= 6:
            child_packing = construct_implicit_packing(described.bipartite_edges(), r=2, a=1)
            source = implicit_mode_source(child_packing)
            for zeta in ((0, 0, 0), (1, 0, 0), (0, 1, 0)):
                next_modes = make_point_modes(source, node=1, precision=7,
                                              extension_degree=3, zeta=zeta)
                assert check_point_modes(next_modes)['valid']
                second = contract_point_child_expansion(described, next_modes)
                assert second['direct_oracle_matches']
                assert all(row['structurally_zero'] or
                           sum(c['edge_count'] for c in row['children']) == 2 * described.edges
                           for row in second['tuples'])
                assert not second['tapered_reconstruction_implemented']


def test_point_mode_checker_rejects_changed_interpolation_point_and_weight():
    from copy import deepcopy

    net = TensorNetwork(2, (Factor((0, 1), (0, 1, 1, 1), 'row:0'),
                            Factor((0,), (1, 1), 'col:0'),
                            Factor((1,), (1, 1), 'col:1')))
    source = implicit_mode_source(construct_implicit_packing(make_bipartite_edges(net), r=2, a=1))
    modes = make_point_modes(source, node=1, precision=5, extension_degree=3,
                             zeta=(0, 1, 0))
    assert check_point_modes(modes)['valid']
    corrupt = deepcopy(modes)
    corrupt['zeta'][0] ^= 1
    assert not check_point_modes(corrupt)['valid']
    if modes['modes']:
        corrupt = deepcopy(modes)
        corrupt['modes'][0]['weight'] += 1
        assert not check_point_modes(corrupt)['valid']


@pytest.mark.parametrize('node', [-3, -2, -1, 1, 2, 3])
@pytest.mark.parametrize('zeta', [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 1)])
def test_point_modes_reconstruct_cauchy_entries_for_four_slot_packets(node, zeta):
    from veritas.core.cnf import CNF
    from veritas.research.tensor import from_cnf

    net = from_cnf(CNF.from_lists(2, [[1, 2], [-1, -2]]))
    packing = construct_implicit_packing(make_bipartite_edges(net), r=2, a=2)
    modes = make_point_modes(implicit_mode_source(packing), node=node, precision=5,
                             extension_degree=3, zeta=zeta)
    assert check_point_modes(modes)['valid']
