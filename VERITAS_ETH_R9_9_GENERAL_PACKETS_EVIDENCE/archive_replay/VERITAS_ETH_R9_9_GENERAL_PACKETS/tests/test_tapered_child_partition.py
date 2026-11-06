from dataclasses import replace

import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_children import build_point_children
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.tensor import from_cnf
from veritas.research.tapered_v4.child_partition import verify_constructed_child_partition
from veritas.research.tapered_v4.child_audit import build_finite_child_size_certificate


def example():
    n = 4
    network = describe_integer_network(from_cnf(CNF.from_lists(n, [[i] for i in range(1, n + 1)])),
                                       creation_precision=5, defining_polynomial=first_irreducible(3))
    source = implicit_mode_source(construct_implicit_packing(network.bipartite_edges(), r=2, a=1))
    modes = make_point_modes(source, node=-1, precision=64, extension_degree=3, zeta=(0, 0, 0))
    children = build_point_children(network, modes, (0,) * len(modes['modes']))
    return network, source, children


def test_child_partition_checks_actual_groups_and_packet_port_mapping():
    parent, source, children = example()
    assert verify_constructed_child_partition(parent, source, 0, children)

    # Changing the group does not change the total number of child edges.
    altered = (replace(children[0], group=9),) + children[1:]
    assert sum(c.network.edges for c in altered) == 2 * parent.edges
    with pytest.raises(ValueError, match='groups'):
        verify_constructed_child_partition(parent, source, 0, altered)

    # Preserve the same graph incidence and edge count while changing which
    # parent half-wires a packet tensor associates with those ports.
    target = next(c for c in children if any(v.side == 'column' and len(v.ports) > 1
                                            for v in c.network.vertices))
    vertex_index = next(i for i, v in enumerate(target.network.vertices)
                        if v.side == 'column' and len(v.ports) > 1)
    vertex = target.network.vertices[vertex_index]
    recipe = vertex.tensor.recipe
    tampered_recipe = replace(recipe, variables=tuple(reversed(recipe.variables)))
    tampered_vertex = replace(vertex, tensor=replace(vertex.tensor, recipe=tampered_recipe))
    vertices = list(target.network.vertices)
    vertices[vertex_index] = tampered_vertex
    tampered_child = replace(target, network=replace(target.network, vertices=tuple(vertices)))
    altered = tuple(tampered_child if c.group == target.group else c for c in children)
    assert sum(c.network.edges for c in altered) == 2 * parent.edges
    with pytest.raises(ValueError, match='half-wire mapping'):
        verify_constructed_child_partition(parent, source, 0, altered)


def test_child_partition_rejects_wrong_coordinate_and_endpoint_graph():
    parent, source, children = example()
    with pytest.raises(ValueError, match='coordinate'):
        verify_constructed_child_partition(parent, source, 1, children)
    changed = dict(source, edges=list(reversed(source['edges'])))
    with pytest.raises(ValueError, match='endpoints'):
        verify_constructed_child_partition(parent, changed, 0, children)


def test_child_audit_preserves_inherited_packet_recipes_at_next_level():
    _, _, first_children = example()
    parent = first_children[0].network
    source = implicit_mode_source(construct_implicit_packing(parent.bipartite_edges(), r=2, a=1))
    modes = make_point_modes(source, node=-1, precision=65, extension_degree=3, zeta=(0, 0, 0))
    beta = (0,) * len(modes['modes'])
    children = build_point_children(parent, modes, beta)
    assert verify_constructed_child_partition(parent, source, 0, children)
    report = build_finite_child_size_certificate(parent, modes, beta)
    assert report['all_parent_half_edges_partitioned_once']
    assert report['sum_child_edges'] == 2 * parent.edges
    assert not report['uniform_shrink_verified']
