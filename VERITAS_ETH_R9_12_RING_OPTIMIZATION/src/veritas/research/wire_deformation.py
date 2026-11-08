"""Exact split-wire deformation for *small* Boolean tensor networks.

For each original edge e=(u,v), give its endpoints independent bits a_e,b_e.
Insert K_t(a,b) = 1 when a=b, else t. Then

    D_G(t) = sum_{all half-edge bits} prod_v T_v(bits(v)) prod_e K_t(a_e,b_e).

D_G(0) equals the original contraction. D_G(1) factorizes completely
into the product of the sum of each vertex tensor, and D_G(-1) into
signed local tensor sums. This is a genuine polynomial wire deformation,
BUT NOT the paper's low-degree Cauchy construction. In particular, it
requires polynomial degree |E| and generic exponentially sized tables;
there is no ETH or asymptotic speedup claim.

Methods do not share contraction logic with the independent half-edge
histogram oracle. All arithmetic is exact integer or in Z/(2**p)Z.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from typing import Sequence

from veritas.research.tensor import TensorNetwork
from veritas.research.violation_polynomial import multiply_polynomials, evaluate_polynomial, PolynomialStats


@dataclass
class WireStats:
    eliminated_half_edges: int = 0
    table_entries_evaluated: int = 0
    max_intermediate_arity: int = 0
    polynomial_multiplications: int = 0
    provably_zero_products_mod_2_power: int = 0


def _endpoint_map(network: TensorNetwork) -> list[tuple[int, ...]]:
    """Maps each vertex-local port to its unique half-edge variable."""
    counts = [0] * network.edges
    mapping: list[tuple[int, ...]] = []
    for factor in network.factors:
        ports = []
        for e in factor.ports:
            side = counts[e]
            if side >= 2:
                raise ValueError('invalid network: edge occurs more than twice')
            ports.append(2 * e + side)
            counts[e] += 1
        mapping.append(tuple(ports))
    if any(count != 2 for count in counts):
        raise ValueError('invalid network: edge missing endpoint')
    return mapping


def factorized_evaluation(network: TensorNetwork, t: int) -> int:
    """Independent rank-one evaluations at t = 1 and t = -1."""
    if type(t) is not int or t not in (1, -1):
        raise ValueError('rank-one formula applies only to t = +/-1')
    answer = 1
    for factor in network.factors:
        total = sum(((-1) ** i.bit_count() if t == -1 else 1) * coefficient
                    for i, coefficient in enumerate(factor.table))
        answer *= total
    return answer


def _order(factors: Sequence[tuple[tuple[int, ...], tuple]], remaining: set[int]) -> int:
    """Minimum-fill order with deterministic tie breaking; performance heuristic only."""
    best = None
    for edge in sorted(remaining):
        selected = [ports for ports, _ in factors if edge in ports]
        neighbors = set().union(*(set(ports) for ports in selected)) - {edge}
        existing = set()
        for ports, _ in factors:
            p = set(ports)
            for a in neighbors & p:
                for b in neighbors & p:
                    if a < b:
                        existing.add((a, b))
        missing = len(neighbors) * (len(neighbors) - 1) // 2 - len(existing)
        key = (missing, len(neighbors), edge)
        if best is None or key < best[0]:
            best = (key, edge)
    return best[1]


def deform_polynomial(network: TensorNetwork, *, precision_bits: int | None = None,
                      max_edges: int = 10, max_table_entries: int = 1 << 13,
                      timeout_s: float = 10.0) -> tuple[list[int], WireStats]:
    """Exact D_G(t) coefficients by generic polynomial-semiring elimination.

    The maximum degree is E and D_G(0)=contract(G). Hard caps limit
    research inputs, not a proof of good asymptotic complexity.
    """
    if precision_bits is not None and (type(precision_bits) is not int or not 1 <= precision_bits <= 64):
        raise ValueError('precision_bits must be 1..64')
    if type(max_edges) is not int or not 0 <= max_edges <= 12 or network.edges > max_edges:
        raise ValueError('wire-deformation edge budget exceeded (maximum 12)')
    if type(max_table_entries) is not int or not 1 <= max_table_entries <= (1 << 16):
        raise ValueError('invalid table budget')
    if not 0 < timeout_s <= 30:
        raise ValueError('invalid timeout')
    degree = network.edges
    size = degree + 1
    one = (1,) + (0,) * degree
    tpoly = (0, 1) + (0,) * (degree - 1) if degree else one
    modulus = 1 << precision_bits if precision_bits is not None else None
    stats = WireStats()
    mut_stats = PolynomialStats()
    maps = _endpoint_map(network)
    factors: list[tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]] = []
    for vertex, ports in zip(network.factors, maps):
        if len(vertex.table) > max_table_entries:
            raise ValueError('input tensor exceeds table budget')
        factors.append((ports, tuple((((x % modulus) if modulus else x),) + (0,) * degree
                                     for x in vertex.table)))
    for e in range(degree):
        factors.append(((2*e, 2*e+1), (one, tpoly, tpoly, one)))
    deadline = monotonic() + timeout_s
    remaining = set(range(2 * degree))

    while remaining:
        if monotonic() > deadline:
            raise TimeoutError('wire polynomial contraction exceeded time budget')
        edge = _order(factors, remaining)
        chosen = [(ports, table) for ports, table in factors if edge in ports]
        if not chosen:
            raise AssertionError('missing half-edge')
        factors = [(ports, table) for ports, table in factors if edge not in ports]
        neighbors = tuple(sorted(set().union(*(set(ports) for ports, _ in chosen)) - {edge}))
        if 1 << len(neighbors) > max_table_entries:
            raise ValueError('wire deformation exceeds intermediate tensor budget')
        stats.max_intermediate_arity = max(stats.max_intermediate_arity, len(neighbors))
        new_table = []
        for mask in range(1 << len(neighbors)):
            stats.table_entries_evaluated += 1
            if stats.table_entries_evaluated % 128 == 0 and monotonic() > deadline:
                raise TimeoutError('wire polynomial contraction exceeded time budget')
            assignment = {p: bool(mask & (1 << j)) for j, p in enumerate(neighbors)}
            acc = [0] * size
            for bit in (False, True):
                assignment[edge] = bit
                contribution = one
                for ports, table in chosen:
                    idx = sum(1 << j for j, p in enumerate(ports) if assignment[p])
                    contribution = multiply_polynomials(
                        contribution, table[idx], precision_bits=precision_bits, stats=mut_stats)
                    if not any(contribution):
                        break
                for j, coeff in enumerate(contribution):
                    acc[j] = ((acc[j] + coeff) % modulus) if modulus else (acc[j] + coeff)
            new_table.append(tuple(acc))
        factors.append((neighbors, tuple(new_table)))
        remaining.remove(edge)
        stats.eliminated_half_edges += 1

    result = one
    for ports, table in factors:
        if ports:
            raise AssertionError('uncontracted half-edges')
        result = multiply_polynomials(result, table[0], precision_bits=precision_bits, stats=mut_stats)
    stats.polynomial_multiplications = mut_stats.multiplication_pairs
    stats.provably_zero_products_mod_2_power = mut_stats.v2_zero_pairs_elided
    return list(result), stats


def independent_defect_histogram(network: TensorNetwork, *, max_edges: int = 7,
                                 timeout_s: float = 10.0) -> list[int]:
    """Separate exhaustive oracle over 2E half-edge bits (4**E assignments)."""
    if type(max_edges) is not int or not 0 <= max_edges <= 9 or network.edges > max_edges:
        raise ValueError('independent half-edge oracle budget exceeded')
    if not 0 < timeout_s <= 30:
        raise ValueError('invalid timeout')
    endpoints = _endpoint_map(network)
    histogram = [0] * (network.edges + 1)
    deadline = monotonic() + timeout_s
    for mask in range(1 << (2*network.edges)):
        if (mask & 1023) == 0 and monotonic() > deadline:
            raise TimeoutError('half-edge oracle timed out')
        value = 1
        for factor, mapped in zip(network.factors, endpoints):
            idx = sum(1 << j for j, p in enumerate(mapped) if mask & (1 << p))
            value *= factor.table[idx]
            if value == 0:
                break
        if value:
            mismatches = sum(bool(mask & (1 << (2*e))) != bool(mask & (1 << (2*e+1)))
                             for e in range(network.edges))
            histogram[mismatches] += value
    return histogram


def check_deformation_invariants(network: TensorNetwork, coefficients: Sequence[int],
                                 *, precision_bits: int | None = None) -> dict:
    """Independently verify the two rank-one nodes, with explicit ring semantics."""
    if len(coefficients) != network.edges + 1 or any(type(c) is not int for c in coefficients):
        raise ValueError('invalid polynomial degree/coefficients')
    modulus = 1 << precision_bits if precision_bits else None
    observed_plus = evaluate_polynomial(coefficients, 1, precision_bits)
    observed_minus = evaluate_polynomial(coefficients, -1, precision_bits)
    expected_plus = factorized_evaluation(network, 1)
    expected_minus = factorized_evaluation(network, -1)
    if modulus:
        expected_plus %= modulus
        expected_minus %= modulus
    if (observed_plus, observed_minus) != (expected_plus, expected_minus):
        raise AssertionError('split-wire rank-one factorization invariant failed')
    return {'at_plus_one': str(observed_plus), 'at_minus_one': str(observed_minus),
            'rank_one_nodes_checked': True}
