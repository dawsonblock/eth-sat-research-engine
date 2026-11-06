"""Bounded exact Hermite recovery weights via polynomial CRT.

This constructs the same constant-term functional as the dense rational
reference, without solving a confluent linear system. It does not prove the
paper's tapered loss bound or an end-to-end bit-complexity claim.
"""
from fractions import Fraction
from math import comb

from veritas.research.hermite_ring import HermitePlan


def hermite_crt_plan(nodes, *, alpha, degree_bound, max_samples=64):
    """Recover F(0) from a prefix of coefficients of F(t+alpha*z).

    For each used node t with multiplicity m let Q_t(x) be the product of
    the other nodes' factors. The inverse of Q_t(t+y) modulo y**m yields
    the standard confluent CRT idempotent. Evaluating the resulting linear
    functional at x=0 supplies one rational weight per used coefficient.
    All computation is exact over Q; no even residue denominator is inverted.
    """
    if type(max_samples) is not int or not 1 <= max_samples <= 64:
        raise ValueError('sample cap must be in 1..64')
    if type(alpha) is not int or not 1 <= alpha <= 256:
        raise ValueError('alpha must be a positive integer <=256')
    if type(degree_bound) is not int or not 0 <= degree_bound < max_samples:
        raise ValueError('degree exceeds sample cap')
    if not isinstance(nodes, (tuple, list)) or not 1 <= len(nodes) <= 32:
        raise ValueError('1..32 node descriptions required')
    specs = []
    for node in nodes:
        if (not isinstance(node, (tuple, list)) or len(node) != 2 or
                type(node[0]) is not int or type(node[1]) is not int or
                abs(node[0]) > 256 or not 1 <= node[1] <= 64):
            raise ValueError('invalid node or multiplicity')
        specs.append(tuple(node))
    specs = tuple(specs)
    if len({t for t, _ in specs}) != len(specs):
        raise ValueError('node positions must be distinct')
    needed = degree_bound + 1
    if sum(m for _, m in specs) < needed:
        raise ValueError('insufficient Hermite samples')
    used = []
    counts = []
    remaining = needed
    for t, multiplicity in specs:
        count = min(multiplicity, remaining)
        if count:
            counts.append((t, count))
            used.extend((t, j) for j in range(count))
            remaining -= count
        if remaining == 0:
            break
    weights = []
    for t, multiplicity in counts:
        # q[k] is [y^k] Q_t(t+y), truncated modulo y^multiplicity.
        q = [1] + [0] * (multiplicity - 1)
        q_at_zero = 1
        for other, other_multiplicity in counts:
            if other == t:
                continue
            delta = t - other
            factor = [comb(other_multiplicity, k) * delta ** (other_multiplicity-k)
                      for k in range(min(multiplicity-1, other_multiplicity)+1)]
            product = [0] * multiplicity
            for i, left in enumerate(q):
                for j, right in enumerate(factor[:multiplicity-i]):
                    product[i+j] += left * right
            q = product
            q_at_zero *= (-other) ** other_multiplicity
        inverse = [Fraction(1, q[0])]
        for n in range(1, multiplicity):
            inverse.append(-sum((q[k] * inverse[n-k] for k in range(1, n+1)),
                                Fraction(0)) / q[0])
        for j in range(multiplicity):
            series = sum((inverse[k] * (-t) ** k for k in range(multiplicity-j)), Fraction(0))
            weights.append(Fraction(q_at_zero * (-t) ** j, alpha ** j) * series)
    guard = max((max(0, ((w.denominator & -w.denominator).bit_length() - 1) -
                          ((abs(w.numerator) & -abs(w.numerator)).bit_length() - 1))
                 for w in weights if w), default=0)
    return HermitePlan(specs, alpha, degree_bound, tuple(used), tuple(weights), guard)
