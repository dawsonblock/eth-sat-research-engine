"""Small, exact reproduction of the manuscript's *local Cauchy deformation*.

Reference: OpenAI, The Exponential Time Hypothesis is False (25 Oct 2026),
appendix D.4.3, formulas (76) and (77).  Here we reproduce the actual
kernel W_xy(T)=C(T)/[C'(0)*(T-(y-x))] and the resulting polynomial F(T)
for a tiny bipartite CNF tensor network.

IMPORTANT: this is exhaustive 4**M half-edge enumeration, with NO packet
collision-packing, finite-field interpolation, valuation-weighted *modes*,
child networks or subexponential runtime.  Results are exact rational
polynomials, not numerical fits or approximate probabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import comb
from time import monotonic
from typing import Sequence

from veritas.research.tensor import TensorNetwork, brute_contract
from veritas.research.algebra import two_adic_valuation


Number = int | Fraction


def _mul(a: Sequence[Number], b: Sequence[Number], cap: int | None = None) -> tuple[Number, ...]:
    n = min(len(a) + len(b) - 1, cap) if cap is not None else len(a) + len(b) - 1
    out: list[Number] = [0] * n
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if i + j >= n:
                    break
                if y:
                    out[i + j] += x * y
    return tuple(out)


def _add_into(target: list[Number], source: Sequence[Number], coefficient: Number = 1) -> None:
    for i, c in enumerate(source):
        target[i] += coefficient * c


def _poly_eval(coeff: Sequence[Number], point: Number) -> Number:
    val: Number = 0
    for c in reversed(coeff):
        val = val * point + c
    return val


def _trim(a: Sequence[Number]) -> tuple[Number, ...]:
    ret = list(a)
    while len(ret) > 1 and not ret[-1]:
        ret.pop()
    return tuple(ret)


def _polynomial_shift(coeff: Sequence[Number], t: int, alpha: int, cap: int | None = None) -> tuple[Number, ...]:
    """Coefficients of P(t+alpha*z) in exact arithmetic."""
    limit = len(coeff) if cap is None else min(cap, len(coeff))
    out: list[Number] = [0] * limit
    for j, c in enumerate(coeff):
        if c:
            for k in range(min(j, limit-1) + 1):
                out[k] += c * comb(j, k) * t**(j-k) * alpha**k
    return tuple(out)


def _valid_L(L: int) -> None:
    if type(L) is not int or L not in (1, 2, 4, 8):
        raise ValueError('packet_size must be a power of two from {1,2,4,8}')


def cauchy_kernel(L: int) -> tuple[tuple[tuple[Fraction, ...], ...], ...]:
    """Exact rational coefficient matrix W[row][column][degree]."""
    _valid_L(L)
    roots = tuple(range(-L, L))
    derivative_at_zero = 1
    for root in roots:
        if root != 0:
            derivative_at_zero *= -root
    rows = []
    for row in range(L):
        columns = []
        for col in range(L):
            difference = col - row
            result: tuple[Number, ...] = (1,)
            for root in roots:
                if root != difference:
                    result = _mul(result, (-root, 1))
            columns.append(tuple(Fraction(c, derivative_at_zero) for c in result))
        rows.append(tuple(columns))
    assert all(_poly_eval(rows[i][j], 0) == int(i == j)
               for i in range(L) for j in range(L))
    return tuple(rows)


def shifted_integral_kernel(L: int, t: int, *, max_order: int | None = None) -> tuple:
    """Return W(t + 2L*z) with 2-adically integral coefficients for t in S.

    The local integral-coordinate lemma applies at these integer nodes.
    Odd denominators are units in Z_2, even if coefficients are not
    ordinary integers. This routine checks the 2-adic integrality condition.
    """
    _valid_L(L)
    if type(t) is not int or t not in range(-L, L):
        raise ValueError('node t must belong to {-L,...,L-1}')
    if max_order is not None and (type(max_order) is not int or not 1 <= max_order <= 128):
        raise ValueError('max_order must be 1..128')
    matrix = cauchy_kernel(L)
    rows = []
    for row in matrix:
        columns = []
        for poly in row:
            shifted = _polynomial_shift(poly, t, 2*L, max_order)
            if any(Fraction(c).denominator % 2 == 0 for c in shifted):
                raise AssertionError('paper local integrality invariant failed')
            columns.append(tuple(Fraction(c) for c in shifted))
        rows.append(tuple(columns))
    return tuple(rows)


def _factor_product(network: TensorNetwork, assignment: int, role: str) -> int:
    product = 1
    for factor in network.factors:
        is_row = factor.label.startswith('clause:')
        is_col = factor.label.startswith('variable:')
        if not (is_row or is_col):
            raise ValueError('Cauchy prototype accepts only CNF bipartite tensors')
        if is_row != (role == 'row'):
            continue
        idx = sum(1 << j for j, e in enumerate(factor.ports) if assignment & (1 << e))
        product *= factor.table[idx]
        if product == 0:
            break
    return product


@dataclass
class CauchyStats:
    nonzero_assignment_pairs: int = 0
    evaluated_pairs: int = 0
    product_multiplications: int = 0
    max_polynomial_degree: int = 0


def _contract_with_kernel(network: TensorNetwork, L: int, matrix: tuple,
                          *, degree_cap: int, timeout_s: float) -> tuple[tuple[Number, ...], CauchyStats]:
    M = network.edges
    if M > 6 or M < 0:
        raise ValueError('small Cauchy prototype supports at most six wires')
    if type(degree_cap) is not int or not 1 <= degree_cap <= 128:
        raise ValueError('invalid degree cap')
    if not 0 < timeout_s <= 30:
        raise ValueError('invalid timeout budget')
    deadline = monotonic() + timeout_s
    stats = CauchyStats()
    ret: list[Number] = [0] * degree_cap
    rows = [(m, _factor_product(network,m,'row')) for m in range(1 << M)]
    cols = [(m, _factor_product(network,m,'col')) for m in range(1 << M)]
    rows = [(m,p) for m,p in rows if p]
    cols = [(m,p) for m,p in cols if p]
    for X, B in cols:
        # z_i(T) = sum_{j in same packet} W_{ij}(T) X_j, padded slots are 0.
        z = []
        for i in range(M):
            result: list[Number] = [0] * degree_cap
            for j in range((i//L)*L, min(M, (i//L+1)*L)):
                if X & (1 << j):
                    _add_into(result, matrix[i%L][j%L])
            z.append(tuple(result))
        for Y, A in rows:
            stats.evaluated_pairs += 1
            if (stats.evaluated_pairs & 63) == 0 and monotonic() > deadline:
                raise TimeoutError('Cauchy polynomial evaluation exceeded time budget')
            p: tuple[Number, ...] = (A*B,)
            for i in range(M):
                zi = z[i]
                if Y & (1 << i):
                    li = zi
                else:
                    li = tuple((1 if k == 0 else 0) - v for k, v in enumerate(zi))
                p = _mul(p, li, degree_cap)
                stats.product_multiplications += 1
                if not any(p):
                    break
            if any(p):
                stats.nonzero_assignment_pairs += 1
                _add_into(ret,p)
    stats.max_polynomial_degree = len(_trim(ret))-1
    return tuple(ret), stats


def exact_cauchy_deformation(network: TensorNetwork, *, packet_size: int = 2,
                              max_edges: int = 5, timeout_s: float = 10.0
                              ) -> tuple[tuple[Fraction, ...], CauchyStats]:
    """Exhaustively compute formula (77), not a fast ETH contraction."""
    _valid_L(packet_size)
    if type(max_edges) is not int or not 0 <= max_edges <= 6 or network.edges > max_edges:
        raise ValueError('Cauchy prototype wire budget exceeded (<=6)')
    degree = network.edges * (2*packet_size-1)
    poly, stats = _contract_with_kernel(network,packet_size,cauchy_kernel(packet_size),
                                        degree_cap=degree+1,timeout_s=timeout_s)
    if poly[0] != brute_contract(network,max_edges=6,timeout_s=timeout_s):
        raise AssertionError('Cauchy T=0 identity failed vs independent contraction')
    return tuple(Fraction(x) for x in poly), stats


def shifted_cauchy_jet_mod(network: TensorNetwork, *, packet_size: int = 2, node: int = 0,
                           precision_bits: int = 8, jet_order: int = 4,
                           max_edges: int = 5, timeout_s: float = 10.0
                           ) -> tuple[tuple[int, ...], CauchyStats]:
    """Compute F(node+2L*z) modulo (2**precision_bits, z**jet_order).

    All kernel coefficients are 2-adically integral (odd denominators) at permitted nodes. Terms
    with valuation >= precision vanish exactly; this is NOT the manuscript's
    weighted mode-pruning algorithm.
    """
    _valid_L(packet_size)
    if type(precision_bits) is not int or not 1 <= precision_bits <= 256:
        raise ValueError('precision_bits must be 1..256')
    if type(jet_order) is not int or not 1 <= jet_order <= 24:
        raise ValueError('jet_order must be 1..24')
    if type(max_edges) is not int or not 0 <= max_edges <= 6 or network.edges > max_edges:
        raise ValueError('Cauchy prototype wire budget exceeded (<=6)')
    mat = shifted_integral_kernel(packet_size, node, max_order=jet_order)
    result, stats = _contract_with_kernel(network, packet_size, mat, degree_cap=jet_order, timeout_s=timeout_s)
    modulus = 1 << precision_bits
    def residue(value: Number) -> int:
        q = Fraction(value)
        if q.denominator % 2 == 0:
            raise AssertionError('non-integral 2-adic coefficient')
        return (q.numerator * pow(q.denominator, -1, modulus)) % modulus
    return tuple(residue(v) for v in result), stats


def coefficient_valuations(coefficients: Sequence[int], precision_bits: int) -> tuple[int | None,...]:
    """Return valuation up to p, with None for coefficients zero mod 2**p."""
    if type(precision_bits) is not int or not 1 <= precision_bits <= 64:
        raise ValueError('invalid precision')
    modulus = 1 << precision_bits
    return tuple(two_adic_valuation(v % modulus) if v % modulus else None for v in coefficients)


def verify_cauchy_small(network: TensorNetwork, coefficients: Sequence[Fraction], L: int,
                        *, timeout_s: float = 10.0) -> dict:
    """Independent evaluation at special nodes, not a full polynomial certificate."""
    _valid_L(L)
    if len(coefficients) != network.edges*(2*L-1)+1:
        raise ValueError('incorrect polynomial degree bound')
    deadline = monotonic() + timeout_s
    def remaining() -> float:
        duration = deadline - monotonic()
        if duration <= 0:
            raise TimeoutError('Cauchy invariant checking exceeded time budget')
        return duration
    expected_count = brute_contract(network,max_edges=6,timeout_s=remaining())
    if coefficients[0] != expected_count:
        raise AssertionError('Cauchy original-count invariant mismatch')
    matrix = cauchy_kernel(L)
    nodes = []
    for t in range(-L,L):
        # Check the prescribed unique column-shift structure in every row.
        for i in range(L):
            for j in range(L):
                if j-i != t and _poly_eval(matrix[i][j],t) != 0:
                    raise AssertionError('Cauchy grid sparsity invariant failed')
        # Evaluate F(t) independently using *constant* kernels.
        point_mat = tuple(tuple(( _poly_eval(entry,t), ) for entry in row) for row in matrix)
        direct, _ = _contract_with_kernel(network,L,point_mat,degree_cap=1,timeout_s=remaining())
        polynomial = _poly_eval(coefficients,t)
        if direct[0] != polynomial:
            raise AssertionError('Cauchy special-node evaluation mismatch')
        nodes.append({'node':t,'value':str(polynomial)})
    return {'original_count':str(expected_count),'grid_nodes_checked':nodes,
            'grid_shift_sparsity_checked':True,
            'warning':'No subexponential algorithm or recursive Cauchy mode contraction is implemented'}
