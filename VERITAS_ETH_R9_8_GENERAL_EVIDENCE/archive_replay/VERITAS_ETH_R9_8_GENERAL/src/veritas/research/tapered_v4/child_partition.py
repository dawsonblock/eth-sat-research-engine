"""Replay the finite child half-wire partition from the checked parent source.

This checks topology, not packet coefficients, the parent/children contraction
identity, or uniform applicability of the manuscript's packing lemma.
"""
from collections import Counter

from veritas.research.eth_packing_v26.implicit import real_packet_slots
from veritas.research.eth_recursive_contraction_v39.described_network import CreatedPacketTensor


def verify_constructed_child_partition(parent, source, coordinate, children):
    """Raise ValueError unless every actual child has its prescribed ports.

    The caller must separately validate the packet source. Group labels and
    actual child incidence are replayed here without invoking the child builder.
    """
    if [list(edge) for edge in parent.bipartite_edges()] != source['edges']:
        raise ValueError('packet endpoints differ from parent topology')
    if type(coordinate) is not int or not 0 <= coordinate < source['a']:
        raise ValueError('packet grouping coordinate is invalid')
    edges = source['edges']
    side_vertices = {side: tuple(v for v in parent.vertices if v.side == side)
                     for side in ('row', 'column')}
    labels = {'row': source['row_labels'], 'column': source['column_labels']}
    vertex_groups = {
        (side, i): labels[side].get(str(i), [0] * source['a'])[coordinate]
        for side in ('row', 'column') for i in range(len(side_vertices[side]))
    }
    row_groups = tuple(labels['row'][str(u)][coordinate] for u, _ in edges)
    column_groups = tuple(labels['column'][str(v)][coordinate] for _, v in edges)
    expected_groups = set(row_groups) | set(column_groups) | set(vertex_groups.values())
    if len({child.group for child in children}) != len(children):
        raise ValueError('duplicate child group')
    if {child.group for child in children} != expected_groups:
        raise ValueError('child groups do not match the parent grouping')

    # Build a separate lookup of each packet's real edge membership. The
    # packet source verifier, run by the caller, checks slot uniqueness.
    packet_edges = [tuple(eid for _, eid in real_packet_slots(packet, source['L']))
                    for packet in source['packets']]
    if Counter(e for packet in packet_edges for e in packet) != Counter(range(parent.edges)):
        raise ValueError('packet slots do not partition parent edges')

    for child in children:
        group = child.group
        variables = tuple([('Y', i) for i, g in enumerate(row_groups) if g == group] +
                          [('X', i) for i, g in enumerate(column_groups) if g == group])
        if child.network.edges != len(variables):
            raise ValueError('child wire count differs from group half-wire count')
        ports = {variable: index for index, variable in enumerate(variables)}
        expected_inherited = []
        for side, kind in (('row', 'Y'), ('column', 'X')):
            for index, vertex in enumerate(side_vertices[side]):
                if vertex_groups[(side, index)] == group:
                    expected_inherited.append((f'{side}:{index}:{vertex.label}',
                                               tuple(ports[(kind, e)] for e in vertex.ports),
                                               vertex.tensor))
        # All inherited factors are on the row side even when their immutable
        # tensor is itself a packet recipe from a previous recursion level.
        inherited = [v for v in child.network.vertices if v.side == 'row']
        if len(inherited) != len(expected_inherited):
            raise ValueError('child inherited factors differ from parent grouping')
        for actual, (label, expected_ports, tensor) in zip(inherited, expected_inherited):
            if (actual.side, actual.label, actual.ports, actual.tensor) != ('row', label, expected_ports, tensor):
                raise ValueError('child inherited factor or port mapping differs from parent')
        expected_packets = {}
        for packet_id, packet in enumerate(packet_edges):
            packet_variables = tuple([('Y', e) for e in packet if row_groups[e] == group] +
                                     [('X', e) for e in packet if column_groups[e] == group])
            if packet_variables:
                expected_packets[packet_id] = packet_variables
        actual_packets = [v for v in child.network.vertices if v.side == 'column']
        if len(actual_packets) != len(expected_packets):
            raise ValueError('child packet factors differ from occupied packet groups')
        for vertex in actual_packets:
            if not isinstance(vertex.tensor, CreatedPacketTensor):
                raise ValueError('child packet factor lacks a packet recipe')
            recipe = vertex.tensor.recipe
            variables_here = expected_packets.pop(recipe.packet_id, None)
            if (variables_here is None or recipe.variables != variables_here or
                    vertex.side != 'column' or
                    vertex.label != f'packet:{recipe.packet_id}' or
                    vertex.ports != tuple(ports[v] for v in variables_here) or
                    recipe.ports != vertex.ports):
                raise ValueError('child packet factor or half-wire mapping differs from slots')
        if expected_packets:
            raise ValueError('a required child packet factor is absent')
    return True
