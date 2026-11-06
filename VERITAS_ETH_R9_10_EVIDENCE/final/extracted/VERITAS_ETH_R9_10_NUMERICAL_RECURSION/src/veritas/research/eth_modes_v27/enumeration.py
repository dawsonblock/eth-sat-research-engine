"""Lazy exact enumeration of the D.4.4 *weight inequality*, not a runtime proof.

Enumerate nonnegative beta with sum(weight_i * beta_i) < precision.
The zero continuation always exists. Hard caps prevent unbounded expansion.
"""
from __future__ import annotations

class ModeBudgetExceeded(ValueError):
    """The finite reference would exceed a declared work/memory cap."""


def count_tuples(weights, precision, *, cap=1_000_000):
    if type(precision) is not int or not 1 <= precision <= 1024:
        raise ValueError('precision must be in [1,1024]')
    if type(cap) is not int or cap < 1:
        raise ValueError('invalid cap')
    # Validate and count the same data even when the caller supplies a
    # one-shot iterator.
    weights = tuple(weights)
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
    n = len(weights)
    if n == 0:
        yield ()
        return
    # Explicit DFS preserves the recursive enumerator's order without tying
    # the supported number of modes to Python's recursion limit. Every
    # visited prefix extends to an admissible tuple by filling with zeroes.
    state = [0] * n
    next_exponent = [0] * n
    remaining = [precision] * (n + 1)
    depth = 0
    while depth >= 0:
        if depth == n:
            yield tuple(state)
            depth -= 1
            continue
        limit = (remaining[depth] - 1) // weights[depth]
        if next_exponent[depth] > limit:
            next_exponent[depth] = 0
            depth -= 1
            continue
        exponent = next_exponent[depth]
        next_exponent[depth] += 1
        state[depth] = exponent
        remaining[depth + 1] = remaining[depth] - weights[depth] * exponent
        depth += 1
