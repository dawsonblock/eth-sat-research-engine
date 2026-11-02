"""Faithful exact-integer reference for Anthropic 2026, paper.pdf, Eqs. (27)-(32).

NOT an implementation of the subexponential #SAT algorithm. Implements its
three-bit octonionic sign identity, crossing decomposition, and polynomial
coefficient construction. Every operation is exact integer arithmetic.
"""
from __future__ import annotations


def sigma(p: int, q: int) -> int:
    """Equation (27), p,q interpreted as three little-endian bits."""
    if not 0 <= p < 8 or not 0 <= q < 8:
        raise ValueError('sigma expects 3-bit blocks (0..7)')
    pb = [(p >> i) & 1 for i in range(3)]
    qb = [(q >> i) & 1 for i in range(3)]
    parity = sum(pb[i] * qb[j] for i in range(3) for j in range(i, 3))
    parity += qb[0] * pb[1] * pb[2]
    parity += pb[0] * qb[1] * pb[2]
    parity += pb[0] * pb[1] * qb[2]
    return -1 if parity & 1 else 1


def psi(k: int, p: int, q: int) -> int:
    """Equation (30), psi_k(p,q) = [p xor q == k] sigma(p,q)."""
    if not 0 <= k < 8:
        raise ValueError('k must be 3-bit')
    return sigma(p, q) if (p ^ q) == k else 0


def crossing_row(x: int, y: int, u: int, v: int) -> int:
    """R(x,y,u,v): sum_k psi_k(x,y) psi_k(v,u)."""
    return sum(psi(k, x, y) * psi(k, v, u) for k in range(8))


def crossing_col(x: int, y: int, u: int, v: int) -> int:
    """C(x,y,u,v): sum_k psi_k(x,u) psi_k(v,y)."""
    return sum(psi(k, x, u) * psi(k, v, y) for k in range(8))


def crossing_direct(x: int, y: int, u: int, v: int) -> int:
    """2*[x=v]*[y=u]; useful independent exact oracle for Eq. (31)."""
    return 2 if x == v and y == u else 0


def crossing_coefficients(x: int, y: int, u: int, v: int, width: int) -> tuple[int, ...]:
    """Equation (32): coefficients A_0..A_t of product_s (R_s + T*C_s).

    x,y,u,v represent width-bit strings, chunked into 3-bit blocks, with
    zero-padding above width as in Definition 5. Returns t+1 integers.
    """
    if width < 1:
        raise ValueError('width >= 1')
    mask = (1 << width) - 1
    if any(z < 0 or z > mask for z in (x, y, u, v)):
        raise ValueError('strings must be nonnegative and fit in width bits')
    t = (width + 2) // 3
    coefficients = [1]
    for block in range(t):
        shift = 3 * block
        xb, yb, ub, vb = ((z >> shift) & 7 for z in (x, y, u, v))
        r, c = crossing_row(xb, yb, ub, vb), crossing_col(xb, yb, ub, vb)
        product = [0] * (len(coefficients) + 1)
        for i, value in enumerate(coefficients):
            product[i] += value * r
            product[i + 1] += value * c
        coefficients = product
    return tuple(coefficients)


def rectangle_identity(x: int, y: int, u: int, v: int, width: int) -> bool:
    """Lemma 2(a): sum_i A_i = 2^ceil(width/3) * [x=v]*[y=u]."""
    coeff = crossing_coefficients(x,y,u,v,width)
    t = (width + 2) // 3
    right = (1 << t) if (x == v and y == u) else 0
    return sum(coeff) == right and all(abs(a) <= (1 << t) for a in coeff)
