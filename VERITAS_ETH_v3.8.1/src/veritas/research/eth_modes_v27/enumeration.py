"""Lazy exact enumeration of the D.4.4 *weight inequality*, not a runtime proof.

Enumerate nonnegative beta with sum(weight_i * beta_i) < precision.
The zero continuation always exists. Hard caps prevent unbounded expansion.
"""
from __future__ import annotations

class ModeBudgetExceeded(ValueError):
    """The finite reference would exceed a declared work/memory cap."""


def count_tuples(weights, precision, *, cap=1_000_000):
    if type(precision) is not int or not 1 <= precision <= 256:
        raise ValueError('precision must be in [1,256]')
    if type(cap) is not int or cap < 1:
        raise ValueError('invalid cap')
    if any(type(w) is not int or w < 1 for w in weights):
        raise ValueError('mode weights must be positive integers')
    # dp[s] counts choices with exactly weight s; no enumeration of vectors.
    dp = [0] * precision
    dp[0] = 1
    for w in weights:
        if w < precision:
            for s in range(w, precision):
                dp[s] += dp[s-w]
                if dp[s] > cap:
                    raise ModeBudgetExceeded('weighted mode count exceeds cap')
        if sum(dp) > cap:
            raise ModeBudgetExceeded('weighted mode count exceeds cap')
    return sum(dp)


def weighted_tuples(weights, precision, *, max_tuples=100_000):
    weights = tuple(weights)
    count_tuples(weights, precision, cap=max_tuples)
    state = [0] * len(weights)

    def visit(k, remaining):
        if k == len(weights):
            yield tuple(state)
            return
        w = weights[k]
        for exponent in range((remaining-1)//w+1):
            state[k] = exponent
            yield from visit(k+1,remaining-w*exponent)
        state[k] = 0

    yield from visit(0,precision)
