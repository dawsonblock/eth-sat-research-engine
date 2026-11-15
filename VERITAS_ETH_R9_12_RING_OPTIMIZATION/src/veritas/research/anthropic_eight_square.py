"""Anthropic / octonion eight-square crossing rewrite (experimental, finite only).

Implements σ and the crossing identities from Anthropic's 3-SAT paper (Eq. 12
and 28). These are exact signed algebraic identities used to decompose a
three-bit crossing; they are not a practical SAT solver and do not establish
any asymptotic bound for this codebase.
"""
from __future__ import annotations

Block = tuple[int, int, int]


def xor3(a: Block, b: Block) -> Block:
    return (a[0] ^ b[0], a[1] ^ b[1], a[2] ^ b[2])


def phi(p: Block, q: Block) -> int:
    """ϕ(p, q) modulo 2 (paper Appendix F)."""
    total = 0
    for i in range(3):
        for j in range(i, 3):
            total ^= p[i] & q[j]
    total ^= q[0] & p[1] & p[2]
    total ^= p[0] & q[1] & p[2]
    total ^= p[0] & p[1] & q[2]
    return total


def sigma(p: Block, q: Block) -> int:
    return 1 if phi(p, q) == 0 else -1


def indicator_equal(a: Block, b: Block) -> int:
    return 1 if a == b else 0


def indicator_xor_zero(*blocks: Block) -> int:
    acc = (0, 0, 0)
    for block in blocks:
        acc = xor3(acc, block)
    return 1 if acc == (0, 0, 0) else 0


def crossing_lhs(x: Block, y: Block, u: Block, v: Block) -> int:
    """2 [x = v] [y = u] in the paper's 0/1-valued indicator convention."""
    return 2 * indicator_equal(x, v) * indicator_equal(y, u)


def crossing_rhs(x: Block, y: Block, u: Block, v: Block) -> int:
    """Parity-weighted row/column split from Eq. (12)."""
    if not indicator_xor_zero(x, y, u, v):
        return 0
    return sigma(x, y) * sigma(v, u) + sigma(x, u) * sigma(v, y)


def crossing_terms(x: Block, y: Block, u: Block, v: Block) -> tuple[int, int]:
    """Signed row and column contributions when the four-block XOR is zero."""
    if not indicator_xor_zero(x, y, u, v):
        return 0, 0
    return sigma(x, y) * sigma(v, u), sigma(x, u) * sigma(v, y)


def identity_28_holds(p: Block, q: Block, p_prime: Block, q_prime: Block) -> bool:
    """σ(p,q)σ(p′,q′) + σ(p,q′)σ(p′,q) = 0 when p⊕q = p′⊕q′ and q ≠ q′."""
    if xor3(p, q) != xor3(p_prime, q_prime) or q == q_prime:
        return True
    left = sigma(p, q) * sigma(p_prime, q_prime)
    right = sigma(p, q_prime) * sigma(p_prime, q)
    return left + right == 0


def all_blocks() -> list[Block]:
    return [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]


def verify_crossing_identity_12() -> dict:
    """Exhaustive check of Eq. (12) over all 4096 quadruples of 3-bit blocks."""
    failures = 0
    checked = 0
    for x in all_blocks():
        for y in all_blocks():
            for u in all_blocks():
                for v in all_blocks():
                    checked += 1
                    if crossing_lhs(x, y, u, v) != crossing_rhs(x, y, u, v):
                        failures += 1
    return {
        'schema': 'ANTHROPIC_EIGHT_SQUARE_CROSSING_V1',
        'equation': '12',
        'settings_checked': checked,
        'failures': failures,
        'claim': 'FINITE_EXHAUSTIVE_IDENTITY_CHECK_ONLY',
        'subexponential_runtime_proven': False,
    }


def verify_identity_28() -> dict:
    failures = 0
    checked = 0
    for p in all_blocks():
        for q in all_blocks():
            for p_prime in all_blocks():
                for q_prime in all_blocks():
                    checked += 1
                    if not identity_28_holds(p, q, p_prime, q_prime):
                        failures += 1
    return {
        'schema': 'ANTHROPIC_EIGHT_SQUARE_PAIR_V1',
        'equation': '28',
        'settings_checked': checked,
        'failures': failures,
        'claim': 'FINITE_EXHAUSTIVE_IDENTITY_CHECK_ONLY',
        'subexponential_runtime_proven': False,
    }


def static_merge_bit_costs() -> dict:
    """Paper §2.5 edge-bit proxy for one crossing versus one rewritten term."""
    return {
        'crossing_bits': 6,
        'row_term_bits': 3,
        'column_term_bits': 6,
        'claim': 'STATIC_TOPOLOGY_PROXY_NOT_RUNTIME_MEASUREMENT',
    }


def prefer_row_merge() -> bool:
    """Row orientation needs fewer crossing bits in the simplified construction."""
    costs = static_merge_bit_costs()
    return costs['row_term_bits'] <= costs['column_term_bits']
