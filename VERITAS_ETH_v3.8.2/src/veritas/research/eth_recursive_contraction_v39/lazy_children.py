"""Finite lazy group-child networks from a checked geometric-mode tuple.

This implements the manuscript's local child *shape* and packet-entry
coefficient extraction for bounded examples. It does not remove the v31/v36
parameter caps, provide nested-ring recursion, or prove the M/8 theorem.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product
from time import monotonic

from veritas.research.eth_modes_v31.jet_tiles import (
    check_jet_tile_modes, _v2,
)
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursion_v30.implicit_children import (
    make_bipartite_edges, _direct_oracle, Limits,
)
from veritas.research.eth_modes_v27.enumeration import weighted_tuples


class ChildEvaluationBudgetExceeded(RuntimeError):
    pass


@dataclass
class _Budget:
    maximum: int
    timeout_s: float
    used: int = 0
    started: float = 0.0

    def __post_init__(self):
        if type(self.maximum) is not int or not 1 <= self.maximum <= 2_000_000:
            raise ValueError('maximum work must be in 1..2000000')
        if type(self.timeout_s) not in (int, float) or not 0 < self.timeout_s <= 30:
            raise ValueError('timeout must be in (0,30]')
        self.started = monotonic()

    def tick(self, amount=1):
        self.used += amount
        if self.used > self.maximum or monotonic() - self.started > self.timeout_s:
            raise ChildEvaluationBudgetExceeded('lazy child work/time budget exhausted')


@dataclass(frozen=True)
class OriginalVertex:
    label: str
    ports: tuple[int, ...]
    table: tuple[int, ...]


@dataclass(frozen=True)
class PacketTensorEntry:
    """Immutable recipe for one packet factor in one group child."""
    packet_id: int
    ports: tuple[int, ...]
    variables: tuple[tuple[str, int], ...]
    rows: tuple
    target_modes: tuple
    source_modes: tuple

    def evaluate(self, port_bits: tuple[int, ...], jets: JetRing, budget: _Budget):
        if len(port_bits) != len(self.ports) or any(bit not in (0, 1) for bit in port_bits):
            raise ValueError('packet tensor entry has the wrong Boolean index')
        assignment = dict(zip(self.ports, port_bits))
        x_value = {edge: assignment[port] for port, (kind, edge) in zip(self.ports, self.variables)
                   if kind == 'X'}
        y_value = {edge: assignment[port] for port, (kind, edge) in zip(self.ports, self.variables)
                   if kind == 'Y'}

        # Only positive target exponents need polynomial variables.  The
        # coefficient table is sparse and truncated componentwise at beta.
        active = tuple((mid, exponent, entries)
                       for mid, exponent, entries in self.target_modes if exponent)
        zero_exp = (0,) * len(active)
        polynomial = {zero_exp: jets.one}
        for row_id, encoded_local in self.rows:
            budget.tick()
            local = jets.zero
            for column_id, encoded in encoded_local:
                if x_value.get(column_id, 0):
                    local = jets.add(local, jets.elem(encoded))
            is_one = y_value.get(row_id, 0)
            constant = local if is_one else jets.sub(jets.one, local)
            sign = 1 if is_one else -1
            row_coefficients = {}
            for mid, exponent, entries in active:
                for rid, encoded in entries:
                    if rid == row_id:
                        row_coefficients[mid] = jets.elem(encoded)
                        break

            out = {}
            for powers, value in polynomial.items():
                budget.tick()
                base_value = jets.mul(value, constant)
                if base_value != jets.zero:
                    out[powers] = jets.add(out.get(powers, jets.zero), base_value)
                for j, (mid, exponent, _) in enumerate(active):
                    if powers[j] >= exponent:
                        continue
                    coeff = row_coefficients.get(mid, jets.zero)
                    if coeff == jets.zero:
                        continue
                    next_powers = list(powers)
                    next_powers[j] += 1
                    key = tuple(next_powers)
                    term = jets.mul(value, coeff if sign == 1 else jets.neg(coeff))
                    if term != jets.zero:
                        out[key] = jets.add(out.get(key, jets.zero), term)
            polynomial = {key: value for key, value in out.items() if value != jets.zero}

        target = tuple(exponent for _, exponent, _ in active)
        result = polynomial.get(target, jets.zero)
        for mid, exponent, column_terms in self.source_modes:
            budget.tick()
            if exponent == 0:
                continue
            linear = sum(power * x_value.get(column_id, 0)
                         for column_id, power in column_terms)
            factor = jets.elem([[linear]])
            result = jets.mul(result, _pow_jets(factor, exponent, jets, budget))
            if result == jets.zero:
                break
        return result


@dataclass(frozen=True)
class GroupChildDescription:
    group: int
    edge_variables: tuple[tuple[str, int], ...]
    original_vertices: tuple[OriginalVertex, ...]
    packet_tensors: tuple[PacketTensorEntry, ...]
    maximum_degree: int

    @property
    def edge_count(self):
        return len(self.edge_variables)


def _pow_jets(value, exponent, jets, budget):
    result = jets.one
    base = value
    n = exponent
    while n:
        budget.tick()
        if n & 1:
            result = jets.mul(result, base)
        n >>= 1
        if n:
            base = jets.mul(base, base)
    return result


def _check_parent(net, mode_certificate):
    verdict = check_jet_tile_modes(mode_certificate)
    if verdict.get('valid') is not True:
        raise ValueError('geometric mode certificate did not verify')
    if net.edges < 1 or net.edges > 6 or len(net.factors) > 20:
        raise ValueError('finite child oracle supports 1..6 parent wires and <=20 factors')
    d3 = mode_certificate['d3_certificate']
    if make_bipartite_edges(net) != d3['edges']:
        raise ValueError('parent network endpoints differ from packet source')
    return d3


def build_group_children(net, mode_certificate, beta):
    """Create immutable group-local children for one retained exponent tuple."""
    d3 = _check_parent(net, mode_certificate)
    return _build_group_children_checked(net, mode_certificate, beta, d3)


def _build_group_children_checked(net, mode_certificate, beta, d3):
    modes = mode_certificate['modes']
    p = mode_certificate['precision']
    if not isinstance(beta, (tuple, list)) or len(beta) != len(modes) or any(type(x) is not int or x < 0 for x in beta):
        raise ValueError('beta must give one nonnegative integer per mode')
    weights = [mode['weight'] for mode in modes]
    if sum(x * w for x, w in zip(beta, weights)) >= p:
        raise ValueError('beta is outside the retained weighted-tuple region')

    m = net.edges
    coordinate = _v2(mode_certificate['node'])
    ring = ExtensionRing(p, first_irreducible(mode_certificate['extension_degree']))
    jets = JetRing(ring, mode_certificate['jet_length'])
    row_groups = tuple(d3['row_labels'][str(u)][coordinate] for u, _ in d3['edges'])
    col_groups = tuple(d3['column_labels'][str(v)][coordinate] for _, v in d3['edges'])
    factor_groups = []
    for factor in net.factors:
        is_row = factor.label.startswith(('row:', 'clause:'))
        _, _, tag = factor.label.partition(':')
        labels = d3['row_labels'] if is_row else d3['column_labels']
        factor_groups.append(labels.get(tag, [0] * d3['a'])[coordinate])
    # Include groups containing isolated zero-port vertices. Their constant
    # tensor factors still contribute to the contraction even though no edge
    # label can mention them.
    group_ids = sorted(set(row_groups) | set(col_groups) | set(factor_groups))

    # Give each local Boolean halfbit a child-network edge index.
    children = []
    for group in group_ids:
        variables = tuple([('Y', eid) for eid in range(m) if row_groups[eid] == group] +
                          [('X', eid) for eid in range(m) if col_groups[eid] == group])
        edge_index = {variable: i for i, variable in enumerate(variables)}

        original = []
        for factor in net.factors:
            is_row = factor.label.startswith(('row:', 'clause:'))
            role, _, tag = factor.label.partition(':')
            labels = d3['row_labels'] if is_row else d3['column_labels']
            if labels.get(tag, [0] * d3['a'])[coordinate] != group:
                continue
            kind = 'Y' if is_row else 'X'
            ports = tuple(edge_index[(kind, eid)] for eid in factor.ports)
            original.append(OriginalVertex(factor.label, ports, tuple(factor.table)))

        packet_tensors = []
        for packet_id, packet in enumerate(d3['packets']):
            real = [(slot, eid) for slot, eid in enumerate(packet['slots']) if eid is not None]
            row_ids = tuple(eid for _, eid in real if row_groups[eid] == group)
            col_ids = tuple(eid for _, eid in real if col_groups[eid] == group)
            port_vars = tuple([('Y', eid) for eid in row_ids] + [('X', eid) for eid in col_ids])
            if not port_vars:
                continue
            ports = tuple(edge_index[var] for var in port_vars)

            packet_rows = []
            for rid in row_ids:
                local = tuple((cid, tuple(tuple(coordinate) for coordinate in encoded))
                              for rr, cid, encoded in mode_certificate['local']
                              if rr == rid and cid in col_ids)
                packet_rows.append((rid, local))

            target_modes = []
            source_modes = []
            for mid, mode in enumerate(modes):
                if mode['packet'] != packet_id:
                    continue
                exponent = beta[mid]
                if mode['target_group'] == group:
                    rows = tuple((rid, tuple(tuple(c) for c in encoded))
                                 for rid, encoded in mode['rows'] if rid in row_ids)
                    target_modes.append((mid, exponent, rows))
                if mode['source_group'] == group:
                    terms = tuple((cid, coefficient)
                                  for cid, coefficient in mode['column_terms'] if cid in col_ids)
                    source_modes.append((mid, exponent, terms))

            packet_tensors.append(PacketTensorEntry(
                packet_id, ports, port_vars, tuple(packet_rows),
                tuple(target_modes), tuple(source_modes)))

        # Every child edge is incident to one original tensor and one packet tensor.
        incidences = Counter(port for vertex in original for port in vertex.ports)
        incidences.update(port for packet in packet_tensors for port in packet.ports)
        if incidences != Counter({i: 2 for i in range(len(variables))}):
            raise ValueError('child halfbit edge is not incident to exactly two child tensors')
        maximum_degree = max([len(v.ports) for v in original] +
                             [len(v.ports) for v in packet_tensors] + [0])
        children.append(GroupChildDescription(group, variables, tuple(original),
                                              tuple(packet_tensors), maximum_degree))
    return tuple(children)


def contract_group_child(child, mode_certificate, *, max_work=250_000,
                         timeout_s=10.0):
    """Contract one finite child by edge enumeration and lazy packet entries."""
    if not isinstance(child, GroupChildDescription):
        raise TypeError('GroupChildDescription required')
    d3 = mode_certificate['d3_certificate']
    p = mode_certificate['precision']
    ring = ExtensionRing(p, first_irreducible(mode_certificate['extension_degree']))
    jets = JetRing(ring, mode_certificate['jet_length'])
    budget = _Budget(max_work, timeout_s)
    total = jets.zero
    for bits in product((0, 1), repeat=child.edge_count):
        budget.tick()
        value = jets.one
        for vertex in child.original_vertices:
            mask = sum(bits[port] << j for j, port in enumerate(vertex.ports))
            value = jets.mul(value, jets.elem([[vertex.table[mask]]]))
            if value == jets.zero:
                break
        if value != jets.zero:
            for packet in child.packet_tensors:
                local_bits = tuple(bits[port] for port in packet.ports)
                value = jets.mul(value, packet.evaluate(local_bits, jets, budget))
                if value == jets.zero:
                    break
        total = jets.add(total, value)
    return {'group': child.group, 'edge_count': child.edge_count,
            'maximum_degree': child.maximum_degree,
            'result': [[int(c) for c in coeff] for coeff in total],
            'work_units': budget.used,
            'manuscript_M_over_8_bound_proven': False}


def contract_child_expansion(net, mode_certificate, *, max_tuples=3000,
                             max_work=250_000, timeout_s=10.0):
    """Evaluate the finite parent-to-child identity for every retained tuple."""
    d3 = _check_parent(net, mode_certificate)
    modes = mode_certificate['modes']
    weights = [mode['weight'] for mode in modes]
    tuples = list(weighted_tuples(weights, mode_certificate['precision'],
                                  max_tuples=max_tuples))
    p = mode_certificate['precision']
    ring = ExtensionRing(p, first_irreducible(mode_certificate['extension_degree']))
    jets = JetRing(ring, mode_certificate['jet_length'])
    accumulated = jets.zero
    tuple_rows = []
    total_work = 0
    deadline = monotonic() + timeout_s

    def remaining_time():
        left = deadline - monotonic()
        if left <= 0:
            raise ChildEvaluationBudgetExceeded('aggregate child wall-time budget exhausted')
        return left

    for beta in tuples:
        remaining_time()
        # Parent validation and mode replay are performed once per call, not
        # once per tuple; this keeps checker overhead outside child expansion.
        children = _build_group_children_checked(net, mode_certificate, beta, d3)
        product_value = jets.one
        child_rows = []
        for child in children:
            remaining = max_work - total_work
            if remaining < 1:
                raise ChildEvaluationBudgetExceeded('aggregate child work budget exhausted')
            out = contract_group_child(child, mode_certificate,
                                       max_work=remaining, timeout_s=remaining_time())
            total_work += out['work_units']
            child_rows.append(out)
            encoded = out['result']
            child_value = jets.elem(encoded)
            product_value = jets.mul(product_value, child_value)
        accumulated = jets.add(accumulated, product_value)
        tuple_rows.append({'beta': list(beta), 'children': child_rows,
                           'product': [[int(c) for c in coeff] for coeff in product_value]})

    direct_budget = Limits(max_assignments=min(max_work, 2_000_000),
                           timeout_s=min(remaining_time(), 20.0))
    direct = _direct_oracle(net, d3, mode_certificate['node'], jets, direct_budget)
    if accumulated != direct:
        raise ArithmeticError('lazy child expansion differs from direct half-edge oracle')
    return {'schema': 'VERITAS_ETH_LAZY_CHILD_EXPANSION_V39',
            'claim': 'FINITE_LAZY_GROUP_CHILD_IDENTITY_ONLY',
            'network': {'edges': net.edges,
                        'factors': [{'ports': list(f.ports), 'table': list(f.table), 'label': f.label}
                                    for f in net.factors]},
            'mode_certificate': mode_certificate,
            'retained_tuple_count': len(tuples), 'tuples': tuple_rows,
            'result': [[int(c) for c in coeff] for coeff in accumulated],
            'direct_oracle_matches': True,
            'algorithm_work_units': total_work,
            'independent_oracle_work_units': direct_budget.used,
            'recursive_child_networks': False,
            'subexponential_runtime_proven': False}


def check_child_expansion_certificate(cert, *, max_tuples=3000,
                                      max_work=250_000, timeout_s=10.0):
    """Rebuild all child descriptions and replay their contraction identity."""
    try:
        if (not isinstance(cert, dict) or
                cert.get('schema') != 'VERITAS_ETH_LAZY_CHILD_EXPANSION_V39' or
                cert.get('claim') != 'FINITE_LAZY_GROUP_CHILD_IDENTITY_ONLY' or
                cert.get('recursive_child_networks') is not False or
                cert.get('subexponential_runtime_proven') is not False):
            raise ValueError('unsupported schema or overstated claim')
        from veritas.research.eth_recursion_v30.implicit_children import _deserialize_net
        network = _deserialize_net(cert['network'])
        expected = contract_child_expansion(network, cert['mode_certificate'],
                                            max_tuples=max_tuples,
                                            max_work=max_work,
                                            timeout_s=timeout_s)
        if expected != cert:
            raise ValueError('child expansion differs from canonical replay')
        return {'valid': True, 'status': 'FINITE_LAZY_CHILD_IDENTITY_REPLAYED',
                'retained_tuple_count': cert['retained_tuple_count'],
                'algorithm_work_units': cert['algorithm_work_units'],
                'independent_oracle_work_units': cert['independent_oracle_work_units'],
                'recursive_child_networks': False,
                'subexponential_runtime_proven': False}
    except (ValueError, TypeError, KeyError, IndexError, OverflowError,
            ArithmeticError, RuntimeError, TimeoutError, ZeroDivisionError) as exc:
        return {'valid': False, 'status': 'INVALID_LAZY_CHILD_EXPANSION',
                'reason': str(exc)}
