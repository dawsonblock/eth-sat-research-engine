"""Bounded direct coefficient oracle for one geometric-mode tuple.

This reference enumerates parent half-wire assignments and row selections.
It does not use the lazy packet tensor coefficient dynamic program. Its
exponential work makes it suitable only for checking very small networks.
"""
from itertools import product

from .lazy_children import _Budget
from .point_children import _ring_for
from veritas.research.eth_packing_v26.implicit import real_packet_slots


def direct_tuple_contribution(parent, certificate, beta, *, max_work=250_000,
                              timeout_s=10.0, _source_validation='canonical',
                              _source_work=1_000_000):
    """Return the exact coefficient contribution of one retained tuple.

    The mode certificate is checked first. The reference then enumerates both
    parent half-wire assignments and all affine row selections for each packet.
    It never evaluates a generated child or its packet-entry recipe.
    """
    ring, source = _ring_for(parent, certificate, max_parent_wires=3,
                             _source_validation=_source_validation, _source_work=_source_work)
    modes = certificate['modes']
    if (not isinstance(beta, (tuple, list)) or len(beta) != len(modes) or
            any(type(value) is not int or value < 0 for value in beta)):
        raise ValueError('beta must contain one nonnegative exponent per mode')
    if sum(value * mode['weight'] for value, mode in zip(beta, modes)) >= ring.base.p:
        raise ValueError('beta is outside the retained weighted-tuple region')
    budget = _Budget(max_work, timeout_s)
    m = parent.edges
    total = ring.zero
    for bits in product((0, 1), repeat=2*m):
        budget.tick()
        x, y = bits[:m], bits[m:]
        term = ring.one
        for vertex in parent.vertices:
            selected = y if vertex.side == 'row' else x
            value = vertex.tensor.evaluate(tuple(selected[e] for e in vertex.ports), ring, budget)
            term = ring.mul(term, value)
        for packet_id, packet in enumerate(source['packets']):
            real = real_packet_slots(packet, source['L'])
            packet_modes = [(mid, mode) for mid, mode in enumerate(modes)
                            if mode['packet'] == packet_id]
            choices = []
            for _, row_id in real:
                local = ring.zero
                for rid, cid, encoded in certificate['local']:
                    if rid == row_id and x[cid]:
                        local = ring.add(local, ring.elem(encoded))
                constant = local if y[row_id] else ring.sub(ring.one, local)
                row_choices = [(None, constant)]
                for mid, mode in packet_modes:
                    if not beta[mid]:
                        continue
                    for rid, encoded in mode['rows']:
                        if rid == row_id:
                            coefficient = ring.elem(encoded)
                            row_choices.append((mid, coefficient if y[row_id]
                                                else ring.neg(coefficient)))
                choices.append(row_choices)
            coefficient = ring.zero
            for selection in product(*choices):
                budget.tick()
                counts = {mid: 0 for mid, _ in packet_modes}
                value = ring.one
                for mid, factor in selection:
                    if mid is not None:
                        counts[mid] += 1
                    value = ring.mul(value, factor)
                if all(counts[mid] == beta[mid] for mid, _ in packet_modes):
                    coefficient = ring.add(coefficient, value)
            for mid, mode in packet_modes:
                linear = sum(power * x[cid] for cid, power in mode['column_terms'])
                factor = ring.elem([[linear]])
                for _ in range(beta[mid]):
                    budget.tick()
                    coefficient = ring.mul(coefficient, factor)
            term = ring.mul(term, coefficient)
        total = ring.add(total, term)
    return {'result': total, 'work_units': budget.used,
            'claim': 'FINITE_DIRECT_TUPLE_ORACLE_ONLY',
            'subexponential_runtime_proven': False}
