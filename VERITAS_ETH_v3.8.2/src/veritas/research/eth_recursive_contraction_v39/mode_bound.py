"""Finite multiplicity audit for the abstract weighted-tuple bound."""
from __future__ import annotations

from collections import Counter
from math import isqrt

from .point_modes import check_point_modes


def weighted_tuple_upper_exponent(multiplicity_numerator, multiplicity_denominator,
                                  precision):
    """Return E with N <= 2**E under a per-weight multiplicity hypothesis.

    The hypothesis is that there are at most numerator/denominator distinct
    modes of each positive integer weight. N counts exponent tuples whose
    weighted sum is strictly less than precision. This is a counting bound,
    not a guarantee that any particular construction meets the hypothesis.
    All rounding is performed with integer arithmetic.
    """
    if (type(multiplicity_numerator) is not int or multiplicity_numerator < 0 or
            type(multiplicity_denominator) is not int or multiplicity_denominator < 1 or
            type(precision) is not int or precision < 1):
        raise ValueError('nonnegative rational multiplicity and positive precision required')
    numerator = 16 * multiplicity_numerator * precision
    root = isqrt(numerator // multiplicity_denominator)
    if root * root * multiplicity_denominator < numerator:
        root += 1
    return root


def _audit_point_mode_multiplicity(certificate, *, max_parent_wires,
                                   source_validation, source_work):
    """Check the source's per-weight multiplicity inequality for one call.

    The returned exponent is a proved abstract upper bound conditional on the
    observed multiplicities.  It is not a bound on total solver runtime.
    """
    checked = check_point_modes(certificate, max_parent_wires=max_parent_wires,
                                _source_validation=source_validation, _source_work=source_work)
    if checked.get('valid') is not True:
        return {'valid': False, 'status': checked.get('status', 'INVALID_POINT_MODES'),
                'reason': checked.get('reason')}
    source = certificate['d3_certificate']
    node = certificate['node']
    i = (abs(node) & -abs(node)).bit_length() - 1
    D = 1 << (source['a'] - i)
    M = source['M']
    counts = Counter(mode['weight'] for mode in certificate['modes'])
    packet_counts = Counter((mode['packet'], mode['weight']) for mode in certificate['modes'])
    mode_bearing_packets = len({packet for packet, _weight in packet_counts})
    per_packet_weight_limit = 1 << (i + 1)
    if any(count > per_packet_weight_limit for count in packet_counts.values()):
        return {'valid': False, 'status': 'GEOMETRIC_TILE_BOUND_NOT_MET',
                'per_packet_weight_limit': per_packet_weight_limit}
    multiplicity_ok = all(count * D <= 6 * M for count in counts.values())
    if not multiplicity_ok:
        return {'valid': False, 'status': 'MULTIPLICITY_HYPOTHESIS_NOT_MET',
                'counts': tuple(sorted(counts.items())), 'D': D, 'M': M}
    K = (6 * M + D - 1) // D
    # The accompanying proof gives log_2 N < 4 sqrt((6M/D) p).
    # Keep 6M/D as a rational rather than rounding it up before the root.
    exponent = weighted_tuple_upper_exponent(6 * M, D, certificate['precision'])
    nominal = certificate['mode_tuple_count']
    structural = certificate['structural_tuple_count']
    if not (0 <= structural <= nominal <= (1 << exponent)):
        return {'valid': False, 'status': 'TUPLE_COUNT_BOUND_NOT_MET'}
    return {'valid': True, 'status': 'FINITE_MULTIPLICITY_BOUND_CHECKED',
            'counts': tuple(sorted(counts.items())), 'D': D, 'M': M,
            'source_validation': source_validation,
            'mode_bearing_packets': mode_bearing_packets,
            'per_packet_weight_limit': per_packet_weight_limit,
            'per_packet_weight_counts': tuple((packet, weight, count)
                                              for (packet, weight), count
                                              in sorted(packet_counts.items())),
            'mode_bearing_packet_sufficient_hypothesis': (
                mode_bearing_packets * source['L'] <= 3 * M),
            'padded_packet_sufficient_hypothesis': source['D'] * source['H_pad'] <= 3 * M,
            'nominal_tuple_count': nominal, 'structural_tuple_count': structural,
            'integer_multiplicity_cap': K,
            'multiplicity_cap_numerator': 6 * M,
            'multiplicity_cap_denominator': D,
            'tuple_count_upper_power_of_two': exponent,
            'total_runtime_proven': False, 'uniform_packing_proven': False}


def audit_point_mode_multiplicity(certificate, *, max_parent_wires=6):
    """Audit a canonically source-replayed finite point-mode certificate."""
    return _audit_point_mode_multiplicity(certificate, max_parent_wires=max_parent_wires,
                                          source_validation='canonical', source_work=1_000_000)


def audit_geometry_point_mode_multiplicity(certificate, *, max_parent_wires=6,
                                           max_geometry_work=1_000_000):
    """Audit independently checked sparse geometry without a canonical trace.

    Source validation and tuple work are bounded finite checks, not a proof of
    the theorem hypotheses for other inputs or a complete cost accounting.
    """
    if type(max_geometry_work) is not int or not 1 <= max_geometry_work <= 2_000_000:
        raise ValueError('finite geometry work limit must be in 1..2000000')
    return _audit_point_mode_multiplicity(certificate, max_parent_wires=max_parent_wires,
                                          source_validation='geometry', source_work=max_geometry_work)
