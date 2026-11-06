"""Exact small reference for tapered Hermite recovery over 2-adic modules.

This implements the interpolation lemma used by the October 25, 2026
quantitative tensor-contraction manuscript. Coefficients of the target
polynomial are represented by coordinate vectors; rational interpolation
scalars act independently on each coordinate. Input jets are canonical
integer representatives modulo their node-specific powers of two.

The code is a finite reference, not the manuscript's full coefficient ring,
recursive contraction, or complexity proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import comb
from typing import Mapping, Sequence, Tuple


CoordinateVector = Tuple[int, ...]
TaylorJet = Tuple[CoordinateVector, ...]


class HermiteInputError(ValueError):
    """Raised when a tapered schedule or its modular jets are malformed."""


def _v2(value: int) -> int:
    if value == 0:
        raise ValueError('2-adic valuation is undefined at zero')
    return (abs(value) & -abs(value)).bit_length() - 1


def _fraction_mod_2(value: Fraction, precision: int) -> int:
    modulus = 1 << precision
    if value.denominator % 2 == 0:
        raise ArithmeticError('cannot reduce a fraction with an even denominator modulo 2^p')
    return value.numerator * pow(value.denominator, -1, modulus) % modulus


@dataclass(frozen=True)
class TaperedHermiteSchedule:
    """Node multiplicities and precisions for a packet size ``2**a``."""

    packet_size: int
    a: int
    M: int
    u: int
    h: int
    target_precision: int
    degree_bound: int
    node_multiplicities: Tuple[Tuple[int, int], ...]
    node_precisions: Tuple[Tuple[int, int], ...]

    @property
    def active_nodes(self) -> Tuple[int, ...]:
        return tuple(node for node, multiplicity in self.node_multiplicities
                     if multiplicity > 0)

    def multiplicity(self, node: int) -> int:
        for candidate, value in self.node_multiplicities:
            if candidate == node:
                return value
        return 0

    def precision(self, node: int) -> int:
        for candidate, value in self.node_precisions:
            if candidate == node:
                return value
        raise HermiteInputError('node has no tapered precision')

    @property
    def total_multiplicity(self) -> int:
        return sum(value for _, value in self.node_multiplicities)


def make_tapered_schedule(packet_size: int, M: int, u: int,
                          target_precision: int) -> TaperedHermiteSchedule:
    """Construct the manuscript's q_t and p_t schedule.

    Preconditions are ``packet_size=2**a``, ``1 <= u <= a``, ``M >= u``.
    The degree bound is ``M*(2L-1)`` and the implementation checks that the
    total Hermite multiplicity strictly exceeds it.
    """
    if type(packet_size) is not int or packet_size < 2 or packet_size & (packet_size - 1):
        raise HermiteInputError('packet_size must be a power of two and at least 2')
    if type(M) is not int or M < 1:
        raise HermiteInputError('M must be a positive integer')
    if type(u) is not int or type(target_precision) is not int:
        raise HermiteInputError('u and target_precision must be integers')
    a = packet_size.bit_length() - 1
    if not 1 <= u <= a or M < u:
        raise HermiteInputError('require 1 <= u <= log2(packet_size) and M >= u')
    if target_precision < 1:
        raise HermiteInputError('target_precision must be positive')

    h = (3 * M + u - 1) // u
    grid = tuple(range(-packet_size, packet_size))
    multiplicities = []
    precisions = []
    for node in grid:
        if node == 0:
            continue
        level = _v2(node)
        multiplicity = h * max(0, u - level)
        multiplicities.append((node, multiplicity))
        if multiplicity:
            D = packet_size >> level
            precision = (target_precision + 8 * h * D
                         + 8 * M * (a + 1))
            precisions.append((node, precision))

    result = TaperedHermiteSchedule(
        packet_size=packet_size,
        a=a,
        M=M,
        u=u,
        h=h,
        target_precision=target_precision,
        degree_bound=M * (2 * packet_size - 1),
        node_multiplicities=tuple(multiplicities),
        node_precisions=tuple(precisions),
    )
    if result.total_multiplicity <= result.degree_bound:
        raise ArithmeticError('Hermite multiplicities do not cover the degree bound')
    if any(value > 4 * M for _, value in result.node_multiplicities):
        raise ArithmeticError('a node multiplicity exceeds the proved 4M bound')
    return result


def _local_hermite_factor(schedule: TaperedHermiteSchedule,
                          node: int) -> tuple[Fraction, Tuple[Fraction, ...]]:
    """Return E_t(0) and E_t(t+alpha*z) truncated below q_t."""
    order = schedule.multiplicity(node)
    if order <= 0:
        raise HermiteInputError('Hermite factor requested for an inactive node')
    alpha = 1 << (schedule.a + 1)
    E_at_zero = Fraction(1)
    local = [Fraction(1)] + [Fraction(0)] * (order - 1)

    for other, multiplicity in schedule.node_multiplicities:
        if other == node or multiplicity == 0:
            continue
        denominator = node - other
        E_at_zero *= Fraction(-other, denominator) ** multiplicity

        slope = Fraction(alpha, denominator)
        factor = [Fraction(0)] * min(order, multiplicity + 1)
        for degree in range(len(factor)):
            factor[degree] = comb(multiplicity, degree) * slope ** degree
        product = [Fraction(0)] * order
        for left_degree, left_value in enumerate(local):
            if not left_value:
                continue
            for right_degree, right_value in enumerate(factor):
                degree = left_degree + right_degree
                if degree >= order:
                    break
                product[degree] += left_value * right_value
        local = product

    if local[0] != 1:
        raise ArithmeticError('local Hermite factor must have constant coefficient one')
    if any(value.denominator % 2 == 0 for value in local):
        raise ArithmeticError('local Hermite factor is not 2-adically integral')
    return E_at_zero, tuple(local)


def recover_tapered_hermite(
    schedule: TaperedHermiteSchedule,
    jets: Mapping[int, Sequence[Sequence[int]]],
) -> CoordinateVector:
    """Recover F(0) modulo 2**target_precision from tapered local jets.

    ``jets[t][j][c]`` is coordinate ``c`` of the z**j coefficient of
    ``F(t + 2**(a+1) z)``, represented in ``[0, 2**p_t)``. Coefficients may
    belong to any finite free module over a 2-adic coefficient ring because
    the Hermite multipliers are rational scalars acting coordinatewise.

    The caller must provide jets arising from a common polynomial satisfying
    the schedule's degree/integrality hypotheses. The routine checks the
    shape, local unit inverses, and final 2-adic integrality, but cannot infer
    the common-polynomial hypothesis from residues alone.
    """
    if set(jets) != set(schedule.active_nodes):
        raise HermiteInputError('jets must be supplied for exactly the active nodes')
    modulus_target = 1 << schedule.target_precision
    totals: list[Fraction] | None = None
    coordinate_count = None

    for node in schedule.active_nodes:
        order = schedule.multiplicity(node)
        precision = schedule.precision(node)
        modulus = 1 << precision
        raw_jet = jets[node]
        if len(raw_jet) != order:
            raise HermiteInputError('each local jet must contain exactly q_t coefficients')
        jet: list[CoordinateVector] = []
        for coefficient in raw_jet:
            if not isinstance(coefficient, (tuple, list)) or not coefficient:
                raise HermiteInputError('each Taylor coefficient must be a nonempty coordinate vector')
            if any(type(value) is not int or not 0 <= value < modulus
                   for value in coefficient):
                raise HermiteInputError('jet coordinates must be canonical residues modulo 2^p_t')
            if coordinate_count is None:
                coordinate_count = len(coefficient)
            if len(coefficient) != coordinate_count:
                raise HermiteInputError('all jet coefficients must have the same coordinate dimension')
            jet.append(tuple(coefficient))

        E_at_zero, local_E = _local_hermite_factor(schedule, node)
        inverse_E = [Fraction(1)] + [Fraction(0)] * (order - 1)
        for degree in range(1, order):
            inverse_E[degree] = -sum(
                local_E[k] * inverse_E[degree - k]
                for k in range(1, degree + 1)
            )
        inverse_mod = tuple(_fraction_mod_2(value, precision)
                            for value in inverse_E)

        quotient = [[0] * coordinate_count for _ in range(order)]
        for degree in range(order):
            for source_degree in range(degree + 1):
                scale = inverse_mod[source_degree]
                source = jet[degree - source_degree]
                for coordinate in range(coordinate_count):
                    quotient[degree][coordinate] = (
                        quotient[degree][coordinate]
                        + scale * source[coordinate]
                    ) % modulus

        z_at_origin = Fraction(-node, 1 << (schedule.a + 1))
        if totals is None:
            totals = [Fraction(0)] * coordinate_count
        for coordinate in range(coordinate_count):
            evaluated = sum(
                (Fraction(quotient[degree][coordinate]) * z_at_origin ** degree
                 for degree in range(order)),
                Fraction(0),
            )
            totals[coordinate] += E_at_zero * evaluated

    if totals is None:
        raise ArithmeticError('schedule unexpectedly has no active Hermite nodes')
    recovered = []
    for value in totals:
        if value.denominator % 2 == 0:
            raise ArithmeticError(
                'reconstructed coordinate is not 2-adically integral; '
                'jets may not satisfy the common-polynomial hypothesis')
        recovered.append(value.numerator * pow(value.denominator, -1, modulus_target)
                         % modulus_target)
    return tuple(recovered)


def integer_polynomial_jets(
    coefficients: Sequence[Sequence[int]],
    schedule: TaperedHermiteSchedule,
) -> dict[int, TaylorJet]:
    """Build canonical node jets for an integer-vector polynomial oracle.

    This is a test/reference helper. Coefficients are listed in ascending T
    degree, and each coefficient is an integer coordinate vector.
    """
    if not coefficients:
        raise HermiteInputError('polynomial must have at least one coefficient')
    dimension = len(coefficients[0])
    if dimension == 0 or any(len(coefficient) != dimension for coefficient in coefficients):
        raise HermiteInputError('polynomial coefficients need a common nonzero dimension')
    if len(coefficients) - 1 > schedule.degree_bound:
        raise HermiteInputError('polynomial exceeds the schedule degree bound')
    if any(type(value) is not int for coefficient in coefficients for value in coefficient):
        raise HermiteInputError('integer polynomial oracle accepts only integer coordinates')

    alpha = 1 << (schedule.a + 1)
    result: dict[int, TaylorJet] = {}
    for node in schedule.active_nodes:
        precision = schedule.precision(node)
        modulus = 1 << precision
        order = schedule.multiplicity(node)
        jet = [[0] * dimension for _ in range(order)]
        for degree, coefficient in enumerate(coefficients):
            for z_degree in range(min(order, degree + 1)):
                scale = comb(degree, z_degree) * node ** (degree - z_degree) * alpha ** z_degree
                for coordinate, value in enumerate(coefficient):
                    jet[z_degree][coordinate] = (
                        jet[z_degree][coordinate] + value * scale
                    ) % modulus
        result[node] = tuple(tuple(row) for row in jet)
    return result


def validate_tapered_hermite_reference(seed: int = 20261031,
                                       cases: int = 25) -> dict[str, int]:
    """Differential-check reconstruction against seeded exact polynomials."""
    import random

    rng = random.Random(seed)
    configurations = ((2, 1, 1), (4, 2, 1), (4, 3, 2), (8, 4, 2),
                      (8, 5, 3), (16, 8, 4))
    max_degree = 0
    max_precision = 0
    for case in range(cases):
        packet_size, M, u = configurations[case % len(configurations)]
        target_precision = (5 if packet_size == 16 else 1 + case % 7)
        schedule = make_tapered_schedule(packet_size, M, u, target_precision)
        degree = rng.randrange(schedule.degree_bound + 1)
        dimension = 1 + case % 3
        coefficients = tuple(
            tuple(rng.randint(-11, 13) for _ in range(dimension))
            for _ in range(degree + 1)
        )
        jets = integer_polynomial_jets(coefficients, schedule)
        got = recover_tapered_hermite(schedule, jets)
        expected = tuple(value % (1 << target_precision)
                         for value in coefficients[0])
        if got != expected:
            raise AssertionError(
                f'tapered Hermite mismatch at case {case}: {got} != {expected}')
        max_degree = max(max_degree, degree)
        max_precision = max(max_precision,
                            max(schedule.precision(node)
                                for node in schedule.active_nodes))
    return {
        'cases': cases,
        'seed': seed,
        'max_degree': max_degree,
        'max_local_precision_bits': max_precision,
        'coefficient_dimensions': 3,
    }
