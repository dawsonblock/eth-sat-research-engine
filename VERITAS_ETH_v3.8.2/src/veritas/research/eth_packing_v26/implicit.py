"""Sparse, on-demand packet representation and finite replay checks.

Paper object: `lem:tensor-packets` in `app:tensor` (historical alias "D.3").

The implicit representation stores only nonempty directed classes. Its sparse
mode source stores only occupied packet slots, even when ``L`` is large. The
exact conditional-expectation constructor accepts arbitrary positive packet
exponents subject to an optional operation estimate. These are executable
finite constructions; they do not implement D.4.4 recursion or prove an
asymptotic runtime bound.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from itertools import product
from types import MappingProxyType
from .expectation import (DEFAULT_MAX_PAIR_RECORDS, assign_full_d3_labels,
                          conditional_expectation_work_bound, validate_edges,
                          max_side_degree, PackingBudgetExceeded)


SPARSE_MODE_SCHEMA = 'VERITAS_ETH_D3_IMPLICIT_SPARSE_ACTIVE_V1'


def _work_budget_valid(max_work, *, allow_zero=False):
    return (max_work is None or
            (type(max_work) is int and max_work >= (0 if allow_zero else 1)))


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


def construct_implicit_packing(edges, *, r=2, a=1, max_work=3_000_000, _budget=None,
                               max_pair_records=DEFAULT_MAX_PAIR_RECORDS):
    """Construct D.3 labels while retaining only nonempty directed classes.

    ``max_work=None`` removes the experimental operation estimate. It does not
    assert a runtime theorem; it asks the caller to run the exact finite
    derandomizer to completion.
    """
    edges = validate_edges(edges)
    if not _work_budget_valid(max_work):
        raise ValueError('max_work must be a positive integer or None')
    labels = assign_full_d3_labels(edges, r=r, a=a, max_work=max_work, _budget=_budget,
                                    max_pair_records=max_pair_records)
    rows = {int(k): tuple(v) for k, v in labels['rows'].items()}
    cols = {int(k): tuple(v) for k, v in labels['columns'].items()}
    buckets = {}
    for i, (row, col) in enumerate(edges):
        if _budget is not None:
            _budget.tick()
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


def check_implicit_packing(packing, *, max_work=1_000_000, check_trace=False,
                           max_pair_records=DEFAULT_MAX_PAIR_RECORDS):
    """Recompute real class contents and independently locate each edge.

    Counts are finite-instance checks, not a proof of the uniform D.3 lemma.
    The work limit is a coarse edge/coordinate estimate, not a bit-cost or
    operating-system resource limit.
    """
    try:
        if not isinstance(packing, ImplicitPacking):
            raise ValueError('incorrect packing type')
        if not _work_budget_valid(max_work, allow_zero=True):
            raise ValueError('invalid work budget')
        if type(check_trace) is not bool:
            raise ValueError('check_trace must be Boolean')
        edges = validate_edges(packing.edges)
        r, a = packing.r, packing.a
        if type(r) is not int or not 2 <= r <= 64 or type(a) is not int or a < 1:
            raise ValueError('invalid dimensions')
        M = len(edges)
        coarse_check_work = M * (4*a + 1)
        trace_work = conditional_expectation_work_bound(edges, r=r, a=a) if check_trace else 0
        if max_work is not None and max(coarse_check_work, trace_work) > max_work:
            return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'}
        L, D = 1 << a, r ** (2*a)
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
        final_score = phi + M*M
        if type(packing.final_score) is not int or packing.final_score != final_score:
            raise ValueError('final conditional-expectation score differs from class loads')
        trace_verified = False
        if check_trace:
            replay = assign_full_d3_labels(edges, r=r, a=a, max_work=max_work,
                                            max_pair_records=max_pair_records)
            replay_rows = {int(k): tuple(v) for k, v in replay['rows'].items()}
            replay_cols = {int(k): tuple(v) for k, v in replay['columns'].items()}
            replay_trace = tuple((step['side'], step['vertex'], step['coordinate'],
                                  step['symbol'], step['expected_square_scaled'])
                                 for step in replay['steps'])
            if (dict(packing.rows) != replay_rows or dict(packing.cols) != replay_cols or
                    packing.initial_score != replay['initial_expected_square_scaled'] or
                    packing.final_score != replay['final_square_scaled'] or
                    packing.trace != replay_trace):
                raise ValueError('conditional-expectation labeling trace differs from deterministic replay')
            trace_verified = True
        return {'valid': True, 'status': 'FINITE_IMPLICIT_PACKING_CHECKED',
                'edge_count': M, 'nonempty_classes': len(expected),
                'directed_classes': D, 'packet_count': D*H//L,
                'potential_bound': phi <= 2*M*delta*D,
                'packing_count_bound': D*H <= 3*M,
                'symbol_port_bound': max_ports*r <= 3*M,
                'd3_numeric_preconditions': numeric,
                'max_side_symbol_load': max_ports,
                'slot_checks': M, 'conditional_expectation_trace_verified': trace_verified,
                'universal_theorem_proven': False}
    except PackingBudgetExceeded:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT'}
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
    if checked.get('status') == 'INCONCLUSIVE_RESOURCE_LIMIT':
        raise PackingBudgetExceeded('implicit packing verification budget exhausted')
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
            if max_work is not None and work > max_work:
                raise PackingBudgetExceeded('active packet construction budget exceeded')
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


def sparse_active_packet_view(packing, *, max_work=1_000_000):
    """Stream-ready occupied slots only; memory is O(number of real edges).

    Unlike ``active_packet_view``, this does not allocate ``L`` slots for an
    occupied packet. Packet indices and orientation are still the canonical
    D.3 ones, so consumers may request a single slot by its integer index.
    """
    checked = check_implicit_packing(packing, max_work=max_work)
    if checked.get('status') == 'INCONCLUSIVE_RESOURCE_LIMIT':
        raise PackingBudgetExceeded('implicit packing verification budget exhausted')
    if checked.get('valid') is not True:
        raise ValueError('implicit packing invalid or verification budget exhausted')
    if not _work_budget_valid(max_work, allow_zero=True):
        raise ValueError('invalid work budget')
    packet_slots = {}
    work = 0
    for (row, col), edge_ids in packing.classes.items():
        pairs = tuple((min(x, y), max(x, y)) for x, y in zip(row, col))
        equal = [d for d, (x, y) in enumerate(pairs) if x == y]
        copies = 1 << len(equal)
        orientation = sum((int(row[d] > col[d]) << d) for d in range(packing.a))
        for offset, eid in enumerate(edge_ids):
            work += 1
            if max_work is not None and work > max_work:
                raise PackingBudgetExceeded('sparse active packet construction budget exceeded')
            index, copy = divmod(offset, copies)
            slot = orientation | sum(((copy >> k) & 1) << d
                                     for k, d in enumerate(equal))
            packet_slots.setdefault((pairs, index), []).append((slot, eid))
    ordered = []
    for (pairs, index), entries in sorted(packet_slots.items()):
        entries.sort()
        if len({slot for slot, _ in entries}) != len(entries):
            raise ValueError('two edges map to one packet slot')
        ordered.append({'symbol_pairs': [list(pair) for pair in pairs],
                        'index': index,
                        'occupied_slots': [[slot, eid] for slot, eid in entries]})
    if len(ordered) > len(packing.edges):
        raise AssertionError('nonempty packet count exceeds real edge count')
    return tuple(ordered)


def real_packet_slots(packet, slot_count):
    """Return validated ``(slot, edge_id)`` pairs for either packet schema."""
    if not isinstance(packet, dict) or type(slot_count) is not int or slot_count < 1:
        raise ValueError('invalid packet or slot count')
    if set(packet) in ({'symbol_pairs', 'slots'},
                       {'symbol_pairs', 'index', 'slots'}):
        slots = packet['slots']
        if not isinstance(slots, (tuple, list)) or len(slots) != slot_count:
            raise ValueError('dense packet slot array has incorrect length')
        result = tuple((slot, edge_id) for slot, edge_id in enumerate(slots)
                       if edge_id is not None)
    elif set(packet) == {'symbol_pairs', 'index', 'occupied_slots'}:
        entries = packet['occupied_slots']
        if not isinstance(entries, (tuple, list)):
            raise ValueError('sparse packet slots must be a sequence')
        result_list = []
        previous = -1
        for entry in entries:
            if (not isinstance(entry, (tuple, list)) or len(entry) != 2 or
                    type(entry[0]) is not int or type(entry[1]) is not int or
                    not 0 <= entry[0] < slot_count or entry[1] < 0 or
                    entry[0] <= previous):
                raise ValueError('sparse packet slots must be sorted unique valid pairs')
            previous = entry[0]
            result_list.append((entry[0], entry[1]))
        result = tuple(result_list)
    else:
        raise ValueError('unsupported packet representation')
    if any(type(slot) is not int or type(edge_id) is not int or edge_id < 0
           for slot, edge_id in result):
        raise ValueError('invalid occupied packet slot')
    return result


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


def implicit_sparse_mode_source(packing, *, max_work=1_000_000):
    """Build a canonical packet source without materializing empty slots."""
    packets = sparse_active_packet_view(packing, max_work=max_work)
    return {
        'schema': SPARSE_MODE_SCHEMA,
        'claim': 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS',
        'r': packing.r, 'a': packing.a, 'L': packing.L, 'D': packing.D,
        'M': len(packing.edges), 'H_pad': packing.H,
        'edges': [list(edge) for edge in packing.edges],
        'row_labels': {str(k): list(v) for k, v in packing.rows.items()},
        'column_labels': {str(k): list(v) for k, v in packing.cols.items()},
        'packets': list(packets),
        'initial_expected_square_scaled': packing.initial_score,
        'final_expected_square_scaled': packing.final_score,
        'conditional_expectation_trace': [list(step) for step in packing.trace],
    }


def check_implicit_mode_source(source, *, max_work=1_000_000, max_slots=4096):
    """Replay the constructor and check the complete sparse packet view."""
    try:
        if not isinstance(source, dict):
            raise ValueError('unsupported implicit packet source')
        schema = source.get('schema')
        if schema == 'VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1':
            expected_claim = 'FINITE_NONEMPTY_PACKET_VIEW'
            builder = implicit_mode_source
        elif schema == SPARSE_MODE_SCHEMA:
            expected_claim = 'FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS'
            builder = implicit_sparse_mode_source
        else:
            raise ValueError('unsupported implicit packet schema')
        if source.get('claim') != expected_claim:
            raise ValueError('unsupported implicit packet claim')
        edges = validate_edges(source['edges'])
        rebuilt = construct_implicit_packing(edges, r=source['r'], a=source['a'],
                                              max_work=max_work)
        if schema == 'VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1':
            expected = builder(rebuilt, max_work=max_work, max_slots=max_slots)
        else:
            expected = builder(rebuilt, max_work=max_work)
        # Compare only canonical fields; caller-supplied extra keys are rejected.
        if source != expected:
            raise ValueError('implicit labels, trace, padding, or occupied slots differ from replay')
        if len(source['packets']) > len(edges):
            raise ValueError('active packet count exceeds edge count')
        for packet in source['packets']:
            real_packet_slots(packet, source['L'])
        return {'valid': True, 'status': 'FINITE_IMPLICIT_MODE_SOURCE_VERIFIED',
                'edge_count': len(edges), 'active_packet_count': len(source['packets']),
                'all_classes_materialized': False,
                'empty_packet_slots_materialized': schema != SPARSE_MODE_SCHEMA,
                'universal_theorem_proven': False}
    except PackingBudgetExceeded as exc:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc)}
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError) as exc:
        return {'valid': False, 'status': 'INVALID_IMPLICIT_MODE_SOURCE', 'reason': str(exc)}


def audit_d3_child_wire_loads(packing, *, coordinate, max_work=1_000_000):
    """Check the per-child wire bound induced by one coordinate's labels.

    This is a finite certificate for the supplied graph and packing. It does
    not establish that every recursive input admits the same packing.
    """
    try:
        if type(coordinate) is not int or not 0 <= coordinate < packing.a:
            raise ValueError('coordinate outside packing dimension')
        checked = check_implicit_packing(packing, max_work=max_work,
                                         check_trace=True)
        if checked.get('valid') is not True:
            return {'status': checked.get('status', 'INVALID_PACKING'),
                    'valid': False, 'reason': checked.get('reason')}
        M, r = len(packing.edges), packing.r
        row_loads = Counter(packing.rows[u][coordinate] for u, _ in packing.edges)
        column_loads = Counter(packing.cols[v][coordinate] for _, v in packing.edges)
        children = []
        for group in range(r):
            row_count = row_loads.get(group, 0)
            column_count = column_loads.get(group, 0)
            child_edges = row_count + column_count
            children.append({
                'group': group,
                'row_half_wire_count': row_count,
                'column_half_wire_count': column_count,
                'child_wire_count': child_edges,
                'meets_6M_over_r': r * child_edges <= 6 * M,
                'meets_3M_over_32': r == 64 and 32 * child_edges <= 3 * M,
            })
        per_side_bound = all(r * load <= 3 * M
                             for load in (*row_loads.values(), *column_loads.values()))
        child_bound = all(item['meets_6M_over_r'] for item in children)
        target_bound = r == 64 and all(item['meets_3M_over_32'] for item in children)
        if sum(item['child_wire_count'] for item in children) != 2 * M:
            raise ValueError('children do not partition the two parent half-wire sets')
        return {
            'valid': True,
            'status': ('FINITE_D3_CHILD_SHRINK_REPLAYED'
                       if per_side_bound and child_bound else
                       'FINITE_D3_CHILD_SHRINK_BOUND_NOT_MET'),
            'claim': 'ONE_PACKING_INSTANCE_ONLY',
            'parent_edges': M,
            'coordinate': coordinate,
            'radix': r,
            'per_side_port_bound': per_side_bound,
            'per_child_6M_over_r_bound': child_bound,
            'all_children_meet_3M_over_32': target_bound,
            'children': children,
            'sum_child_wires': 2 * M,
            'universal_theorem_proven': False,
        }
    except (ValueError, TypeError, AttributeError) as exc:
        return {'valid': False, 'status': 'INVALID_CHILD_LOAD_AUDIT',
                'reason': str(exc)}


def construct_preconditioned_d3_packing(edges, *, a, r=64, max_work=None,
                                        max_pair_records=DEFAULT_MAX_PAIR_RECORDS):
    """Construct and replay a theorem-parameter D.3 packing for one graph.

    The call requires the D.3 numeric hypotheses and fixed radix 64. The
    result verifies this finite input only; it is not a uniform schedule or
    complexity theorem. ``max_work=None`` runs the explicit polynomial-time
    derandomizer without the experimental operation estimate.
    """
    from .constructor import d3_preconditions

    edges = validate_edges(edges)
    if type(r) is not int or r != 64:
        raise ValueError('the theorem-parameter packing requires radix 64')
    if type(a) is not int or a < 1:
        raise ValueError('positive packet exponent required')
    if not _work_budget_valid(max_work):
        raise ValueError('max_work must be a positive integer or None')
    M, delta = len(edges), max_side_degree(edges)
    preconditions = d3_preconditions(M, r, a, delta)
    required = ('M_ge_2_D_squared_delta', 'M_ge_LD', '2L_le_delta')
    if not all(preconditions[name] for name in required):
        return {'status': 'INCONCLUSIVE_D3_PRECONDITIONS',
                'preconditions': preconditions,
                'universal_theorem_proven': False}
    try:
        packing = construct_implicit_packing(edges, r=r, a=a, max_work=max_work,
                                             max_pair_records=max_pair_records)
        replay = check_implicit_packing(packing, max_work=max_work, check_trace=True,
                                        max_pair_records=max_pair_records)
        if replay.get('valid') is not True:
            return {'status': replay.get('status', 'INVALID_PACKING'),
                    'packing_check': replay,
                    'universal_theorem_proven': False}
        if not all(replay.get(key) is True for key in
                   ('potential_bound', 'packing_count_bound', 'symbol_port_bound',
                    'd3_numeric_preconditions')):
            return {'status': 'INCONCLUSIVE_PACKING_BOUNDS_NOT_REPLAYED',
                    'packing_check': replay,
                    'universal_theorem_proven': False}
        child_audits = [audit_d3_child_wire_loads(
            packing, coordinate=coordinate, max_work=max_work)
            for coordinate in range(a)]
        if any(item.get('valid') is not True or
               item.get('status') != 'FINITE_D3_CHILD_SHRINK_REPLAYED'
               for item in child_audits):
            return {'status': 'INCONCLUSIVE_CHILD_LOAD_BOUND_NOT_REPLAYED',
                    'packing_check': replay, 'child_audits': child_audits,
                    'universal_theorem_proven': False}
        return {'status': 'FINITE_D3_PRECONDITIONED_PACKING_REPLAYED',
                'packing': packing,
                'preconditions': preconditions,
                'packing_check': replay,
                'child_audits': child_audits,
                'universal_theorem_proven': False}
    except PackingBudgetExceeded:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT',
                'preconditions': preconditions,
                'universal_theorem_proven': False}


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
