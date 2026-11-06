"""Finite structural accounting for packet-to-child wire counts.

The audit checks one supplied finite packing, interpolation point, and mode
tuple. It is not a theorem that the asymptotic schedule's hypotheses hold.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from math import gcd

from veritas.research.eth_packing_v26.implicit import (
    check_implicit_mode_source, check_implicit_packing,
    construct_implicit_packing,
)
from veritas.research.eth_packing_v26.expectation import max_side_degree
from veritas.research.eth_recursive_contraction_v39.described_network import CreatedPacketTensor
from veritas.research.eth_recursive_contraction_v39.point_children import (
    _build_point_children_checked, _ring_for,
)

from .certificates import canonical


SCHEMA = 'VERITAS_FINITE_CHILD_SIZE_AUDIT_V1'


def _fraction(numerator: int, denominator: int) -> dict:
    common = gcd(numerator, denominator) if denominator else 1
    return {'numerator': numerator // common,
            'denominator': denominator // common,
            'decimal': numerator / denominator if denominator else None}


def _expected_groups(parent, source, coordinate):
    edges = tuple(tuple(edge) for edge in source['edges'])
    row_labels = source['row_labels']
    column_labels = source['column_labels']
    row_group = tuple(row_labels[str(u)][coordinate] for u, _ in edges)
    column_group = tuple(column_labels[str(v)][coordinate] for _, v in edges)
    by_side = {side: tuple(v for v in parent.vertices if v.side == side)
               for side in ('row', 'column')}
    vertex_groups = {}
    for side, labels in (('row', row_labels), ('column', column_labels)):
        for index, _vertex in enumerate(by_side[side]):
            vertex_groups[(side, index)] = labels.get(str(index), [0] * source['a'])[coordinate]
    groups = sorted(set(row_group) | set(column_group) | set(vertex_groups.values()))
    variables = {}
    for group in groups:
        variables[group] = tuple(
            [('Y', e) for e, label in enumerate(row_group) if label == group] +
            [('X', e) for e, label in enumerate(column_group) if label == group])
    return edges, row_group, column_group, by_side, vertex_groups, groups, variables


def build_finite_child_size_certificate(parent, mode_certificate, beta):
    """Rebuild children and certify their finite wire/port accounting.

    Each parent edge contributes two half-edge variables, Y_e and X_e. The
    packet tensors add factor vertices and incidences on those variables; they
    do not add further Boolean wire variables in this representation.
    """
    ring, source = _ring_for(parent, mode_certificate, max_parent_wires=8)
    packing = construct_implicit_packing(source['edges'], r=source['r'], a=source['a'])
    packing_check = check_implicit_packing(packing)
    source_check = check_implicit_mode_source(source)
    if source_check.get('valid') is not True or packing_check.get('valid') is not True:
        raise ValueError('finite packet source did not independently replay')

    coordinate = (abs(mode_certificate['node']) & -abs(mode_certificate['node'])).bit_length() - 1
    delta = max_side_degree(source['edges'])
    D, L, M, H = source['D'], source['L'], parent.edges, source['H_pad']
    finite_hypotheses = {
        'M': M, 'delta': delta, 'r': source['r'], 'a': source['a'],
        'L': L, 'D': D, 'H': H,
        'M_at_least_2_D_squared_delta': {
            'left': M, 'right': 2 * D * D * delta,
            'holds': M >= 2 * D * D * delta,
        },
        'M_at_least_L_D': {
            'left': M, 'right': L * D, 'holds': M >= L * D,
        },
        '2_L_at_most_delta': {
            'left': 2 * L, 'right': delta, 'holds': 2 * L <= delta,
        },
        'D_H_at_most_3_M': {
            'left': D * H, 'right': 3 * M, 'holds': D * H <= 3 * M,
        },
    }
    finite_hypotheses['all_reported_conditions_hold'] = all(
        item['holds'] for key, item in finite_hypotheses.items()
        if isinstance(item, dict) and 'holds' in item)
    edges, row_group, column_group, side_vertices, vertex_groups, groups, variables = (
        _expected_groups(parent, source, coordinate))
    row_symbol_loads = Counter(row_group)
    column_symbol_loads = Counter(column_group)
    per_side_bound_holds = all(
        source['r'] * load <= 3 * parent.edges
        for load in (*row_symbol_loads.values(), *column_symbol_loads.values()))
    children = _build_point_children_checked(parent, mode_certificate, beta, ring, source)
    child_by_group = {child.group: child for child in children}
    if tuple(sorted(child_by_group)) != tuple(groups):
        raise ValueError('child groups differ from independently reconstructed groups')

    rows = []
    all_wire_ids = Counter()
    for group in groups:
        child = child_by_group[group]
        expected_variables = variables[group]
        all_wire_ids.update(expected_variables)
        network = child.network
        if network.edges != len(expected_variables):
            raise ValueError('child edge count differs from its row/column half-edge variables')
        variable_to_port = {variable: index for index, variable in enumerate(expected_variables)}

        # Inherited factors can themselves contain packet recipes from an
        # earlier recursion level. The builder puts all inherited factors on
        # the row side and newly introduced packet factors on the column side.
        inherited_vertices = [vertex for vertex in network.vertices if vertex.side == 'row']
        packet_vertices = [vertex for vertex in network.vertices if vertex.side == 'column']
        if any(not isinstance(vertex.tensor, CreatedPacketTensor) for vertex in packet_vertices):
            raise ValueError('introduced packet factor lacks a packet recipe')
        packet_variables = Counter(variable for vertex in packet_vertices
                                   for variable in vertex.tensor.recipe.variables)
        if packet_variables != Counter(expected_variables):
            raise ValueError('packet factors do not cover each child wire exactly once')

        expected_inherited_specs = []
        inherited_port_map = []
        for side in ('row', 'column'):
            kind = 'Y' if side == 'row' else 'X'
            for index, parent_vertex in enumerate(side_vertices[side]):
                if vertex_groups[(side, index)] != group:
                    continue
                local_ports = tuple(variable_to_port[(kind, edge)]
                                    for edge in parent_vertex.ports)
                expected_inherited_specs.append((f'{side}:{index}:{parent_vertex.label}',
                                                 local_ports, parent_vertex.tensor))
                for source_port, edge in enumerate(parent_vertex.ports):
                    inherited_port_map.append({
                        'wire': [kind, edge],
                        'parent_edge_endpoints': list(edges[edge]),
                        'parent_vertex_side': side,
                        'parent_vertex_index': index,
                        'parent_vertex_label': parent_vertex.label,
                        'parent_vertex_port': source_port,
                        'child_wire_port': variable_to_port[(kind, edge)],
                    })
        if len(inherited_vertices) != len(expected_inherited_specs):
            raise ValueError('child inherited factor count differs from parent grouping')
        for actual, (expected_label, expected_ports, expected_tensor) in zip(
                inherited_vertices, expected_inherited_specs):
            if (actual.side != 'row' or actual.label != expected_label or
                    actual.ports != expected_ports or actual.tensor != expected_tensor):
                raise ValueError('child inherited factor ports differ from their parent factors')
        if Counter(tuple(item['wire']) for item in inherited_port_map) != Counter(expected_variables):
            raise ValueError('inherited factors do not cover each child wire exactly once')

        packet_port_map = []
        for vertex in packet_vertices:
            recipe = vertex.tensor.recipe
            if len(recipe.variables) != len(vertex.ports):
                raise ValueError('packet recipe variables differ from packet factor ports')
            for packet_port, (variable, child_wire_port) in enumerate(
                    zip(recipe.variables, vertex.ports)):
                if (variable not in variable_to_port or
                        child_wire_port != variable_to_port[variable]):
                    raise ValueError('packet factor port is not attached to its declared half-wire')
                packet_port_map.append({
                    'wire': list(variable), 'packet_id': recipe.packet_id,
                    'packet_factor_label': vertex.label, 'packet_port': packet_port,
                    'child_wire_port': child_wire_port,
                })

        row_ports = sum(len(vertex.ports) for vertex in network.vertices
                        if vertex.side == 'row')
        column_ports = sum(len(vertex.ports) for vertex in network.vertices
                           if vertex.side == 'column')
        packet_ports = sum(len(vertex.ports) for vertex in packet_vertices)
        inherited_ports = sum(len(vertex.ports) for vertex in inherited_vertices)
        if (row_ports != network.edges or column_ports != network.edges or
                packet_ports != network.edges or inherited_ports != network.edges):
            raise ValueError('child wire incidence does not have one inherited and one packet endpoint')

        row_half_edges = sum(label == group for label in row_group)
        column_half_edges = sum(label == group for label in column_group)
        if network.edges != row_half_edges + column_half_edges:
            raise ValueError('child edge count is not the sum of its two half-edge loads')
        rows.append({
            'group': group,
            'row_half_edge_count': row_half_edges,
            'column_half_edge_count': column_half_edges,
            'child_edges': network.edges,
            'shrink_ratio': _fraction(network.edges, parent.edges),
            'target_ratio': {'numerator': 1, 'denominator': 8, 'relation': '<'},
            'meets_strict_one_eighth': 8 * network.edges < parent.edges,
            'theorem_target_ratio': {'numerator': 3, 'denominator': 32,
                                     'relation': '<='},
            'meets_three_over_32': 32 * network.edges <= 3 * parent.edges,
            'meets_finite_six_M_over_r': source['r'] * network.edges <= 6 * parent.edges,
            'inherited_factor_vertices': len(inherited_vertices),
            'inherited_factor_ports': inherited_ports,
            'introduced_packet_factor_vertices': len(packet_vertices),
            'introduced_packet_factor_ports': packet_ports,
            'introduced_boolean_wire_edges': 0,
            'total_factor_incidence_ports': row_ports + column_ports,
            'incidence_check': 'one inherited and one packet endpoint per Boolean wire',
            'inherited_port_map': inherited_port_map,
            'packet_port_map': packet_port_map,
            'wire_ids': [[kind, edge_id] for kind, edge_id in expected_variables],
        })

    expected_wire_ids = Counter([('Y', e) for e in range(parent.edges)] +
                                 [('X', e) for e in range(parent.edges)])
    if all_wire_ids != expected_wire_ids:
        raise ValueError('children do not partition all parent half-edge variables exactly once')
    if sum(row['child_edges'] for row in rows) != 2 * parent.edges:
        raise ValueError('sum of child wire counts must equal two parent half-edge sets')

    maximal = max(rows, key=lambda row: (row['child_edges'], -row['group']))
    failed_conditions = []
    for name in ('d3_numeric_preconditions', 'packing_count_bound', 'symbol_port_bound'):
        if packing_check.get(name) is not True:
            failed_conditions.append(name)
    audit = {
        'schema': SCHEMA,
        'claim': 'FINITE_CHILD_WIRE_ACCOUNTING_ONLY',
        'parent_topology_sha256': sha256(canonical({
            'edges': parent.edges,
            'bipartite_edges': [list(edge) for edge in parent.bipartite_edges()],
        })).hexdigest(),
        'mode_certificate_sha256': sha256(canonical(mode_certificate)).hexdigest(),
        'node': mode_certificate['node'],
        'zeta': mode_certificate['zeta'],
        'beta': list(beta),
        'finite_parameters': {'a': source['a'], 'r': source['r'], 'L': source['L'],
                              'directed_classes': source['D']},
        'finite_hypothesis_arithmetic': finite_hypotheses,
        'coordinate_symbol_loads': {
            'coordinate': coordinate,
            'row': [{'symbol': symbol, 'load': row_symbol_loads.get(symbol, 0)}
                    for symbol in range(source['r'])],
            'column': [{'symbol': symbol, 'load': column_symbol_loads.get(symbol, 0)}
                       for symbol in range(source['r'])],
            'per_side_bound': {'numerator': 3 * parent.edges,
                               'denominator': source['r'],
                               'relation': '<='},
            'all_sides_meet_per_side_bound': per_side_bound_holds,
        },
        'parent_edges': parent.edges,
        'child_edges': maximal['child_edges'],
        'witness_group': maximal['group'],
        'shrink_ratio': maximal['shrink_ratio'],
        'target_ratio': maximal['target_ratio'],
        'theorem_target_ratio': maximal['theorem_target_ratio'],
        'children': rows,
        'child_count': len(rows),
        'sum_child_edges': sum(row['child_edges'] for row in rows),
        'expected_sum_child_edges': 2 * parent.edges,
        'introduced_packet_factor_vertices': sum(
            row['introduced_packet_factor_vertices'] for row in rows),
        'introduced_packet_factor_ports': sum(
            row['introduced_packet_factor_ports'] for row in rows),
        'introduced_boolean_wire_edges': 0,
        'all_parent_half_edges_partitioned_once': True,
        'all_children_meet_finite_six_M_over_r': all(
            row['meets_finite_six_M_over_r'] for row in rows),
        'all_children_meet_strict_one_eighth': all(
            row['meets_strict_one_eighth'] for row in rows),
        'all_children_meet_three_over_32': all(
            row['meets_three_over_32'] for row in rows),
        'finite_packing_checks': packing_check,
        'failed_finite_packing_conditions': failed_conditions,
        'theorem_schedule_implemented': False,
        'theorem_premises_verified': False,
        'uniform_shrink_verified': False,
        'coverage': 'one finite packing, one interpolation point, one mode tuple',
        'conditional_size_lemma': (
            'If each side-symbol load is at most 3M/r, then each child has '
            'at most 6M/r wires because it contains one row and one column half-edge per load.'),
        'result': 'FINITE_EXPERIMENT_ONLY',
    }
    return audit


def check_finite_child_size_certificate(parent, mode_certificate, beta, certificate):
    """Recompute a finite audit and reject altered counts or theorem claims."""
    if type(certificate) is not dict:
        return {'valid': False, 'status': 'INVALID_CHILD_SIZE_CERTIFICATE'}
    try:
        expected = build_finite_child_size_certificate(parent, mode_certificate, beta)
        valid = canonical(certificate) == canonical(expected)
    except (TypeError, ValueError, KeyError, IndexError, ArithmeticError,
            AttributeError, ZeroDivisionError):
        valid = False
    return {'valid': valid,
            'status': 'FINITE_CHILD_SIZE_AUDIT_REPLAYED' if valid else 'INVALID_CHILD_SIZE_CERTIFICATE',
            'theorem_premises_verified': False,
            'uniform_shrink_verified': False,
            'independent_theorem_proof': False}
