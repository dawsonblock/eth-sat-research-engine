#!/usr/bin/env python3
"""Exact small reference for the packet Cauchy deformation.

This module checks the local polynomial kernel and the identity F(0)=Z on
small two-sided Boolean tensor tables. The companion tapered_hermite module
implements and checks the exact interpolation recovery lemma, but neither
module implements the full recursive network contraction.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from math import comb
from typing import Sequence, Union


Exact = Union[int, Fraction]
Polynomial = tuple[Fraction, ...]  # coefficients in ascending degree order


class ReferenceLimit(RuntimeError):
    """Raised when a finite exhaustive reference exceeds its declared cap."""


def _trim(values: Sequence[Exact]) -> Polynomial:
    result = [Fraction(v) for v in values]
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result or [Fraction(0)])


def _add(left: Polynomial, right: Polynomial) -> Polynomial:
    size = max(len(left), len(right))
    out = [Fraction(0)] * size
    for i, value in enumerate(left):
        out[i] += value
    for i, value in enumerate(right):
        out[i] += value
    return _trim(out)


def _scale(poly: Polynomial, scalar: Exact) -> Polynomial:
    factor = Fraction(scalar)
    return _trim([factor * value for value in poly])


def _mul(left: Polynomial, right: Polynomial) -> Polynomial:
    out = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        if not a:
            continue
        for j, b in enumerate(right):
            if b:
                out[i + j] += a * b
    return _trim(out)


def _eval(poly: Polynomial, value: Exact) -> Fraction:
    x = Fraction(value)
    total = Fraction(0)
    for coefficient in reversed(poly):
        total = total * x + coefficient
    return total


def _derivative(poly: Polynomial) -> Polynomial:
    if len(poly) <= 1:
        return (Fraction(0),)
    return _trim([i * poly[i] for i in range(1, len(poly))])


def _divide_by_linear(poly: Polynomial, root: int) -> tuple[Polynomial, Fraction]:
    """Return quotient and remainder for division by T-root."""
    if len(poly) <= 1:
        return (Fraction(0),), poly[0]
    quotient = [Fraction(0)] * (len(poly) - 1)
    quotient[-1] = poly[-1]
    for index in range(len(poly) - 2, 0, -1):
        quotient[index - 1] = poly[index] + root * quotient[index]
    remainder = poly[0] + root * quotient[0]
    return _trim(quotient), remainder


def _validate_exact_table(table: Sequence[Exact], expected_size: int, name: str) -> tuple[Fraction, ...]:
    if len(table) != expected_size:
        raise ValueError(f'{name} must contain {expected_size} entries')
    result = []
    for value in table:
        if type(value) is int or isinstance(value, Fraction):
            result.append(Fraction(value))
        else:
            raise TypeError(f'{name} entries must be exact int or Fraction values')
    return tuple(result)


@dataclass(frozen=True)
class CauchyPacket:
    """Polynomial packet kernel W_xy(T), with x,y in [0, packet_size)."""

    packet_size: int
    grid: tuple[int, ...]
    cauchy_polynomial: Polynomial
    derivative_at_zero: Fraction
    entries: tuple[tuple[Polynomial, ...], ...]

    def evaluate(self, value: Exact) -> tuple[tuple[Fraction, ...], ...]:
        return tuple(tuple(_eval(poly, value) for poly in row)
                     for row in self.entries)


@dataclass(frozen=True)
class ModeExpansionResult:
    direct_residue: int
    mode_sum_residue: int
    number_of_modes: int
    minimum_coefficient_valuation: int


def make_cauchy_packet(packet_size: int) -> CauchyPacket:
    """Construct W_xy(T)=C(T)/(C'(0)(T-(y-x))) exactly over Q[T].

    The grid is S={-L,...,L-1}; every packet difference y-x lies in S.
    Polynomial division is performed before scaling, so no rational-function
    evaluation or removable-pole special case is used in the implementation.
    """
    if type(packet_size) is not int or packet_size < 1:
        raise ValueError('packet_size must be a positive integer')
    grid = tuple(range(-packet_size, packet_size))
    cauchy = (Fraction(1),)
    for root in grid:
        cauchy = _mul(cauchy, (Fraction(-root), Fraction(1)))
    derivative_at_zero = _derivative(cauchy)[0]
    if derivative_at_zero == 0:
        raise ArithmeticError('C\'(0) must be nonzero for this grid')

    rows = []
    for x in range(packet_size):
        row = []
        for y in range(packet_size):
            quotient, remainder = _divide_by_linear(cauchy, y - x)
            if remainder:
                raise ArithmeticError('packet difference was not a grid root')
            row.append(_scale(quotient, Fraction(1, 1) / derivative_at_zero))
        rows.append(tuple(row))
    return CauchyPacket(packet_size, grid, cauchy, derivative_at_zero,
                        tuple(rows))


def _compose_affine(poly: Polynomial, center: int, slope: int) -> Polynomial:
    """Return poly(center+slope*z) exactly in ascending z-degree order."""
    out = [Fraction(0)] * len(poly)
    for degree, coefficient in enumerate(poly):
        for z_degree in range(degree + 1):
            out[z_degree] += (coefficient * comb(degree, z_degree)
                              * center ** (degree - z_degree)
                              * slope ** z_degree)
    return _trim(out)


def local_coordinate_series(packet: CauchyPacket, node: int) -> tuple[tuple[Polynomial, ...], ...]:
    """Return W(node+2^(a+1)z) for L=2^a, over exact rational polynomials.

    The manuscript's local-integrality claim is membership in Z_(2)[z],
    meaning every coefficient has an odd denominator, not necessarily an
    integer coefficient. This routine checks no modular arithmetic itself.
    """
    size = packet.packet_size
    if size & (size - 1):
        raise ValueError('local coordinates require packet_size to be a power of two')
    if node not in packet.grid:
        raise ValueError('node must belong to the Cauchy grid')
    a = size.bit_length() - 1
    alpha = 1 << (a + 1)
    series = tuple(tuple(_compose_affine(poly, node, alpha) for poly in row)
                   for row in packet.entries)
    if any(coefficient.denominator % 2 == 0
           for row in series for poly in row for coefficient in poly):
        raise ArithmeticError('local coordinate has a non-unit 2-adic denominator')
    return series


def _v2_integer(value: int) -> int:
    if value == 0:
        raise ValueError('2-adic valuation is undefined for zero in this helper')
    absolute = abs(value)
    return (absolute & -absolute).bit_length() - 1


def _fraction_mod_power_of_two(value: Fraction, precision: int) -> int:
    modulus = 1 << precision
    if value.denominator % 2 == 0:
        raise ValueError('fraction denominator is not invertible modulo 2^precision')
    return value.numerator * pow(value.denominator, -1, modulus) % modulus


def _poly_dict_multiply(left: dict[tuple[int, ...], int],
                        right: dict[tuple[int, ...], int],
                        modulus: int) -> dict[tuple[int, ...], int]:
    out: dict[tuple[int, ...], int] = {}
    for left_exp, left_value in left.items():
        for right_exp, right_value in right.items():
            exponent = tuple(a + b for a, b in zip(left_exp, right_exp))
            out[exponent] = (out.get(exponent, 0) + left_value * right_value) % modulus
    return {exponent: value for exponent, value in out.items() if value}


def _weighted_mode_tuples(weights: Sequence[int], precision: int):
    ranges = [range((precision - 1) // weight + 1) for weight in weights]
    for exponents in product(*ranges):
        if sum(weight * exponent for weight, exponent in zip(weights, exponents)) < precision:
            yield tuple(exponents)


def _unary_product_table(weights: Sequence[Sequence[Exact]], size: int) -> tuple[Fraction, ...]:
    if len(weights) != size:
        raise ValueError('one unary tensor is required per packet port')
    unary = []
    for pair in weights:
        if len(pair) != 2:
            raise ValueError('each unary tensor must have two Boolean entries')
        values = []
        for value in pair:
            if type(value) is int or isinstance(value, Fraction):
                values.append(Fraction(value))
            else:
                raise TypeError('unary tensor entries must be exact int or Fraction values')
        unary.append(tuple(values))
    table = []
    for mask in range(1 << size):
        value = Fraction(1)
        for position in range(size):
            bit = (mask >> position) & 1
            value *= unary[position][bit]
        table.append(value)
    return tuple(table)


def expand_crossing_entry_mod(
    packet: CauchyPacket,
    *,
    node: int,
    row: int,
    tile_base: int,
    tile_index: int,
    z: int,
    precision: int,
) -> ModeExpansionResult:
    """Evaluate one paper-style geometric mode expansion modulo 2^precision.

    Preconditions encode an active valuation level and a crossing row/tile.
    This finite reference checks one wire entry, not the recursive network
    identity or its global mode-count theorem.
    """
    size = packet.packet_size
    if size & (size - 1):
        raise ValueError('mode expansion requires packet_size to be a power of two')
    if type(precision) is not int or precision < 1:
        raise ValueError('precision must be a positive integer')
    if type(row) is not int or not 0 <= row < size:
        raise ValueError('row index is outside the packet')
    if type(tile_index) is not int or tile_index < 0:
        raise ValueError('tile_index must be a nonnegative integer')
    if type(z) is not int:
        raise TypeError('the finite local-coordinate test requires integer z')
    a = size.bit_length() - 1
    if node not in packet.grid or node == 0:
        raise ValueError('node must be a nonzero Cauchy grid point')
    i = _v2_integer(node)
    if i >= a:
        raise ValueError('node valuation must be below log2(packet_size)')
    tile_width = 1 << (i + 1)
    if type(tile_base) is not int or not 0 <= tile_base < tile_width:
        raise ValueError('tile_base must be in [0, 2^(v2(node)+1))')
    base_denominator = node - tile_base + row
    if base_denominator == 0 or _v2_integer(base_denominator) > i:
        raise ValueError('row/tile do not satisfy the crossing valuation condition')
    column = tile_base + tile_width * tile_index
    if column >= size:
        raise ValueError('tile_index selects an unused slot')

    alpha = 1 << (a + 1)
    T = node + alpha * z
    denominator = T - tile_base + row
    valuation = _v2_integer(denominator)
    if valuation != _v2_integer(base_denominator):
        raise ArithmeticError('local shift changed the denominator valuation')
    modulus = 1 << precision
    ratio_mod = ((1 << (i + 1 - valuation))
                 * pow(denominator // (1 << valuation), -1, modulus)) % modulus
    base_entry = _eval(packet.entries[row][tile_base], T)
    if base_entry.denominator % 2 == 0:
        raise ArithmeticError('mode base coefficient is not 2-adically integral')
    base_valuation = _v2_integer(base_entry.numerator) if base_entry else 10**9
    expected_minimum_valuation = a + 1 - i
    if base_valuation - _v2_integer(base_entry.denominator) < expected_minimum_valuation:
        raise ArithmeticError('mode base coefficient lacks its claimed 2-adic valuation')
    base_mod = _fraction_mod_power_of_two(base_entry, precision)

    mode_sum = 0
    mode_count = max(0, precision - 1)  # b+1 < precision
    for b in range(mode_count):
        mode_sum = (mode_sum + base_mod * pow(ratio_mod, b, modulus)
                    * pow(tile_index, b, modulus)) % modulus
    direct = _eval(packet.entries[row][column], T)
    direct_mod = _fraction_mod_power_of_two(direct, precision)
    if direct_mod != mode_sum:
        raise ArithmeticError('truncated geometric mode expansion disagrees modulo 2^p')
    return ModeExpansionResult(direct_mod, mode_sum, mode_count,
                               expected_minimum_valuation)


def two_group_mode_contraction(
    packet: CauchyPacket,
    *,
    node: int,
    z: int,
    precision: int,
    row_unary: Sequence[Sequence[Exact]],
    column_unary: Sequence[Sequence[Exact]],
) -> dict[str, int]:
    """Check one complete two-group, one-packet mode-factorization identity.

    Slots are grouped by bit i=v2(node): row_group[x]=bit_i(x), while
    column_group[y]=1-bit_i(y). Modes run from each column tile to the
    opposite row group. Both the direct deformed contraction and the sum of
    products of independent group contractions are evaluated modulo 2^p.
    This is a tiny one-step identity check, not the paper's recursive packing
    lemma or global child-size theorem.
    """
    size = packet.packet_size
    if size < 2 or size & (size - 1):
        raise ValueError('two-group mode test requires a power-of-two packet size >= 2')
    if size > 8:
        raise ReferenceLimit('two-group exhaustive reference is capped at packet size 8')
    if type(precision) is not int or not 1 <= precision <= 8:
        raise ValueError('reference mode precision must be between 1 and 8')
    a = size.bit_length() - 1
    if node not in packet.grid or node == 0:
        raise ValueError('node must be a nonzero Cauchy grid point')
    i = _v2_integer(node)
    if i >= a:
        raise ValueError('node valuation must be below log2(packet_size)')
    modulus = 1 << precision
    alpha = 1 << (a + 1)
    T = node + alpha * z
    row_table = _unary_product_table(row_unary, size)
    column_table = _unary_product_table(column_unary, size)
    W = packet.evaluate(T)

    # Independent direct evaluation of the deformed contraction.
    direct = Fraction(0)
    bit_vectors = tuple(product((0, 1), repeat=size))
    for X in bit_vectors:
        x_index = sum(bit << position for position, bit in enumerate(X))
        forms = [sum((W[row][column] * X[column] for column in range(size)),
                     Fraction(0)) for row in range(size)]
        for Y in bit_vectors:
            y_index = sum(bit << position for position, bit in enumerate(Y))
            term = row_table[y_index] * column_table[x_index]
            for row, bit in enumerate(Y):
                term *= forms[row] if bit else 1 - forms[row]
            direct += term
    direct_residue = _fraction_mod_power_of_two(direct, precision)

    # Construct mode variables for each tile and each retained weight.
    tile_width = 1 << (i + 1)
    modes = []
    for tile_base in range(tile_width):
        target_group = (tile_base >> i) & 1
        source_group = 1 - target_group
        for b in range(max(0, precision - 1)):
            modes.append({
                'tile_base': tile_base,
                'b': b,
                'weight': b + 1,
                'source': source_group,
                'target': target_group,
            })
    mode_weights = tuple(mode['weight'] for mode in modes)
    mode_tuples = tuple(_weighted_mode_tuples(mode_weights, precision))

    def child_value(group: int, beta: tuple[int, ...]) -> int:
        rows = tuple(x for x in range(size) if ((x >> i) & 1) == group)
        columns = tuple(y for y in range(size) if 1 - ((y >> i) & 1) == group)
        target_ids = tuple(index for index, mode in enumerate(modes)
                           if mode['target'] == group)
        source_ids = tuple(index for index, mode in enumerate(modes)
                           if mode['source'] == group)
        target_position = {mode_id: position for position, mode_id in enumerate(target_ids)}
        total = 0
        row_assignments = tuple(product((0, 1), repeat=len(rows)))
        column_assignments = tuple(product((0, 1), repeat=len(columns)))
        for X_group in column_assignments:
            X = {column: bit for column, bit in zip(columns, X_group)}
            column_weight = Fraction(1)
            for column, bit in X.items():
                column_weight *= Fraction(column_unary[column][bit])
            if not column_weight:
                continue
            outgoing = 1
            for mode_id in source_ids:
                mode = modes[mode_id]
                tile_base, power = mode['tile_base'], mode['b']
                linear_summary = 0
                for local_j, y in enumerate(range(tile_base, size, tile_width)):
                    if y in X and X[y]:
                        linear_summary += (local_j ** power)
                outgoing = (outgoing * pow(linear_summary % modulus,
                                           beta[mode_id], modulus)) % modulus
            for Y_group in row_assignments:
                Y = {row: bit for row, bit in zip(rows, Y_group)}
                row_weight = Fraction(1)
                for row, bit in Y.items():
                    row_weight *= Fraction(row_unary[row][bit])
                if not row_weight:
                    continue
                row_polynomial: dict[tuple[int, ...], int] = {
                    (0,) * len(target_ids): 1
                }
                for row in rows:
                    local_value = Fraction(0)
                    for column in columns:
                        if column in X:
                            local_value += W[row][column] * X[column]
                    local_mod = _fraction_mod_power_of_two(local_value, precision)
                    bit = Y[row]
                    constant = local_mod if bit else (1 - local_mod) % modulus
                    factor: dict[tuple[int, ...], int] = {
                        (0,) * len(target_ids): constant % modulus
                    }
                    sign = 1 if bit else -1
                    for mode_id in target_ids:
                        mode = modes[mode_id]
                        tile_base, power = mode['tile_base'], mode['b']
                        denominator = T - tile_base + row
                        base_entry = _eval(packet.entries[row][tile_base], T)
                        ratio = Fraction(tile_width, denominator)
                        coefficient = base_entry * ratio ** power
                        coefficient_mod = _fraction_mod_power_of_two(
                            coefficient, precision)
                        exponent = [0] * len(target_ids)
                        exponent[target_position[mode_id]] = 1
                        exponent_key = tuple(exponent)
                        factor[exponent_key] = (
                            factor.get(exponent_key, 0) + sign * coefficient_mod
                        ) % modulus
                    row_polynomial = _poly_dict_multiply(
                        row_polynomial, factor, modulus)
                target_exponents = tuple(beta[mode_id] for mode_id in target_ids)
                coefficient = row_polynomial.get(target_exponents, 0)
                total = (total + _fraction_mod_power_of_two(
                    row_weight * column_weight, precision)
                    * coefficient * outgoing) % modulus
        return total

    decomposed = 0
    for beta in mode_tuples:
        product_of_children = 1
        for group in (0, 1):
            product_of_children = (product_of_children
                                  * child_value(group, beta)) % modulus
        decomposed = (decomposed + product_of_children) % modulus
    if decomposed != direct_residue:
        raise ArithmeticError(
            f'two-group mode decomposition mismatch: {decomposed} != {direct_residue}')
    return {
        'direct_residue': direct_residue,
        'mode_decomposition_residue': decomposed,
        'mode_variables': len(modes),
        'mode_tuples': len(mode_tuples),
        'groups': 2,
    }


def deformed_packet_contraction_polynomial(
    packet: CauchyPacket,
    row_tensor: Sequence[Exact],
    column_tensor: Sequence[Exact],
    *,
    max_exhaustive_packet_size: int = 8,
) -> Polynomial:
    """Brute-force F(T) for a tiny packet and return its exact polynomial.

    Tables are indexed by the integer whose bit i is port i. This is only a
    correctness oracle for the deformation identity, not a scalable evaluator.
    """
    size = packet.packet_size
    if size > max_exhaustive_packet_size:
        raise ReferenceLimit(
            f'exhaustive packet size {size} exceeds cap {max_exhaustive_packet_size}')
    table_size = 1 << size
    row_values = _validate_exact_table(row_tensor, table_size, 'row_tensor')
    column_values = _validate_exact_table(column_tensor, table_size, 'column_tensor')
    total = (Fraction(0),)
    bit_vectors = tuple(product((0, 1), repeat=size))

    for column_bits in bit_vectors:
        column_index = sum(bit << i for i, bit in enumerate(column_bits))
        column_weight = column_values[column_index]
        if column_weight == 0:
            continue
        linear_forms = []
        for row in range(size):
            form = (Fraction(0),)
            for column, bit in enumerate(column_bits):
                if bit:
                    form = _add(form, packet.entries[row][column])
            linear_forms.append(form)

        for row_bits in bit_vectors:
            row_index = sum(bit << i for i, bit in enumerate(row_bits))
            scalar = column_weight * row_values[row_index]
            if scalar == 0:
                continue
            term = (Fraction(scalar),)
            for bit, form in zip(row_bits, linear_forms):
                # l_1(z)=z; l_0(z)=1-z.
                factor = form if bit else _add((Fraction(1),), _scale(form, -1))
                term = _mul(term, factor)
                if term == (Fraction(0),):
                    break
            total = _add(total, term)
    return total


def _check_packet_grid(packet: CauchyPacket) -> None:
    derivative = _derivative(packet.cauchy_polynomial)
    for node in packet.grid:
        matrix = packet.evaluate(node)
        expected_weight = _eval(derivative, node) / packet.derivative_at_zero
        for x in range(packet.packet_size):
            for y in range(packet.packet_size):
                expected = expected_weight if y - x == node else Fraction(0)
                if matrix[x][y] != expected:
                    raise AssertionError(
                        f'grid shift property failed at L={packet.packet_size}, '
                        f'T={node}, x={x}, y={y}')
    if packet.evaluate(0) != tuple(
            tuple(Fraction(int(x == y)) for y in range(packet.packet_size))
            for x in range(packet.packet_size)):
        raise AssertionError('W(0) is not the identity')


def _check_rational_kernel_formula(packets: Sequence[CauchyPacket]) -> int:
    checks = 0
    points = (Fraction(1, 7), Fraction(-2, 5))
    for packet in packets:
        if len(packet.entries[0][0]) - 1 != 2 * packet.packet_size - 1:
            raise AssertionError('kernel entry degree does not equal 2L-1')
        cauchy_at_points = {point: _eval(packet.cauchy_polynomial, point)
                            for point in points}
        for x in range(packet.packet_size):
            for y in range(packet.packet_size):
                difference = y - x
                for point in points:
                    rational_value = (cauchy_at_points[point]
                                      / (packet.derivative_at_zero
                                         * (point - difference)))
                    polynomial_value = _eval(packet.entries[x][y], point)
                    if rational_value != polynomial_value:
                        raise AssertionError('polynomial kernel differs from rational formula')
                    checks += 1
    return checks


def _check_deformed_contraction(seed: int = 20261031, cases: int = 24) -> dict[str, int]:
    rng = random.Random(seed)
    max_packet_size = 0
    for case in range(cases):
        size = 1 + case % 5
        packet = make_cauchy_packet(size)
        row = tuple(rng.randint(-3, 4) for _ in range(1 << size))
        column = tuple(rng.randint(-3, 4) for _ in range(1 << size))
        deformed = deformed_packet_contraction_polynomial(packet, row, column)
        original = sum(Fraction(row[mask] * column[mask]) for mask in range(1 << size))
        if deformed[0] != original:
            raise AssertionError(
                f'F(0) mismatch in case {case}: {deformed[0]} != {original}')
        max_packet_size = max(max_packet_size, size)
    return {'cases': cases, 'seed': seed, 'max_packet_size': max_packet_size}


def _check_local_coordinates() -> dict[str, int]:
    coefficient_count = 0
    for exponent in range(4):
        packet = make_cauchy_packet(1 << exponent)
        for node in packet.grid:
            series = local_coordinate_series(packet, node)
            coefficient_count += sum(len(poly) for row in series for poly in row)
    return {'power_of_two_packet_sizes': 4,
            '2_adically_integral_coefficients_checked': coefficient_count}


def _check_crossing_modes() -> dict[str, int]:
    cases = 0
    for exponent in range(1, 4):
        size = 1 << exponent
        packet = make_cauchy_packet(size)
        for node in packet.grid:
            if node == 0:
                continue
            i = _v2_integer(node)
            if i >= exponent:
                continue
            tile_width = 1 << (i + 1)
            for row in range(size):
                for tile_base in range(tile_width):
                    base = node - tile_base + row
                    if base == 0 or _v2_integer(base) > i:
                        continue
                    for tile_index in range((size - 1 - tile_base) // tile_width + 1):
                        for z in (0, 1, 3):
                            for precision in (1, 2, 4, 8):
                                expand_crossing_entry_mod(
                                    packet, node=node, row=row, tile_base=tile_base,
                                    tile_index=tile_index, z=z, precision=precision)
                                cases += 1
    return {'crossing_entry_expansions_checked': cases,
            'packet_sizes': 3, 'precisions': [1, 2, 4, 8]}


def _check_two_group_factorization(cases: int = 16,
                                  seed: int = 20261031) -> dict[str, int]:
    rng = random.Random(seed)
    packet = make_cauchy_packet(4)
    max_modes = 0
    max_tuples = 0
    nonzero_residues = 0
    for case in range(cases):
        row_unary = tuple((rng.randint(-2, 3), rng.randint(-2, 3))
                          for _ in range(packet.packet_size))
        column_unary = tuple((rng.randint(-2, 3), rng.randint(-2, 3))
                             for _ in range(packet.packet_size))
        result = two_group_mode_contraction(
            packet, node=(-3, -1, 1, 3)[case % 4], z=case % 4,
            precision=3 + case % 4,
            row_unary=row_unary, column_unary=column_unary)
        max_modes = max(max_modes, result['mode_variables'])
        max_tuples = max(max_tuples, result['mode_tuples'])
        nonzero_residues += result['direct_residue'] != 0
    return {'cases': cases, 'seed': seed, 'packet_size': packet.packet_size,
            'max_modes': max_modes, 'max_mode_tuples': max_tuples,
            'nonzero_direct_residues': nonzero_residues, 'groups': 2}


def self_test() -> dict[str, object]:
    from tapered_hermite import validate_tapered_hermite_reference

    packets = [make_cauchy_packet(size) for size in range(1, 9)]
    for packet in packets:
        _check_packet_grid(packet)
    rational_checks = _check_rational_kernel_formula(packets)
    contraction = _check_deformed_contraction()
    local_coordinates = _check_local_coordinates()
    modes = _check_crossing_modes()
    factorization = _check_two_group_factorization()
    hermite = validate_tapered_hermite_reference()
    return {
        'schema': 'ETH_SAT_V032_CAUCHY_DEFORMATION_REFERENCE',
        'packet_sizes_checked': [packet.packet_size for packet in packets],
        'grid_nodes_checked': sum(len(packet.grid) for packet in packets),
        'rational_kernel_formula_entry_checks': rational_checks,
        'polynomial_degrees': [len(packet.cauchy_polynomial) - 1 for packet in packets],
        'deformed_contraction_identity': contraction,
        'local_2_adic_coordinates': local_coordinates,
        'crossing_mode_expansion': modes,
        'two_group_mode_factorization': factorization,
        'tapered_hermite_recovery': hermite,
        'full_recursive_modular_mode_pruning_implemented': False,
        'tapered_hermite_reconstruction_implemented': True,
        'recursive_child_contraction_implemented': False,
        'general_subexponential_claim': False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if not args.self_test:
        parser.error('select --self-test')
    print(json.dumps(self_test(), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
