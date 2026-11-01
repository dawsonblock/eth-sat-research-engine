"""Sparse, on-demand reference for D.3 packet slots.

Conditional-expectation labeling is the existing bounded implementation. The
representation stores only nonempty classes, never the padded class array.
It does not implement D.4.4 recursion or prove an asymptotic runtime bound.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from itertools import product
from types import MappingProxyType
from .expectation import assign_full_d3_labels, validate_edges, max_side_degree


@dataclass(frozen=True)
class ImplicitPacking:
    edges: tuple
    r: int
    a: int
    H: int
    rows: object
    cols: object
    classes: object
    initial_score: int
    final_score: int
    trace: tuple

    @property
    def L(self):
        return 1 << self.a

    @property
    def D(self):
        return self.r ** (2 * self.a)

    @property
    def packet_count(self):
        return self.D * self.H // self.L

    def packet_slot(self, pairs, index, slot):
        """Read one packet slot without constructing the padded packet."""
        if not isinstance(pairs, (tuple, list)) or len(pairs) != self.a:
            raise ValueError('incorrect pair dimension')
        norm = []
        for pair in pairs:
            if (not isinstance(pair, (tuple, list)) or len(pair) != 2 or
                any(type(x) is not int for x in pair) or
                not 0 <= pair[0] <= pair[1] < self.r):
                raise ValueError('invalid unordered pair')
            norm.append(tuple(pair))
        equal = [d for d, (x, y) in enumerate(norm) if x == y]
        copies = 1 << len(equal)
        if type(index) is not int or not 0 <= index < self.H // copies:
            raise ValueError('packet index outside padded class')
        if type(slot) is not int or not 0 <= slot < self.L:
            raise ValueError('slot outside packet')
        row, col = [], []
        for d, (x, y) in enumerate(norm):
            row.append(y if (slot >> d) & 1 else x)
            col.append(x if (slot >> d) & 1 else y)
        copy = sum(((slot >> d) & 1) << k for k, d in enumerate(equal))
        positions = self.classes.get((tuple(row), tuple(col)), ())
        offset = index * copies + copy
        return positions[offset] if offset < len(positions) else None

    def packet(self, pairs, index, *, max_slots=4096):
        """Read one complete packet subject to a slot budget."""
        if type(max_slots) is not int or max_slots < 1 or self.L > max_slots:
            raise ValueError('packet slot budget exceeded')
        return tuple(self.packet_slot(pairs, index, slot) for slot in range(self.L))

    def iter_packets(self, *, max_packets, max_slots=4096):
        """Stream packets with a caller-supplied total packet limit."""
        if type(max_packets) is not int or max_packets < 0 or self.packet_count > max_packets:
            raise ValueError('packet count exceeds budget')
        choices = tuple((x, y) for x in range(self.r) for y in range(x, self.r))
        for pairs in product(choices, repeat=self.a):
            copies = 1 << sum(x == y for x, y in pairs)
            for index in range(self.H // copies):
                yield pairs, index, self.packet(pairs, index, max_slots=max_slots)


def construct_implicit_packing(edges, *, r=2, a=1, max_work=3_000_000):
    """Assign bounded D.3 labels; retain only real directed classes."""
    edges = validate_edges(edges)
    labels = assign_full_d3_labels(edges, r=r, a=a, max_work=max_work)
    rows = {int(k): tuple(v) for k, v in labels['rows'].items()}
    cols = {int(k): tuple(v) for k, v in labels['columns'].items()}
    buckets = {}
    for i, (row, col) in enumerate(edges):
        buckets.setdefault((rows[row], cols[col]), []).append(i)
    L = 1 << a
    max_load = max((len(x) for x in buckets.values()), default=0)
    H = ((max_load + L - 1) // L) * L
    trace = tuple((step['side'], step['vertex'], step['coordinate'], step['symbol'],
                   step['expected_square_scaled']) for step in labels['steps'])
    return ImplicitPacking(edges, r, a, H, MappingProxyType(rows),
                           MappingProxyType(cols),
                           MappingProxyType({k: tuple(v) for k, v in buckets.items()}),
                           labels['initial_expected_square_scaled'],
                           labels['final_square_scaled'], trace)


def check_implicit_packing(packing, *, max_work=1_000_000):
    """Recompute real class contents and independently locate each edge.

    Counts are finite-instance checks, not a proof of the uniform D.3 lemma.
    The work limit is a coarse edge/coordinate estimate, not a bit-cost or
    operating-system resource limit.
    """
    try:
        if not isinstance(packing, ImplicitPacking):
            raise ValueError('incorrect packing type')
        if type(max_work) is not int or max_work < 0:
            raise ValueError('invalid work budget')
        edges = validate_edges(packing.edges)
        r, a = packing.r, packing.a
        if type(r) is not int or not 2 <= r <= 64 or type(a) is not int or not 1 <= a <= 8:
            raise ValueError('invalid dimensions')
        L, D, M = 1 << a, r ** (2*a), len(edges)
        if M * (4*a + 1) > max_work:
            return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'}
        if set(packing.rows) != {u for u, _ in edges} or set(packing.cols) != {v for _, v in edges}:
            raise ValueError('vertex labels do not match edges')
        for labels in (packing.rows, packing.cols):
            for label in labels.values():
                if len(label) != a or any(type(x) is not int or not 0 <= x < r for x in label):
                    raise ValueError('invalid label')
        expected = {}
        for eid, (u, v) in enumerate(edges):
            expected.setdefault((tuple(packing.rows[u]), tuple(packing.cols[v])), []).append(eid)
        expected = {k: tuple(v) for k, v in expected.items()}
        if dict(packing.classes) != expected:
            raise ValueError('directed classes mismatch')
        H = ((max(map(len, expected.values()), default=0) + L - 1) // L) * L
        if type(packing.H) is not int or packing.H != H:
            raise ValueError('padding mismatch')
        for (row, col), ids in expected.items():
            pairs = tuple((min(x, y), max(x, y)) for x, y in zip(row, col))
            equal = [i for i, (x, y) in enumerate(pairs) if x == y]
            copies = 1 << len(equal)
            for offset, eid in enumerate(ids):
                packet_index, copy = divmod(offset, copies)
                slot = sum((int(row[d] > col[d]) << d) for d in range(a))
                slot |= sum(((copy >> k) & 1) << d for k, d in enumerate(equal))
                if packing.packet_slot(pairs, packet_index, slot) != eid:
                    raise ValueError('edge packet location mismatch')
        delta = max_side_degree(edges)
        phi = D * sum(len(ids)**2 for ids in expected.values()) - M*M
        numeric = M >= 2*D*D*delta and M >= L*D and 2*L <= delta
        ports = Counter((side, d, labels[vertex][d])
                        for u, v in edges
                        for side, labels, vertex in (('row', packing.rows, u),
                                                     ('col', packing.cols, v))
                        for d in range(a))
        max_ports = max(ports.values(), default=0)
        return {'valid': True, 'status': 'FINITE_IMPLICIT_PACKING_CHECKED',
                'edge_count': M, 'nonempty_classes': len(expected),
                'directed_classes': D, 'packet_count': D*H//L,
                'potential_bound': phi <= 2*M*delta*D,
                'packing_count_bound': D*H <= 3*M,
                'symbol_port_bound': max_ports*r <= 3*M,
                'd3_numeric_preconditions': numeric,
                'slot_checks': M, 'universal_theorem_proven': False}
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        return {'valid': False, 'status': 'INVALID_PACKING', 'reason': str(exc)}


def active_packet_view(packing, *, max_work=1_000_000, max_slots=4096):
    """Return the canonical nonempty packets without enumerating empty classes.

    Packet order matches the explicit constructor's lexicographic order, but
    only packets containing at least one edge are retained. The returned view
    is an input adapter for finite geometric-mode experiments; it is not an
    explicit D.3 certificate and carries no asymptotic guarantee.
    """
    checked = check_implicit_packing(packing, max_work=max_work)
    if checked.get('valid') is not True:
        raise ValueError('implicit packing invalid or verification budget exhausted')
    if type(max_slots) is not int or max_slots < 1 or packing.L > max_slots:
        raise ValueError('packet slot budget exceeded')
    packets = {}
    work = 0
    for (row, col), edge_ids in packing.classes.items():
        pairs = tuple((min(x, y), max(x, y)) for x, y in zip(row, col))
        equal = [d for d, (x, y) in enumerate(pairs) if x == y]
        copies = 1 << len(equal)
        for offset, eid in enumerate(edge_ids):
            work += 1
            if work > max_work:
                raise ValueError('active packet construction budget exceeded')
            index, copy = divmod(offset, copies)
            slot = sum((int(row[d] > col[d]) << d) for d in range(packing.a))
            slot |= sum(((copy >> k) & 1) << d for k, d in enumerate(equal))
            key = (pairs, index)
            slots = packets.setdefault(key, [None] * packing.L)
            if slots[slot] is not None:
                raise ValueError('two edges map to one packet slot')
            slots[slot] = eid
    ordered = sorted(packets.items())
    return tuple({'symbol_pairs': [list(pair) for pair in pairs],
                  'index': index, 'slots': slots}
                 for (pairs, index), slots in ordered)


def implicit_mode_source(packing, *, max_work=1_000_000, max_slots=4096):
    """Serialize immutable labels plus occupied packets for mode generation."""
    packets = active_packet_view(packing, max_work=max_work, max_slots=max_slots)
    return {
        'schema': 'VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1',
        'claim': 'FINITE_NONEMPTY_PACKET_VIEW',
        'r': packing.r, 'a': packing.a, 'L': packing.L, 'D': packing.D,
        'M': len(packing.edges), 'H_pad': packing.H,
        'edges': [list(edge) for edge in packing.edges],
        'row_labels': {str(k): list(v) for k, v in packing.rows.items()},
        'column_labels': {str(k): list(v) for k, v in packing.cols.items()},
        'packets': list(packets),
        'initial_expected_square_scaled': packing.initial_score,
        'final_square_scaled': packing.final_score,
        'conditional_expectation_trace': [list(step) for step in packing.trace],
    }


def check_implicit_mode_source(source, *, max_work=1_000_000, max_slots=4096):
    """Replay the constructor and check the complete sparse packet view."""
    try:
        if not isinstance(source, dict) or source.get('schema') != 'VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1' or source.get('claim') != 'FINITE_NONEMPTY_PACKET_VIEW':
            raise ValueError('unsupported implicit packet source')
        edges = validate_edges(source['edges'])
        rebuilt = construct_implicit_packing(edges, r=source['r'], a=source['a'],
                                              max_work=max_work)
        expected = implicit_mode_source(rebuilt, max_work=max_work,
                                        max_slots=max_slots)
        # Compare only canonical fields; caller-supplied extra keys are rejected.
        if source != expected:
            raise ValueError('implicit labels, trace, padding, or occupied slots differ from replay')
        if len(source['packets']) > len(edges):
            raise ValueError('active packet count exceeds edge count')
        return {'valid': True, 'status': 'FINITE_IMPLICIT_MODE_SOURCE_VERIFIED',
                'edge_count': len(edges), 'active_packet_count': len(source['packets']),
                'all_classes_materialized': False, 'universal_theorem_proven': False}
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        return {'valid': False, 'status': 'INVALID_IMPLICIT_MODE_SOURCE', 'reason': str(exc)}


def materialize_finite_certificate(packing, *, max_packets=10_000,
                                   max_slots=32, max_work=1_000_000):
    """Bridge a bounded implicit packing to the existing v26 certificate.

    Explicit output is deliberately limited to the independent checker's
    finite domain. This is not a scalable recursive child representation.
    """
    from .constructor import d3_preconditions
    from .checker import verify_d3_packing

    checked = check_implicit_packing(packing, max_work=max_work)
    if checked.get('valid') is not True:
        raise ValueError('implicit packing invalid or verification budget exhausted')
    if (type(max_packets) is not int or max_packets < 0 or
            type(max_slots) is not int or max_slots < 1):
        raise ValueError('invalid materialization budget')
    if (packing.a > 5 or packing.D > 4096 or len(packing.edges) > 4000 or
            packing.L > max_slots or packing.packet_count > min(max_packets, 10000)):
        raise ValueError('finite certificate materialization budget exceeded')
    steps = [{'side': side, 'vertex': vertex, 'coordinate': coord,
              'symbol': symbol, 'expected_square_scaled': score}
             for side, vertex, coord, symbol, score in packing.trace]
    certificate = {
        'schema': 'VERITAS_ETH_D3_CERT_V1', 'claim': 'FINITE_D3_PACKET_CONSTRUCTION',
        'r': packing.r, 'a': packing.a, 'L': packing.L, 'D': packing.D,
        'M': len(packing.edges), 'H_pad': packing.H,
        'delta': max_side_degree(packing.edges),
        'edges': [list(edge) for edge in packing.edges],
        'row_labels': {str(k): list(v) for k, v in packing.rows.items()},
        'column_labels': {str(k): list(v) for k, v in packing.cols.items()},
        'packets': [{'symbol_pairs': [list(pair) for pair in pairs], 'slots': list(slots)}
                    for pairs, _, slots in packing.iter_packets(
                        max_packets=max_packets, max_slots=max_slots)],
        'initial_expected_square_scaled': packing.initial_score,
        'final_square_scaled': packing.final_score,
        'hypotheses': d3_preconditions(len(packing.edges), packing.r, packing.a,
                                       max_side_degree(packing.edges)),
        'conditional_expectation_steps': steps,
    }
    result = verify_d3_packing(certificate, check_trace=True)
    if not result['valid']:
        raise ValueError('finite certificate verification failed: ' + result['reason'])
    certificate['verification'] = result
    return certificate
