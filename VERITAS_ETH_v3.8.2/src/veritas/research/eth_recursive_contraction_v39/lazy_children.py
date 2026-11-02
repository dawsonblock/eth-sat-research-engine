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
from veritas.research.eth_packing_v26.implicit import real_packet_slots
from veritas.research.eth_recursion_v30.implicit_children import (
    make_bipartite_edges, _direct_oracle, Limits,
)
from veritas.research.eth_modes_v27.enumeration import weighted_tuples


class ChildEvaluationBudgetExceeded(RuntimeError):
    def __init__(self, message, *, work_units=None):
        super().__init__(message)
        self.work_units = work_units


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
            raise ChildEvaluationBudgetExceeded('lazy child work/time budget exhausted',
                                                work_units=min(self.used, self.maximum))


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

    def __post_init__(self):
        if type(self.packet_id) is not int or self.packet_id < 0:
            raise ValueError('packet id must be a nonnegative integer')
        if (type(self.ports) is not tuple or
                any(type(port) is not int or port < 0 for port in self.ports) or
                len(set(self.ports)) != len(self.ports)):
            raise ValueError('packet ports must be distinct nonnegative integers')
        if (type(self.variables) is not tuple or len(self.variables) != len(self.ports) or
                any(type(item) is not tuple or len(item) != 2 or
                    item[0] not in ('X', 'Y') or type(item[1]) is not int or item[1] < 0
                    for item in self.variables) or
                len(set(self.variables)) != len(self.variables)):
            raise ValueError('packet variables must uniquely match the ports')
        x_ids = {edge for kind, edge in self.variables if kind == 'X'}
        y_ids = {edge for kind, edge in self.variables if kind == 'Y'}

        def coefficient(value):
            if (type(value) is not tuple or any(type(part) is not tuple or
                    any(type(c) is not int for c in part) for part in value)):
                raise ValueError('packet coefficients must be immutable integer jets')

        if type(self.rows) is not tuple:
            raise ValueError('packet rows must be immutable')
        row_ids = set()
        for item in self.rows:
            if (type(item) is not tuple or len(item) != 2 or
                    type(item[0]) is not int or item[0] not in y_ids or
                    item[0] in row_ids or type(item[1]) is not tuple):
                raise ValueError('invalid or duplicate packet row')
            row_ids.add(item[0])
            column_ids = set()
            for term in item[1]:
                if (type(term) is not tuple or len(term) != 2 or
                        type(term[0]) is not int or term[0] not in x_ids or
                        term[0] in column_ids):
                    raise ValueError('invalid or duplicate local column reference')
                column_ids.add(term[0])
                coefficient(term[1])
        if row_ids != y_ids:
            raise ValueError('packet rows must cover each row variable once')

        for modes, target in ((self.target_modes, True), (self.source_modes, False)):
            if type(modes) is not tuple:
                raise ValueError('packet modes must be immutable')
            mode_ids = set()
            for mode in modes:
                if (type(mode) is not tuple or len(mode) != 3 or
                        type(mode[0]) is not int or mode[0] < 0 or mode[0] in mode_ids or
                        type(mode[1]) is not int or mode[1] < 0 or type(mode[2]) is not tuple):
                    raise ValueError('invalid packet mode id or exponent')
                mode_ids.add(mode[0])
                seen = set()
                for entry in mode[2]:
                    if (type(entry) is not tuple or len(entry) != 2 or
                            type(entry[0]) is not int or
                            entry[0] not in (y_ids if target else x_ids) or
                            entry[0] in seen):
                        raise ValueError('invalid or duplicate packet mode reference')
                    seen.add(entry[0])
                    if target:
                        coefficient(entry[1])
                    elif type(entry[1]) is not int:
                        raise ValueError('source mode coefficient must be an integer')

    def _inputs(self, port_bits, budget):
        if len(port_bits) != len(self.ports):
            raise ValueError('packet tensor entry has the wrong Boolean index')
        for bit in port_bits:
            budget.tick()
            if type(bit) is not int or bit not in (0, 1):
                raise ValueError('packet tensor entry has the wrong Boolean index')
        assignment = dict(zip(self.ports, port_bits))
        x_value = {edge: assignment[port] for port, (kind, edge) in zip(self.ports, self.variables)
                   if kind == 'X'}
        y_value = {edge: assignment[port] for port, (kind, edge) in zip(self.ports, self.variables)
                   if kind == 'Y'}
        return x_value, y_value

    def _target_coefficient_streaming(self, x_value, y_value, jets, budget):
        """Enumerate affine-row selections, retaining one selection at a time."""
        active_list = []
        for mid, exponent, entries in self.target_modes:
            budget.tick()
            if exponent:
                active_list.append((mid, exponent, entries))
        active = tuple(active_list)
        target = tuple(exponent for _, exponent, _ in active)
        # Every row factor is affine, so one row can contribute at most one
        # target mode. This also handles positive exponents with no rows.
        if sum(target) > len(self.rows):
            return jets.zero
        choices = []
        for row_id, encoded_local in self.rows:
            budget.tick()
            local = jets.zero
            for column_id, encoded in encoded_local:
                budget.tick()
                if x_value.get(column_id, 0):
                    local = jets.add(local, jets.elem(encoded))
            is_one = y_value.get(row_id, 0)
            constant = local if is_one else jets.sub(jets.one, local)
            row_coefficients = {}
            for mid, _, entries in active:
                budget.tick()
                for rid, encoded in entries:
                    budget.tick()
                    if rid == row_id:
                        row_coefficients[mid] = jets.elem(encoded)
                        break
            options = []
            if constant != jets.zero:
                options.append((-1, constant))
            for index, (mid, _, _) in enumerate(active):
                coefficient = row_coefficients.get(mid, jets.zero)
                if coefficient != jets.zero:
                    options.append((index, coefficient if is_one else jets.neg(coefficient)))
            if not options:
                return jets.zero
            choices.append(tuple(options))

        # With no positive target exponents, only the constants contribute.
        # Tick even for an empty product so a deadline is still observed.
        if not active:
            budget.tick()
            result = jets.one
            for options in choices:
                budget.tick()
                result = jets.mul(result, options[0][1])
            return result

        # A first-order coefficient needs just the constant product and its
        # linear coefficient.  This is a streaming product rule, so it
        # avoids walking q different length-q selections without division.
        if len(active) == 1 and target == (1,):
            constant_product = jets.one
            coefficient = jets.zero
            for options in choices:
                budget.tick()
                constant = next((v for i, v in options if i == -1), jets.zero)
                linear = next((v for i, v in options if i == 0), jets.zero)
                coefficient = jets.add(jets.mul(coefficient, constant),
                                       jets.mul(constant_product, linear))
                constant_product = jets.mul(constant_product, constant)
            return coefficient

        result = jets.zero
        q = len(choices)
        counts = [0] * len(active)
        remaining = sum(target)
        next_choice = [0] * q
        selected = [-1] * q
        products = [jets.one] + [jets.zero] * q
        depth = 0
        # An explicit stack streams one partial row selection at a time.
        # Reject branches as soon as an exponent is exceeded or the
        # remaining rows cannot supply the remaining target degree.
        while True:
            budget.tick()
            if depth == q:
                if remaining == 0:
                    result = jets.add(result, products[depth])
                depth -= 1
                if depth < 0:
                    break
                if selected[depth] >= 0:
                    counts[selected[depth]] -= 1
                    remaining += 1
                continue
            if next_choice[depth] == len(choices[depth]):
                next_choice[depth] = 0
                if depth == 0:
                    break
                depth -= 1
                if selected[depth] >= 0:
                    counts[selected[depth]] -= 1
                    remaining += 1
                continue
            index, factor = choices[depth][next_choice[depth]]
            next_choice[depth] += 1
            if index >= 0:
                if counts[index] >= target[index]:
                    continue
                counts[index] += 1
                remaining -= 1
            if remaining > q - depth - 1:
                if index >= 0:
                    counts[index] -= 1
                    remaining += 1
                continue
            selected[depth] = index
            products[depth + 1] = jets.mul(products[depth], factor)
            depth += 1
        return result

    def _target_coefficient_dp_reference(self, x_value, y_value, jets, budget):
        """Original bounded sparse-DP coefficient evaluator for comparisons."""
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
        return polynomial.get(target, jets.zero)

    def _multiply_source(self, result, x_value, jets, budget):
        for mid, exponent, column_terms in self.source_modes:
            budget.tick()
            if exponent == 0:
                continue
            linear = 0
            for column_id, power in column_terms:
                budget.tick()
                linear += power * x_value.get(column_id, 0)
            factor = jets.elem([[linear]])
            result = jets.mul(result, _pow_jets(factor, exponent, jets, budget))
            if result == jets.zero:
                break
        return result

    def evaluate(self, port_bits: tuple[int, ...], jets: JetRing, budget: _Budget):
        x_value, y_value = self._inputs(port_bits, budget)
        result = self._target_coefficient_streaming(x_value, y_value, jets, budget)
        return self._multiply_source(result, x_value, jets, budget)

    def evaluate_dp_reference(self, port_bits: tuple[int, ...], jets: JetRing, budget: _Budget):
        """Bounded coefficient-table reference; unsuitable for space claims."""
        x_value, y_value = self._inputs(port_bits, budget)
        result = self._target_coefficient_dp_reference(x_value, y_value, jets, budget)
        return self._multiply_source(result, x_value, jets, budget)


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
    if type(exponent) is not int or exponent < 0:
        raise ValueError('jet exponent must be a nonnegative integer')
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
            real = real_packet_slots(packet, d3['L'])
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
