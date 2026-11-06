"""Independent finite audit of labeled sparse packet geometry and group loads.

This accepts any explicit labeling and packet placement satisfying the
stated geometric conditions. It does not replay conditional expectation,
certify a contraction identity, or prove that a suitable labeling exists.
"""
from collections import Counter

from .expectation import max_side_degree, validate_edges
from .implicit import SPARSE_MODE_SCHEMA, real_packet_slots


def audit_sparse_packet_geometry(source, *, max_work=1_000_000):
    """Audit one sparse source, including every coordinate's child loads.

    Work is guarded by a coarse count of source items and coordinate visits,
    not by a hard deadline, bit-operation bound, or memory cap. No
    deterministic-labeling trace or tensor coefficients are checked.
    """
    if type(max_work) is not int or max_work < 1:
        raise ValueError('positive integer work budget required')
    try:
        if not isinstance(source, dict) or source.get('schema') != SPARSE_MODE_SCHEMA:
            raise ValueError('sparse packet source required')
        if source.get('claim') != 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS':
            raise ValueError('invalid sparse packet claim')
        r, a, H = source['r'], source['a'], source['H_pad']
        if (type(r) is not int or not 2 <= r <= 64 or
                type(a) is not int or not 1 <= a <= 64 or
                type(H) is not int or H < 0 or H.bit_length() > 4096):
            raise ValueError('invalid packet dimensions or padding')
        L, D = 1 << a, r ** (2 * a)
        if (type(source['L']) is not int or type(source['D']) is not int or
                source['L'] != L or source['D'] != D or H % L):
            raise ValueError('inconsistent packet dimensions or padding')
        raw_edges, packets = source['edges'], source['packets']
        if not isinstance(raw_edges, (list, tuple)) or not isinstance(packets, (list, tuple)):
            raise ValueError('explicit edges and occupied packets required')
        M = len(raw_edges)
        if type(source['M']) is not int or source['M'] != M or len(packets) > M:
            raise ValueError('incorrect edge or occupied packet count')
        if (M + len(packets)) * (a + 1) + a * r > max_work:
            return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'}
        edges = validate_edges(raw_edges)
        labels = {}
        for side, index, field in (('row', 0, 'row_labels'),
                                   ('column', 1, 'column_labels')):
            data = source[field]
            expected = {str(edge[index]) for edge in edges}
            if not isinstance(data, dict) or set(data) != expected:
                raise ValueError('labels do not match graph vertices')
            if any(not isinstance(word, (tuple, list)) or len(word) != a or
                   any(type(symbol) is not int or not 0 <= symbol < r for symbol in word)
                   for word in data.values()):
                raise ValueError('invalid vertex label')
            labels[side] = data

        classes = Counter((tuple(labels['row'][str(u)]), tuple(labels['column'][str(v)]))
                          for u, v in edges)
        if max(classes.values(), default=0) > H:
            raise ValueError('padding is smaller than a real class')
        seen_packets, seen_edges = set(), set()
        for packet in packets:
            pairs = packet['symbol_pairs']
            if (not isinstance(pairs, (list, tuple)) or len(pairs) != a or
                    any(not isinstance(pair, (list, tuple)) or len(pair) != 2 or
                        any(type(x) is not int for x in pair) or
                        not 0 <= pair[0] <= pair[1] < r for pair in pairs)):
                raise ValueError('invalid unordered symbol pairs')
            pairs = tuple(tuple(pair) for pair in pairs)
            equal_coordinates = sum(x == y for x, y in pairs)
            index = packet['index']
            if type(index) is not int or not 0 <= index < H // (1 << equal_coordinates):
                raise ValueError('packet index outside padded classes')
            key = (pairs, index)
            if key in seen_packets:
                raise ValueError('duplicate packet address')
            seen_packets.add(key)
            if len(packet['occupied_slots']) > M:
                raise ValueError('too many packet entries')
            occupied = real_packet_slots(packet, L)
            if not occupied:
                raise ValueError('sparse packet must contain a real edge')
            for slot, eid in occupied:
                if eid >= M or eid in seen_edges:
                    raise ValueError('duplicate or invalid real edge')
                seen_edges.add(eid)
                u, v = edges[eid]
                row, col = labels['row'][str(u)], labels['column'][str(v)]
                for d, (low, high) in enumerate(pairs):
                    expected_row, expected_col = ((high, low) if (slot >> d) & 1
                                                   else (low, high))
                    if row[d] != expected_row or col[d] != expected_col:
                        raise ValueError('packet orientation does not match vertex labels')
        if len(seen_edges) != M:
            raise ValueError('packet slots omit real edges')

        coordinates = []
        for d in range(a):
            rows = Counter(labels['row'][str(u)][d] for u, _ in edges)
            columns = Counter(labels['column'][str(v)][d] for _, v in edges)
            groups = []
            for group in range(r):
                row, col = rows[group], columns[group]
                groups.append({'group': group, 'row_ports': row, 'column_ports': col,
                               'predicted_child_wires': row + col,
                               'meets_six_M_over_r': r * (row + col) <= 6 * M,
                               'meets_three_M_over_32': r == 64 and 32 * (row + col) <= 3 * M})
            side_bound = all(r * count <= 3 * M for count in (*rows.values(), *columns.values()))
            child_bound = all(item['meets_six_M_over_r'] for item in groups)
            coordinates.append({'coordinate': d, 'per_side_port_bound': side_bound,
                                'per_child_six_M_over_r': child_bound, 'groups': groups})

        delta = max_side_degree(edges)
        return {'valid': True, 'status': 'FINITE_PACKET_GEOMETRY_AND_LOADS_CHECKED',
                'parent_edges': M, 'actual_maximum_degree': delta, 'radix': r,
                'coordinate_count': a, 'active_packets': len(packets),
                'padded_packet_count': D * H // L,
                'packing_numeric_conditions_with_actual_degree': (
                    M >= 2 * D * D * delta and M >= L * D and 2 * L <= delta),
                'packing_count_bound': D * H <= 3 * M,
                'coordinates': coordinates,
                'deterministic_trace_verified': False,
                'constructed_children_verified': False,
                'contraction_identity_verified': False,
                'uniform_theorem_proven': False}
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError) as exc:
        return {'valid': False, 'status': 'INVALID_PACKET_GEOMETRY', 'reason': str(exc)}
