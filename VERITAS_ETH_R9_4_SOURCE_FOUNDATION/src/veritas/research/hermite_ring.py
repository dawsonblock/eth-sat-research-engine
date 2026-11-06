"""Precision-safe Hermite reconstruction over Z/(2**p).

This is a bounded exact-arithmetic reference for a *component* of the
manuscript's local-coordinate recovery. It does NOT implement Lemma D.5's
special asymptotic schedule or establish the ETH runtime bound.

Input jets are coefficients of F(t + alpha*z), rather than derivatives.
For integer t and alpha, the evaluation matrix has integer entries. Its
inverse has rational entries, so modular reconstruction can LOSE 2-adic
precision. We calculate a *sufficient* guard-bit bound from the exact
inverse linear functional for F(0), then refuse inadequate data.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import comb
from typing import Sequence


def _v2(x: int) -> int:
    assert x != 0
    x = abs(x)
    return (x & -x).bit_length() - 1


def modular_fraction(value: Fraction | int, bits: int) -> int:
    """Reduction of a 2-adically integral rational; reject even denominators."""
    f = Fraction(value)
    if not 1 <= bits <= 256:
        raise ValueError('precision must be 1..256')
    if f.denominator % 2 == 0:
        raise ValueError('even denominator is not invertible modulo 2^p')
    modulus = 1 << bits
    return f.numerator * pow(f.denominator, -1, modulus) % modulus


def _solve_exact(a: list[list[int]], b: list[int]) -> tuple[Fraction,...]:
    n = len(a)
    if n < 1 or n > 64 or len(b) != n or any(len(row) != n for row in a):
        raise ValueError('matrix must be square with order 1..64')
    mat = [[Fraction(e) for e in row] + [Fraction(b[i])] for i, row in enumerate(a)]
    for k in range(n):
        pivot = next((i for i in range(k,n) if mat[i][k]), None)
        if pivot is None:
            raise ValueError('singular Hermite sample system')
        mat[k], mat[pivot] = mat[pivot], mat[k]
        d = mat[k][k]
        mat[k] = [v/d for v in mat[k]]
        for i in range(n):
            if i != k and mat[i][k]:
                mul = mat[i][k]
                mat[i] = [x-mul*y for x,y in zip(mat[i],mat[k])]
    return tuple(row[-1] for row in mat)


@dataclass(frozen=True)
class HermitePlan:
    nodes: tuple[tuple[int,int], ...]
    alpha: int
    degree_bound: int
    samples_used: tuple[tuple[int,int], ...]
    weights: tuple[Fraction, ...]
    guard_bits: int


def hermite_plan(nodes: Sequence[tuple[int,int]], *, alpha: int, degree_bound: int) -> HermitePlan:
    """Exact linear recovery weights for F(0) from a sufficient collection of jets.

    Each node (t,m) provides j=0..m-1 coefficients of F(t+alpha*z).
    A prefix of exactly degree_bound+1 rows is used. Jets from the same
    node MUST be a prefix, which makes the confluent matrix nonsingular.
    The bounded dense reference supports degree at most 63 (64 samples).
    """
    if type(alpha) is not int or alpha < 1 or alpha > 256:
        raise ValueError('alpha must be a positive integer <=256')
    if type(degree_bound) is not int or not 0 <= degree_bound <= 63:
        raise ValueError('degree bound must be 0..63')
    if not nodes or len(nodes) > 32:
        raise ValueError('1..32 node descriptions required')
    specs = tuple((t,m) for t,m in nodes)
    if any(type(t) is not int or type(m) is not int or abs(t)>256 or not 1<=m<=64 for t,m in specs):
        raise ValueError('invalid node/multiplicity')
    if len({t for t,_ in specs}) != len(specs):
        raise ValueError('Hermite node positions must be distinct')
    total = degree_bound+1
    if sum(m for _,m in specs) < total:
        raise ValueError('insufficient Hermite samples for the degree bound')
    used = tuple((t,j) for t,m in specs for j in range(m))[:total]
    # Rows represent the coefficient of z^j in (t + alpha*z)^k.
    matrix = [[comb(k,j) * t**(k-j) * alpha**j if j<=k else 0
               for k in range(total)] for t,j in used]
    # Recover constant coefficient only: A^T*w=e_0.
    transposed = [[matrix[s][k] for s in range(total)] for k in range(total)]
    weights = _solve_exact(transposed, [1]+[0]*(total-1))
    guard = max((max(0, _v2(w.denominator)-_v2(w.numerator))
                 for w in weights if w), default=0)
    return HermitePlan(specs, alpha, degree_bound, used, weights, guard)


def reconstruct_mod(
    plan: HermitePlan,
    jets: Sequence[Sequence[int]],
    *,
    precision_bits: int,
    data_precision_bits: int,
) -> int:
    """Recover F(0) modulo 2^p using a certified sufficient input precision.

    The data in ``jets[i][j]`` are residues modulo 2**data_precision_bits.
    If measured precision is insufficient, this function raises ValueError
    instead of silently dividing by a nonunit modulo 2^p.
    """
    if type(precision_bits) is not int or not 1<=precision_bits<=128:
        raise ValueError('target precision must be 1..128')
    if type(data_precision_bits) is not int or not 1<=data_precision_bits<=256:
        raise ValueError('data precision must be 1..256')
    if data_precision_bits < precision_bits + plan.guard_bits:
        raise ValueError(f'insufficient data precision: require >= {precision_bits+plan.guard_bits} bits')
    if len(jets) != len(plan.nodes):
        raise ValueError('node count does not match the reconstruction plan')
    for jet, (_,m) in zip(jets, plan.nodes):
        if len(jet) < m or any(type(x) is not int or not 0 <= x < (1<<data_precision_bits) for x in jet[:m]):
            raise ValueError('missing or out-of-range modular jet coefficient')
    shift = plan.guard_bits
    mod = 1 << (precision_bits+shift)
    values = {(t,j): jets[i][j] for i,(t,m) in enumerate(plan.nodes) for j in range(m)}
    accumulator = 0
    for spec, weight in zip(plan.samples_used,plan.weights):
        # Each 2**shift*weight has odd denominator, and can be reduced as a unit.
        scaled = modular_fraction(weight*(1<<shift), precision_bits+shift)
        accumulator = (accumulator + scaled * values[spec]) % mod
    if accumulator % (1<<shift):
        raise ValueError('jet residues are incompatible with an integral F(0)')
    return (accumulator >> shift) % (1<<precision_bits)


def jets_from_polynomial(coeff: Sequence[Fraction | int], plan: HermitePlan,
                         *, data_precision_bits: int) -> tuple[tuple[int,...], ...]:
    """Independent exact polynomial expansion into local node coordinates.

    Useful for test oracles. The actual Cauchy small-reference solver has
    its *own* local jet evaluator and should be used for cross-validation.
    """
    if len(coeff)-1 > plan.degree_bound:
        raise ValueError('polynomial degree exceeds the proposed bound')
    jets = []
    for t,m in plan.nodes:
        row = []
        for j in range(m):
            value = sum((Fraction(c)*comb(k,j)*t**(k-j)*plan.alpha**j
                         for k,c in enumerate(coeff) if k>=j), Fraction(0))
            row.append(modular_fraction(value, data_precision_bits))
        jets.append(tuple(row))
    return tuple(jets)
