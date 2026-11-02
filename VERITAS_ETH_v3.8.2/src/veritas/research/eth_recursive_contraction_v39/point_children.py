"""A second finite child transformation at an interpolation point.

Input vertices may already be immutable lazy packet descriptions.  This
checks another local mode identity over their truncated coefficient ring; it
does not implement tapered reconstruction or the asymptotic schedule.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import json
from time import monotonic

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry
from veritas.research.eth_interpolation.extension_lagrange import evaluate_polynomial
from veritas.research.eth_modes_v31.jet_tiles import check_jet_tile_modes, _v2
from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from .lazy_children import PacketTensorEntry, _Budget, ChildEvaluationBudgetExceeded
from .described_network import (
    CreatedDenseTensor, CreatedPacketTensor, DescribedNetwork, DescribedVertex,
    contract_described_network,
)
from .point_modes import SCHEMA as POINT_MODE_SCHEMA, check_point_modes
from .structural_tuples import structural_tuples
from .mode_matching import _BudgetExceeded as MatchingBudgetExceeded, _Work as MatchingWork, certify_structural_tuple_matching
from .point_mode_matching import _verify_hall_witness
from veritas.research.eth_packing_v26.implicit import real_packet_slots


@dataclass(frozen=True)
class DescribedGroupChild:
    group: int
    network: DescribedNetwork


class ChildSizeInvariantViolation(RuntimeError):
    """A finite child violates a specifically requested size invariant."""


def _ring_for(parent, mode_certificate, *, max_parent_wires=6, _tuple_work=None,
              _source_validation='canonical', _source_work=1_000_000):
    if not isinstance(parent, DescribedNetwork) or not parent.vertices:
        raise ValueError('a nonempty described network is required')
    if type(max_parent_wires) is not int or not 1 <= max_parent_wires <= 8:
        raise ValueError('finite parent-wire limit must be in 1..8')
    if not 1 <= parent.edges <= max_parent_wires:
        raise ValueError('finite point-child reference exceeds its parent-wire limit')
    check = (check_point_modes(mode_certificate, max_parent_wires=max_parent_wires,
                               _tuple_work=_tuple_work,
                               _source_validation=_source_validation, _source_work=_source_work)
             if mode_certificate.get('schema') == POINT_MODE_SCHEMA
             else check_jet_tile_modes(mode_certificate))
    if check.get('status') == 'INCONCLUSIVE_RESOURCE_LIMIT':
        raise ModeBudgetExceeded(check.get('reason', 'mode verification budget exhausted'))
    if check.get('valid') is not True:
        raise ValueError('geometric mode certificate did not verify')
    if mode_certificate['jet_length'] != 1:
        raise ValueError('point-child modes must contain scalar coefficients')
    source = mode_certificate['d3_certificate']
    if [list(edge) for edge in parent.bipartite_edges()] != source['edges']:
        raise ValueError('packing endpoints do not match described parent')
    p = mode_certificate['precision']
    f = first_irreducible(mode_certificate['extension_degree'])
    length = None
    for vertex in parent.vertices:
        tensor = vertex.tensor
        if isinstance(tensor, CreatedDenseTensor):
            entry = tensor.entries[0]
            created, poly, size = entry.creation_precision, entry.defining_polynomial, len(entry.coefficients)
        elif isinstance(tensor, CreatedPacketTensor):
            created, poly, size = tensor.creation_precision, tensor.defining_polynomial, tensor.jet_length
        else:
            raise ValueError('unsupported entry description')
        if poly != f or created > p or (length is not None and size != length):
            raise ValueError('entry creation ring is incompatible with this call')
        length = size
    return JetRing(ExtensionRing(p, f), length), source


def build_point_children(parent, mode_certificate, beta, *, max_parent_wires=6):
    """Build one immutable group-child graph per occupied symbol group."""
    ring, source = _ring_for(parent, mode_certificate, max_parent_wires=max_parent_wires)
    return _build_point_children_checked(parent, mode_certificate, beta, ring, source)


def _build_point_children_checked(parent, mode_certificate, beta, ring, source):
    modes = mode_certificate['modes']
    if (not isinstance(beta, (tuple, list)) or len(beta) != len(modes) or
            any(type(x) is not int or x < 0 for x in beta)):
        raise ValueError('beta must contain one nonnegative exponent per mode')
    if sum(value * mode['weight'] for value, mode in zip(beta, modes)) >= ring.base.p:
        raise ValueError('beta exceeds the retained weight budget')

    coordinate = _v2(mode_certificate['node'])
    edges = source['edges']
    row_groups = tuple(source['row_labels'][str(u)][coordinate] for u, _ in edges)
    column_groups = tuple(source['column_labels'][str(v)][coordinate] for _, v in edges)
    side_vertices = {side: tuple(v for v in parent.vertices if v.side == side)
                     for side in ('row', 'column')}
    vertex_groups = {}
    for side in ('row', 'column'):
        labels = source['row_labels'] if side == 'row' else source['column_labels']
        for index, vertex in enumerate(side_vertices[side]):
            # Isolated vertices have no packing label but still contribute.
            vertex_groups[(side, index)] = labels.get(str(index), [0] * source['a'])[coordinate]
    groups = sorted(set(row_groups) | set(column_groups) | set(vertex_groups.values()))

    children = []
    for group in groups:
        variables = tuple([('Y', e) for e in range(parent.edges) if row_groups[e] == group] +
                          [('X', e) for e in range(parent.edges) if column_groups[e] == group])
        edge_index = {value: index for index, value in enumerate(variables)}
        vertices = []
        for side in ('row', 'column'):
            kind = 'Y' if side == 'row' else 'X'
            for index, vertex in enumerate(side_vertices[side]):
                if vertex_groups[(side, index)] != group:
                    continue
                ports = tuple(edge_index[(kind, e)] for e in vertex.ports)
                vertices.append(DescribedVertex('row', f'{side}:{index}:{vertex.label}',
                                                ports, vertex.tensor))

        for packet_id, packet in enumerate(source['packets']):
            real = real_packet_slots(packet, source['L'])
            rows = tuple(eid for _, eid in real if row_groups[eid] == group)
            columns = tuple(eid for _, eid in real if column_groups[eid] == group)
            variables_here = tuple([('Y', eid) for eid in rows] + [('X', eid) for eid in columns])
            if not variables_here:
                continue
            ports = tuple(edge_index[item] for item in variables_here)
            row_data = []
            for rid in rows:
                local = tuple((cid, tuple(tuple(c) for c in encoded))
                              for rr, cid, encoded in mode_certificate['local']
                              if rr == rid and cid in columns)
                row_data.append((rid, local))
            targets, sources = [], []
            for mid, mode in enumerate(modes):
                if mode['packet'] != packet_id:
                    continue
                if mode['target_group'] == group:
                    coeffs = tuple((rid, tuple(tuple(c) for c in encoded))
                                   for rid, encoded in mode['rows'] if rid in rows)
                    targets.append((mid, beta[mid], coeffs))
                if mode['source_group'] == group:
                    terms = tuple((cid, coefficient) for cid, coefficient in mode['column_terms']
                                  if cid in columns)
                    sources.append((mid, beta[mid], terms))
            recipe = PacketTensorEntry(packet_id, ports, variables_here, tuple(row_data),
                                       tuple(targets), tuple(sources))
            tensor = CreatedPacketTensor(recipe, ring.base.p, ring.base.f, ring.length)
            vertices.append(DescribedVertex('column', f'packet:{packet_id}', ports, tensor))
        children.append(DescribedGroupChild(group, DescribedNetwork(len(variables), tuple(vertices))))
    return tuple(children)


def _direct_point_oracle(parent, source, node, zeta, ring, budget):
    """Independent full X,Y half-edge sum at T=node+2L*zeta."""
    m = parent.edges
    packet_rows = []
    for packet in source['packets']:
        real = real_packet_slots(packet, source['L'])
        for x, rid in real:
            entries = tuple((cid, ring.elem([evaluate_polynomial(
                ring.base, shift_cauchy_entry(source['L'], node, ring.base, x, y),
                zeta)])) for y, cid in real)
            packet_rows.append((rid, entries))
    total = ring.zero
    for xbits in product((0, 1), repeat=m):
        for ybits in product((0, 1), repeat=m):
            budget.tick()
            term = ring.one
            for vertex in parent.vertices:
                bits = ybits if vertex.side == 'row' else xbits
                value = vertex.tensor.evaluate(tuple(bits[e] for e in vertex.ports), ring, budget)
                term = ring.mul(term, value)
                if term == ring.zero:
                    break
            if term != ring.zero:
                for rid, entries in packet_rows:
                    linear = ring.zero
                    for cid, coefficient in entries:
                        if xbits[cid]:
                            linear = ring.add(linear, coefficient)
                    value = linear if ybits[rid] else ring.sub(ring.one, linear)
                    term = ring.mul(term, value)
                    if term == ring.zero:
                        break
            total = ring.add(total, term)
    return total


def contract_point_child_expansion(parent, mode_certificate, *, max_tuples=3000,
                                   max_work=250_000, timeout_s=10.0,
                                   require_one_eighth_shrink=False,
                                   max_parent_wires=6,
                                   _child_contractor=None, _source_validation='canonical',
                                   _source_work=1_000_000, enable_hall_pruning=False):
    """Check a complete finite mode sum for a previously described child."""
    if type(require_one_eighth_shrink) is not bool:
        raise ValueError('require_one_eighth_shrink must be Boolean')
    if type(enable_hall_pruning) is not bool:
        raise ValueError('enable_hall_pruning must be Boolean')
    ring, source = _ring_for(parent, mode_certificate, max_parent_wires=max_parent_wires,
                             _source_validation=_source_validation, _source_work=_source_work)
    deadline = monotonic() + timeout_s
    total, work, nested_oracle_work, rows = ring.zero, 0, 0, []
    hall_work, hall_pruned = 0, 0

    def charge_hall():
        nonlocal work, hall_work
        if monotonic() >= deadline or work + nested_oracle_work >= max_work:
            raise ChildEvaluationBudgetExceeded('point-child Hall work/time budget exhausted')
        work += 1
        hall_work += 1

    for beta in structural_tuples(mode_certificate['modes'], ring.base.p, max_tuples=max_tuples):
        if monotonic() >= deadline:
            raise ChildEvaluationBudgetExceeded('point-child wall-time budget exhausted')
        if enable_hall_pruning:
            available = min(max_work - work - nested_oracle_work, 2_000_000)
            if available < 1:
                raise ChildEvaluationBudgetExceeded('point-child Hall work budget exhausted')
            match = certify_structural_tuple_matching(mode_certificate['modes'], beta,
                                                      max_work=available, _on_step=charge_hall)
            if match['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT':
                raise ChildEvaluationBudgetExceeded('point-child Hall matching budget exhausted')
            if match['status'] == 'ZERO_IF_SUPPLIED_SUPPORT_COMPLETE':
                available = min(max_work - work - nested_oracle_work, 2_000_000)
                if available < 1:
                    raise ChildEvaluationBudgetExceeded('point-child Hall witness budget exhausted')
                try:
                    _verify_hall_witness(mode_certificate['modes'], beta, match['witness'],
                                         MatchingWork(available, charge_hall))
                except MatchingBudgetExceeded as exc:
                    raise ChildEvaluationBudgetExceeded('point-child Hall witness budget exhausted') from exc
                rows.append({'beta': tuple(beta), 'children': (), 'term': ring.zero,
                             'structurally_zero': True, 'hall_witness': match['witness']})
                hall_pruned += 1
                continue
            if match['status'] != 'MATCHING_FEASIBLE_ONLY':
                raise ArithmeticError('unexpected Hall matching status')
        children = _build_point_children_checked(parent, mode_certificate, beta, ring, source)
        term, summaries = ring.one, []
        for child in children:
            child_edges = child.network.edges
            meets_eighth = 8 * child_edges < parent.edges
            meets_port_bound = source['r'] * child_edges <= 6 * parent.edges
            if require_one_eighth_shrink and not (meets_eighth and meets_port_bound):
                raise ChildSizeInvariantViolation(
                    f'group {child.group} has {child_edges} child edges for '
                    f'{parent.edges} parent edges and radix {source["r"]}')
            left_work, left_time = max_work - work - nested_oracle_work, deadline - monotonic()
            if left_work < 1 or left_time <= 0:
                raise ChildEvaluationBudgetExceeded('point-child resource budget exhausted')
            if _child_contractor is None:
                out = contract_described_network(child.network, ring, max_work=left_work,
                                                 timeout_s=left_time, max_edges=12)
            else:
                out = _child_contractor(child.network, ring, left_work, left_time)
                if (not isinstance(out, dict) or 'result' not in out or
                        type(out.get('work_units')) is not int or
                        type(out.get('oracle_work_units', 0)) is not int or
                        out['work_units'] < 0 or out.get('oracle_work_units', 0) < 0 or
                        out['work_units'] + out.get('oracle_work_units', 0) > left_work):
                    raise ValueError('child contractor did not return a complete bounded result')
            work += out['work_units']
            nested_oracle_work += out.get('oracle_work_units', 0)
            term = ring.mul(term, out['result'])
            summaries.append({'group': child.group, 'edge_count': child_edges,
                              'maximum_degree': max((len(v.ports) for v in child.network.vertices), default=0),
                              'result': out['result'], 'meets_strict_one_eighth': meets_eighth,
                              'meets_six_M_over_r': meets_port_bound})
        total = ring.add(total, term)
        rows.append({'beta': tuple(beta), 'children': tuple(summaries),
                     'term': term, 'structurally_zero': False})
    left_time = deadline - monotonic()
    if left_time <= 0:
        raise ChildEvaluationBudgetExceeded('point-child wall-time budget exhausted')
    remaining_work = max_work - work - nested_oracle_work
    if remaining_work < 1:
        raise ChildEvaluationBudgetExceeded('point-child oracle work budget exhausted')
    oracle_budget = _Budget(remaining_work, min(left_time, 30.0))
    zeta = tuple(mode_certificate.get('zeta', [0] * ring.base.e))
    oracle = _direct_point_oracle(parent, source, mode_certificate['node'], zeta, ring, oracle_budget)
    if total != oracle:
        raise ArithmeticError('described child expansion disagrees with direct half-edge sum')
    if (mode_certificate.get('schema') == POINT_MODE_SCHEMA and
            len(rows) != mode_certificate['structural_tuple_count']):
        raise ArithmeticError('structural tuple stream differs from the checked mode certificate')
    omitted = mode_certificate['mode_tuple_count'] - len(rows)
    if omitted < 0:
        raise ArithmeticError('structural tuple count exceeds nominal mode tuple count')
    valuations = tuple({'mode': index, 'weight': mode['weight'],
                        'minimum_observed_valuation': min(
                            ring.base.valuation(ring.base.elem(encoded[0]))
                            for _, encoded in mode['rows'])}
                       for index, mode in enumerate(mode_certificate['modes']))
    result = {'result': total, 'tuples': tuple(rows), 'algorithm_work_units': work,
            'structurally_zero_tuples': omitted,
            'independent_oracle_work_units': nested_oracle_work + oracle_budget.used,
            'parent_edge_count': parent.edges, 'radix': source['r'],
            'precision': ring.base.p, 'mode_valuations': valuations,
            'all_children_meet_strict_one_eighth': all(
                child['meets_strict_one_eighth'] for row in rows for child in row['children']),
            'all_children_meet_six_M_over_r': all(
                child['meets_six_M_over_r'] for row in rows for child in row['children']),
            'direct_oracle_result': oracle,
            'direct_oracle_matches': True, 'tapered_reconstruction_implemented': False,
            'subexponential_runtime_proven': False}
    if enable_hall_pruning:
        result.update({'hall_pruned_tuples': hall_pruned, 'hall_work_units': hall_work})
    return result


def check_point_child_expansion_certificate(parent, mode_certificate, certificate,
                                            *, max_tuples=3000, max_work=250_000,
                                            timeout_s=10.0, max_parent_wires=6,
                                            enable_hall_pruning=False):
    """Replay finite child values, valuations, sizes, and the half-edge identity."""
    try:
        if type(certificate) is not dict:
            raise ValueError('finite point-child certificate must be a dictionary')
        checked = contract_point_child_expansion(parent, mode_certificate,
                                                  max_tuples=max_tuples,
                                                  max_work=max_work, timeout_s=timeout_s,
                                                  max_parent_wires=max_parent_wires,
                                                  enable_hall_pruning=enable_hall_pruning)
        fields = ('result', 'tuples', 'structurally_zero_tuples', 'parent_edge_count',
                  'radix', 'precision', 'mode_valuations',
                  'all_children_meet_strict_one_eighth', 'all_children_meet_six_M_over_r',
                  'direct_oracle_result', 'direct_oracle_matches',
                  'tapered_reconstruction_implemented', 'subexponential_runtime_proven')
        if enable_hall_pruning:
            fields += ('hall_pruned_tuples',)
        observed = json.dumps({field: certificate.get(field) for field in fields},
                              sort_keys=True, separators=(',', ':'), allow_nan=False)
        expected = json.dumps({field: checked[field] for field in fields},
                              sort_keys=True, separators=(',', ':'), allow_nan=False)
        if observed != expected:
            raise ValueError('child expansion certificate differs from source replay')
        return {'valid': True, 'status': 'FINITE_POINT_CHILD_IDENTITY_REPLAYED',
                'all_children_meet_strict_one_eighth': checked['all_children_meet_strict_one_eighth'],
                'work_counters_verified': False,
                'subexponential_runtime_proven': False}
    except (ChildEvaluationBudgetExceeded, ModeBudgetExceeded) as exc:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc)}
    except (TypeError, ValueError, KeyError, IndexError, ArithmeticError) as exc:
        return {'valid': False, 'status': 'INVALID_POINT_CHILD_CERTIFICATE', 'reason': str(exc)}
