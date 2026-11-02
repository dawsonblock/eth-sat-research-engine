"""Exact numeric preflight for the finite tapered parameter formulas."""
from __future__ import annotations


def inspect_finite_schedule(wires, packet_exponent, u, target_precision, *,
                            max_precision_bits=1024):
    """Report point and guard requirements without building a contraction.

    This is arithmetic on caller-supplied scaled parameters, not validation
    of the manuscript's depth-dependent theorem schedule or packing lemma.
    """
    values = (wires, packet_exponent, u, target_precision, max_precision_bits)
    if any(type(value) is not int for value in values):
        raise ValueError('integer schedule parameters required')
    if (not 1 <= wires <= 1_000_000 or not 1 <= packet_exponent <= 8 or
            not 1 <= u <= min(packet_exponent, wires) or target_precision < 1 or
            max_precision_bits < 1):
        raise ValueError('finite schedule parameters outside supported preflight range')
    L = 1 << packet_exponent
    h = (3 * wires + u - 1) // u
    degree = wires * (2 * L - 1)
    points = degree + 1
    extension_degree = (points - 1).bit_length()
    nodes = []
    for t in range(-L, L):
        if not t:
            continue
        i = (abs(t) & -abs(t)).bit_length() - 1
        if i >= u:
            continue
        precision = target_precision + 8 * h * (L >> i) + 8 * wires * (packet_exponent + 1)
        nodes.append({'node': t, 'valuation': i, 'multiplicity': h * (u - i),
                      'required_precision_bits': precision})
    maximum = max(node['required_precision_bits'] for node in nodes)
    return {'claim': 'FINITE_NUMERIC_SCHEDULE_PREFLIGHT_ONLY',
            'wires': wires, 'packet_exponent': packet_exponent, 'u': u, 'L': L, 'h': h,
            'degree_bound': degree, 'interpolation_points': points,
            'minimum_extension_degree': extension_degree, 'nodes': nodes,
            'maximum_required_precision_bits': maximum,
            'precision_within_cap': maximum <= max_precision_bits,
            'theorem_schedule_verified': False}
