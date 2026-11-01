"""Finite multiplicity audit for the abstract weighted-tuple bound."""
from __future__ import annotations

from collections import Counter
from math import isqrt

from .point_modes import check_point_modes


def audit_point_mode_multiplicity(certificate):
    """Check the source's per-weight multiplicity inequality for one call.

    The returned exponent is a proved abstract upper bound conditional on the
    observed multiplicities.  It is not a bound on total solver runtime.
    """
    checked = check_point_modes(certificate)
    if checked.get('valid') is not True:
        return {'valid': False, 'status': 'INVALID_POINT_MODES'}
    source = certificate['d3_certificate']
    node = certificate['node']
    i = (abs(node) & -abs(node)).bit_length() - 1
    D = 1 << (source['a'] - i)
    M = source['M']
    counts = Counter(mode['weight'] for mode in certificate['modes'])
    multiplicity_ok = all(count * D <= 6 * M for count in counts.values())
    if not multiplicity_ok:
        return {'valid': False, 'status': 'MULTIPLICITY_HYPOTHESIS_NOT_MET',
                'counts': tuple(sorted(counts.items())), 'D': D, 'M': M}
    K = (6 * M + D - 1) // D
    n = K * certificate['precision']
    root = isqrt(n)
    if root * root < n:
        root += 1
    # The accompanying proof shows N < exp(3 sqrt(Kp)) < 2^(5 ceil sqrt(Kp)).
    return {'valid': True, 'status': 'FINITE_MULTIPLICITY_BOUND_CHECKED',
            'counts': tuple(sorted(counts.items())), 'D': D, 'M': M,
            'integer_multiplicity_cap': K, 'tuple_count_upper_power_of_two': 5 * root,
            'total_runtime_proven': False, 'uniform_packing_proven': False}
