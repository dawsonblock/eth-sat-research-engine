"""Independent finite replay of actual packet recipes and port loads.

The checked mode certificate supplies the source coefficients. This module
indexes that source independently of the child builder and checks every
constructed packet's local rows, mode exponents, source linear forms, and
creation ring. It checks one supplied tuple, not a universal theorem.
"""
from collections import Counter, defaultdict

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_packing_v26.implicit import real_packet_slots
from veritas.research.eth_recursive_contraction_v39.described_network import CreatedPacketTensor
from .child_partition import verify_constructed_child_partition


def verify_constructed_child_recipes(parent, source, modes, beta, children, ring, *, on_step=None):
    """Check topology, coefficient provenance, creation precision and loads.

    Callers must first validate the packet source and mode certificate. The
    optional callback meters item visits; it is not a bit or memory bound.
    Raises ValueError on any mismatch. The report's load checks describe actual
    constructed half-wires, and make no assertion about existence of a packing.
    """
    def tick():
        if on_step is not None:
            on_step()

    if not isinstance(ring, JetRing):
        raise ValueError('a checked jet ring is required')
    if (ring.base.p != modes['precision'] or
            ring.base.f != first_irreducible(modes['extension_degree'])):
        raise ValueError('child ring differs from the checked mode ring')
    mode_items = modes['modes']
    if (not isinstance(beta, (tuple, list)) or len(beta) != len(mode_items) or
            any(type(value) is not int or value < 0 for value in beta) or
            sum(value * mode['weight'] for value, mode in zip(beta, mode_items)) >= ring.base.p):
        raise ValueError('invalid retained mode tuple')
    node = modes['node']
    if type(node) is not int or node == 0:
        raise ValueError('invalid interpolation node')
    coordinate = (abs(node) & -abs(node)).bit_length() - 1
    verify_constructed_child_partition(parent, source, coordinate, children)

    packet_for_edge = {}
    for packet_id, packet in enumerate(source['packets']):
        for _, edge in real_packet_slots(packet, source['L']):
            tick()
            if edge in packet_for_edge:
                raise ValueError('duplicate packet edge')
            packet_for_edge[edge] = packet_id
    if set(packet_for_edge) != set(range(parent.edges)):
        raise ValueError('packet edge coverage differs from parent')

    row_labels, column_labels, edges = source['row_labels'], source['column_labels'], source['edges']
    row_group = {i: row_labels[str(u)][coordinate] for i, (u, _) in enumerate(edges)}
    col_group = {i: column_labels[str(v)][coordinate] for i, (_, v) in enumerate(edges)}
    local = defaultdict(dict)
    for rid, cid, encoded in modes['local']:
        tick()
        pid = packet_for_edge[rid]
        if packet_for_edge[cid] != pid or row_group[rid] != col_group[cid]:
            raise ValueError('local coefficient crosses packet or group')
        key = (pid, row_group[rid], rid)
        if cid in local[key]:
            raise ValueError('duplicate local mode coefficient')
        local[key][cid] = tuple(tuple(part) for part in encoded)

    target = defaultdict(dict)
    origin = defaultdict(dict)
    for mid, mode in enumerate(mode_items):
        tick()
        pid = mode['packet']
        if type(pid) is not int or not 0 <= pid < len(source['packets']):
            raise ValueError('mode refers to an invalid packet')
        target[(pid, mode['target_group'])][mid] = mode
        origin[(pid, mode['source_group'])][mid] = mode

    rows = []
    for child in children:
        tick()
        group = child.group
        if type(group) is not int or not 0 <= group < source['r']:
            raise ValueError('child group outside radix')
        loads = Counter()
        for vertex in child.network.vertices:
            if vertex.side != 'column':
                continue
            tick()
            tensor = vertex.tensor
            if not isinstance(tensor, CreatedPacketTensor):
                raise ValueError('constructed packet lacks a creation recipe')
            if (tensor.creation_precision != ring.base.p or tensor.defining_polynomial != ring.base.f or
                    tensor.jet_length != ring.length):
                raise ValueError('constructed packet creation ring differs from point ring')
            recipe = tensor.recipe
            pid = recipe.packet_id
            yids = {edge for kind, edge in recipe.variables if kind == 'Y'}
            xids = {edge for kind, edge in recipe.variables if kind == 'X'}
            loads.update(kind for kind, _ in recipe.variables)
            expected_rows = {rid: local.get((pid, group, rid), {}) for rid in yids}
            actual_rows = {rid: dict(terms) for rid, terms in recipe.rows}
            if actual_rows != expected_rows:
                raise ValueError('packet local Cauchy coefficients do not match checked modes')
            expected_targets = {}
            for mid, mode in target[(pid, group)].items():
                tick()
                expected_targets[mid] = (beta[mid], {rid: tuple(tuple(part) for part in encoded)
                                                      for rid, encoded in mode['rows'] if rid in yids})
            actual_targets = {mid: (exponent, dict(entries))
                              for mid, exponent, entries in recipe.target_modes}
            if actual_targets != expected_targets:
                raise ValueError('packet target-mode coefficients or exponents differ from checked modes')
            expected_sources = {}
            for mid, mode in origin[(pid, group)].items():
                tick()
                expected_sources[mid] = (beta[mid], {cid: coefficient
                                                      for cid, coefficient in mode['column_terms'] if cid in xids})
            actual_sources = {mid: (exponent, dict(entries))
                              for mid, exponent, entries in recipe.source_modes}
            if actual_sources != expected_sources:
                raise ValueError('packet source-mode coefficients or exponents differ from checked modes')
        row, column = loads['Y'], loads['X']
        if row + column != child.network.edges:
            raise ValueError('actual half-wire loads differ from child wire count')
        M, radix = parent.edges, source['r']
        rows.append({'group': group, 'row_ports': row, 'column_ports': column,
                     'child_edges': child.network.edges,
                     'row_bound': radix * row <= 3 * M,
                     'column_bound': radix * column <= 3 * M,
                     'child_bound': radix * (row + column) <= 6 * M,
                     'strict_one_eighth': 8 * (row + column) < M})
    if sum(item['child_edges'] for item in rows) != 2 * parent.edges:
        raise ValueError('actual children do not contain both half-edges')
    return {'status': 'FINITE_CHILD_RECIPES_AND_ACTUAL_LOADS_CHECKED', 'groups': rows,
            'all_sides_meet_port_bound': all(x['row_bound'] and x['column_bound'] for x in rows),
            'all_children_meet_six_M_over_r': all(x['child_bound'] for x in rows),
            'all_children_meet_strict_one_eighth': all(x['strict_one_eighth'] for x in rows),
            'uniform_theorem_proven': False}
