"""Exact arithmetic for the sparse-polynomial counting construction.

Implements the pieces of `lem:rational-idempotent` and `lem:tensor-sparse-query`
of the pinned preprint: the modulus-amplifying indicator polynomials e_j, the
lifted equation factors B_i(V) at integer arguments, the multilinear coefficient
inversion over incidence subsets, and the lexicographic subset indexing used by
the indexed-wire networks. These are exact integer computations; the lemma's
n>=20 and asymptotic hypotheses gate the claimed bound, not the algebra.
"""
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import comb


@lru_cache(maxsize=None)
def comb_cached(n, d):
    """Memoized binomial for repeated rank/unrank and width lookups."""
    return comb(n, d)

from .parameters import natural
from .resources import ResourceLimit


def normalize_equation(monomials, n):
    """Multilinearize powers and combine duplicate monomials modulo two."""
    natural(n, 'declared variables', 1)
    parity = {}
    for monomial in monomials:
        # Validate before set insertion: bool, float and other equal-valued
        # objects can otherwise disappear behind an earlier integer index.
        indices = set()
        for v in monomial:
            if type(v) is not int or not 0 <= v < n:
                raise ValueError('monomial variable outside declared range')
            indices.add(v)
        s = frozenset(indices)
        parity[s] = parity.get(s, 0) ^ 1
    return tuple(sorted(
        (m for m, p in parity.items() if p),
        key=lambda m: (len(m), sorted(m))))


def normalize_system(n, equations):
    natural(n, 'declared variables', 1)
    if not isinstance(equations, (tuple, list)):
        raise ValueError('equation list required')
    return tuple(normalize_equation(eq, n) for eq in equations)


def scopes(system):
    """Free incidence set I_i of each equation."""
    return tuple(set().union(*eq) if eq else set() for eq in system)


def _divmod_h(poly):
    """Divide by h(Y)=Y^2-Y: returns (quotient, remainder degree<=1)."""
    rem = list(poly)
    q = [0] * max(0, len(rem) - 2)
    for i in range(len(rem) - 1, 1, -1):
        c = rem[i]
        if c:
            q[i - 2] = c
            rem[i] = 0
            rem[i - 1] += c
    while q and not q[-1]:
        q.pop()
    return q, tuple((rem + [0, 0])[:2])


def idempotent_coefficients(ell, budget=None):
    """Construct e_0..e_{ell-1} of lem:rational-idempotent.

    p_ell(Y) = (1-Y)^ell * sum_{j<ell} binom(ell+j-1, j) Y^j, divided
    successively by h = Y(Y-1) into degree-at-most-one remainders.
    """
    natural(ell, 'truncation order', 1)
    if budget is not None:
        budget.items(ell, 'idempotent coefficient list')
        budget.bits(4 * ell * ell.bit_length() + 8, 'idempotent coefficient width')
    factor_sum = [comb(ell + j - 1, j) for j in range(ell)]
    factor_pow = [(-1 if j & 1 else 1) * comb(ell, j) for j in range(ell + 1)]
    poly = [0] * (2 * ell + 1)
    for i, a in enumerate(factor_pow):
        for j, b in enumerate(factor_sum):
            poly[i + j] += a * b
    es = []
    while True:
        quotient, remainder = _divmod_h(poly)
        es.append(remainder)
        if not quotient:
            break
        poly = quotient
        if len(es) > ell:
            raise ArithmeticError('idempotent expansion degree exceeded')
    if len(es) != ell:
        raise ArithmeticError('idempotent expansion length mismatch')
    return tuple(es)


def factor_coefficients(L_value, modulus, ell, es):
    """B_i(V) evaluated at integer L: sum_j e_j(L) h(L)^j V^j mod modulus."""
    natural(ell, 'truncation order', 1)
    if type(modulus) is not int or modulus <= 0 or modulus & (modulus - 1):
        raise ValueError('power-of-two modulus required')
    h = (L_value * (L_value - 1)) % modulus
    out = []
    hp = 1
    for j in range(ell):
        a, b = es[j]
        out.append((a + b * L_value) * hp % modulus)
        hp = hp * h % modulus
    return tuple(out)


def truncated_multiply(left, right, modulus, ell):
    """Multiply in (Z/2^p)[V]/(V^ell)."""
    out = [0] * ell
    for i, x in enumerate(left):
        if x:
            for j in range(min(ell - i, len(right))):
                y = right[j]
                if y:
                    out[i + j] = (out[i + j] + x * y) % modulus
    return tuple(out)


def incidence_coefficient(monomials, subset, modulus, ell, es, budget=None):
    """[z_S] B̄_i = sum_{T<=S} (-1)^{|S|-|T|} B_i(1_T, V).

    B_i(1_T, V) is evaluated at the integer L_i(1_T) counting the normalized
    monomials contained in T; no dense multilinear expansion is materialized.
    """
    S = sorted(subset)
    acc = [0] * ell
    for mask in range(1 << len(S)):
        T = {S[i] for i in range(len(S)) if mask >> i & 1}
        L_value = sum(1 for m in monomials if m <= T)
        b = factor_coefficients(L_value, modulus, ell, es)
        negative = (len(S) - len(T)) & 1
        for j in range(ell):
            acc[j] = (acc[j] - b[j] if negative else acc[j] + b[j]) % modulus
        if budget is not None:
            budget.tick(len(S) + 1)
    return tuple(acc)


def subset_unrank(n, d, index):
    """Decode a lexicographic index into a sorted d-subset of range(n)."""
    natural(n, 'incidence count')
    natural(d, 'subset size')
    if type(index) is not int or not 0 <= index < comb_cached(n, d):
        raise ValueError('subset index out of range')
    s, r, x = [], index, 0
    for _ in range(d):
        while True:
            c = comb_cached(n - x - 1, d - len(s) - 1)
            if c <= r:
                r -= c
                x += 1
            else:
                s.append(x)
                x += 1
                break
    return tuple(s)


def subset_rank(n, subset):
    """Lexicographic index of a subset of range(n); inverse of subset_unrank."""
    s = sorted(subset)
    if any(type(v) is not int or not 0 <= v < n for v in s) or len(set(s)) != len(s):
        raise ValueError('subset outside range')
    d = len(s)
    r, prev = 0, -1
    for i, x in enumerate(s):
        for y in range(prev + 1, x):
            r += comb_cached(n - y - 1, d - i - 1)
        prev = x
    return r


def wire_bits(count):
    """Boolean wires to index a set of size `count` in lexicographic order."""
    natural(count, 'indexable size', 1)
    return (count - 1).bit_length()
