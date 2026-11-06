"""Differential check: dense and sparse packet sources must be interchangeable.

The implicit constructor has two serialisations of the same packing:
``implicit_mode_source`` writes one entry per packet slot (dense) and
``implicit_sparse_mode_source`` writes only occupied slots. Both describe the
packing of `lem:tensor-packets`, so every consumer must produce identical
certificates from either. This suite pins that invariant; before it existed,
several modules indexed ``packet['slots']`` directly and rejected or crashed
on the sparse schema.
"""
from __future__ import annotations

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import (
    check_implicit_mode_source, construct_implicit_packing, implicit_mode_source,
    implicit_sparse_mode_source, real_packet_slots,
)
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31.jet_tiles import check_jet_tile_modes, make_jet_tile_modes
from veritas.research.eth_recursive_contraction_v39 import (
    build_point_children, contract_child_expansion, contract_point_child_expansion,
    describe_integer_network, make_point_modes,
)
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples


CASES = [
    (2, [[1, 2]], 2, 1),
    (2, [[1, 2], [-1, -2]], 2, 1),
    (3, [[1, 2], [-1, 3], [2, -3]], 2, 1),
    (2, [[1, 2], [-1, -2], [1, -2]], 2, 2),
]


def _sources(wires, clauses, radix, exponent):
    net = from_cnf(CNF.from_lists(wires, clauses))
    packing = construct_implicit_packing(make_bipartite_edges(net), r=radix, a=exponent,
                                         max_work=None)
    return net, (implicit_mode_source(packing, max_work=None),
                 implicit_sparse_mode_source(packing, max_work=None))


@pytest.mark.parametrize('wires,clauses,radix,exponent', CASES)
def test_both_schemas_verify_and_agree_on_occupied_slots(wires, clauses, radix, exponent):
    _net, (dense, sparse) = _sources(wires, clauses, radix, exponent)
    assert check_implicit_mode_source(dense)['valid'] is True
    assert check_implicit_mode_source(sparse)['valid'] is True
    assert dense['schema'] != sparse['schema']
    for left, right in zip(dense['packets'], sparse['packets']):
        assert real_packet_slots(left, dense['L']) == real_packet_slots(right, sparse['L'])


@pytest.mark.parametrize('wires,clauses,radix,exponent', CASES)
def test_geometric_tile_modes_are_identical(wires, clauses, radix, exponent):
    _net, (dense, sparse) = _sources(wires, clauses, radix, exponent)
    left = make_jet_tile_modes(dense, node=1, precision=5, extension_degree=3, jet_length=2)
    right = make_jet_tile_modes(sparse, node=1, precision=5, extension_degree=3, jet_length=2)
    assert left['modes'] == right['modes']
    assert left['local'] == right['local']
    assert left['cross_pairs'] == right['cross_pairs']
    assert check_jet_tile_modes(left)['valid'] is True
    assert check_jet_tile_modes(right)['valid'] is True


@pytest.mark.parametrize('wires,clauses,radix,exponent', CASES)
def test_group_child_expansion_is_identical(wires, clauses, radix, exponent):
    net, (dense, sparse) = _sources(wires, clauses, radix, exponent)
    results = []
    for source in (dense, sparse):
        modes = make_jet_tile_modes(source, node=1, precision=5,
                                    extension_degree=3, jet_length=2)
        results.append(contract_child_expansion(net, modes, max_work=400_000))
    assert results[0]['result'] == results[1]['result']
    assert results[0]['tuples'] == results[1]['tuples']
    assert results[0]['direct_oracle_matches'] is True


@pytest.mark.parametrize('wires,clauses,radix,exponent', CASES)
def test_point_mode_children_are_identical(wires, clauses, radix, exponent):
    net = from_cnf(CNF.from_lists(wires, clauses))
    described = describe_integer_network(net, creation_precision=3,
                                         defining_polynomial=first_irreducible(3))
    packing = construct_implicit_packing(described.bipartite_edges(), r=radix,
                                         a=exponent, max_work=None)
    results = []
    for source in (implicit_mode_source(packing, max_work=None),
                   implicit_sparse_mode_source(packing, max_work=None)):
        modes = make_point_modes(source, node=1, precision=5, extension_degree=3)
        beta = next(iter(structural_tuples(modes['modes'], modes['precision'])))
        children = build_point_children(described, modes, beta)
        outcome = contract_point_child_expansion(described, modes, max_tuples=6000,
                                                  max_work=400_000, timeout_s=30)
        results.append(([child.network.edges for child in children],
                        outcome['result'], outcome['direct_oracle_matches']))
    assert results[0] == results[1]
