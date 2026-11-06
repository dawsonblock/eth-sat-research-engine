"""Exact numerical preflight for the pinned contraction schedule.

Paper objects: `eq:tensor-parameters`, the leaf threshold `H`, and the degree
bound `Delta` in `app:tensor` (historical alias "Appendix D").

This does not construct packets or implement recursive contraction. A passed
preflight is not a certificate of the packing lemma or a complexity theorem.
"""

from math import isqrt


def uniform_schedule_lemma(lambda_value: int, *, size_constant: int = 1,
                           max_integer_bits: int = 4096) -> dict:
    """Check a sufficient symbolic threshold for all active depths.

    This is conditional on the root size, child shrinkage, and degree
    invariants described in APPENDIX_D_EXPLICIT_SCHEDULE_THRESHOLD.md. It
    neither constructs s (which has lambda bits) nor proves those invariants.
    """
    if any(type(v) is not int for v in (lambda_value, size_constant, max_integer_bits)):
        raise ValueError('integer parameters required')
    if lambda_value < 1 or size_constant < 1 or max_integer_bits < 2:
        raise ValueError('parameters outside valid range')
    if (lambda_value.bit_length() > max_integer_bits or
            600 + 10 * size_constant.bit_length() > max_integer_bits):
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT'}
    threshold = (1 << 600) * size_constant ** 10
    if lambda_value < threshold:
        return {'status': 'INCONCLUSIVE_SUFFICIENT_THRESHOLD',
                'lambda_threshold': threshold}
    return {'status': 'CONDITIONAL_UNIFORM_PACKING_NUMERICS',
            'lambda_threshold': threshold, 'size_constant': size_constant,
            'requires_root_edge_bound': True,
            'requires_child_shrink_and_degree_invariants': True,
            'packing_constructor_proven': False,
            'implementation_complexity_proven': False}


def _ceil_tenth_root(n: int) -> int:
    """Return ceil(n**(1/10)) using integer arithmetic only."""
    if n < 2:
        return n
    x = 1 << ((n.bit_length() + 9) // 10)
    while True:
        y = (9 * x + n // (x ** 9)) // 10
        if y >= x:
            break
        x = y
    return x if x ** 10 == n else x + 1


def _degree_limit(s: int) -> int:
    """Return ceil(s**(9/10)) exactly, including a sparse power-of-two case.

    For s=2**(10k), the value is exactly 2**(9k). Recognizing this case
    permits reproducible schedule checks at large exponents without first
    constructing s**9 or invoking integer root iteration on it. It is a
    numeric preflight only; no network or recursive contraction is built.
    """
    exponent = s.bit_length() - 1
    if exponent % 10 == 0 and s == 1 << exponent:
        return 1 << (9 * exponent // 10)
    return _ceil_tenth_root(s ** 9)


def schedule_preflight(s: int, edges: int, degree: int, depth: int, *,
                       size_constant: int = 1, max_size_bits: int = 4096) -> dict:
    """Check one call's numeric conditions; no tensor result is computed.

    size_constant is a caller-supplied integer upper bound C for root edges.
    An eligible active call still needs the D.3 constructor and the entire
    recursive contraction. Resource or hypothesis failures are inconclusive.
    """
    values = (s, edges, degree, depth, size_constant, max_size_bits)
    if any(type(v) is not int for v in values):
        raise ValueError('integer parameters required')
    if s < 2 or edges < 0 or degree < 0 or depth < 0 or size_constant < 1 or max_size_bits < 2:
        raise ValueError('parameters outside valid range')
    if any(value.bit_length() > max_size_bits
           for value in (s, edges, degree, depth, size_constant)):
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT'}
    if degree > edges:
        return {'status': 'INVALID_DEGREE'}
    # M <= C*s/8**depth, without constructing an enormous power.
    if edges and (depth > (size_constant * s).bit_length() // 3 or
                  (edges << (3 * depth)) > size_constant * s):
        return {'status': 'INVALID_RECURSIVE_SIZE_BOUND'}
    lam = (s - 1).bit_length()
    leaf_threshold = (s + isqrt(lam) - 1) // isqrt(lam)
    delta = _degree_limit(s)
    if degree > delta:
        return {'status': 'INVALID_DEGREE_BOUND', 'degree_limit': delta}
    common = {'lambda': lam, 'leaf_threshold': leaf_threshold,
              'degree_limit': delta, 'depth': depth, 'edges': edges,
              'packing_proven': False, 'complexity_proven': False}
    if edges <= leaf_threshold:
        return dict(common, status='DIRECT_LEAF_ALLOWED')
    # floor(lambda/(131072 * 2**d)), without giant shifts at deep nodes.
    base = lam // 131072
    u = base >> depth if depth < base.bit_length() else 0
    if u == 0:
        return dict(common, status='INCONCLUSIVE_SCHEDULE', u=u)
    a = 2 * sum(base >> j for j in range(min(depth + 1, base.bit_length())))
    # r=64, L=2**a, D=r**(2*a)=2**(12*a).
    checks = {
        'M_ge_2_D_squared_delta': (edges >> (1 + 24 * a)) >= delta,
        'M_ge_LD': (edges >> (13 * a)) >= 1,
        '2L_le_delta': (delta >> (a + 1)) >= 1,
    }
    return dict(common, status=('ACTIVE_NUMERIC_PRECONDITIONS_MET'
                                if all(checks.values()) else 'INCONCLUSIVE_PACKING'),
                u=u, a=a, packet_size_exponent=a, label_class_exponent=12*a,
                numeric_preconditions=checks)


def schedule_path_preflight(s: int, states, *, size_constant: int = 1,
                            max_size_bits: int = 4096, max_calls: int = 1024) -> dict:
    """Check the numeric schedule along one explicitly supplied ancestry.

    ``states[d]`` is ``(wire_count, maximum_degree)`` for the call at depth
    ``d``. The caller supplies these numbers; this routine does not inspect
    network descriptions, prove their origin, or establish that all branches
    were provided. It checks every adjacent 3/32 shrink bound and prevents
    descendants after the prescribed direct leaf. An active final call is
    permitted because the supplied path may be an unfinished prefix.
    """
    if type(max_calls) is not int or max_calls < 1:
        raise ValueError('max_calls must be a positive integer')
    if not isinstance(states, (tuple, list)) or not states:
        raise ValueError('a nonempty sequence of call states is required')
    if len(states) > max_calls:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'path length exceeds limit'}
    normalized = []
    for state in states:
        if (not isinstance(state, (tuple, list)) or len(state) != 2 or
                any(type(value) is not int or value < 0 for value in state)):
            raise ValueError('each call state must contain nonnegative integer wires and degree')
        normalized.append(tuple(state))

    calls = []
    for depth, (edges, degree) in enumerate(normalized):
        check = schedule_preflight(s, edges, degree, depth,
                                   size_constant=size_constant,
                                   max_size_bits=max_size_bits)
        calls.append(check)
        if check['status'] not in ('DIRECT_LEAF_ALLOWED', 'ACTIVE_NUMERIC_PRECONDITIONS_MET'):
            return {'status': check['status'], 'depth': depth, 'calls': calls}
        if depth:
            parent_edges = normalized[depth - 1][0]
            if 32 * edges > 3 * parent_edges:
                return {'status': 'INVALID_CHILD_SHRINK', 'depth': depth,
                        'parent_edges': parent_edges, 'child_edges': edges,
                        'calls': calls}
        if check['status'] == 'DIRECT_LEAF_ALLOWED':
            if depth != len(normalized) - 1:
                return {'status': 'INVALID_CHILD_AFTER_LEAF', 'depth': depth,
                        'calls': calls}
    return {'status': 'FINITE_SCHEDULE_PATH_NUMERICS_CHECKED', 'calls': calls,
            'ends_at_leaf': calls[-1]['status'] == 'DIRECT_LEAF_ALLOWED',
            'network_descriptions_verified': False,
            'child_identities_verified': False,
            'all_branches_verified': False,
            'uniform_theorem_proven': False}
