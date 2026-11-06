#!/usr/bin/env python3
"""Exact permanent-polynomial expansion for a sparse block boundary.

For a square matrix A and a common row/column block labeling, write
A = B + z D, where B retains within-block entries and D retains nonzero
cross-block entries. Enumerate subsets of D that are matchings; the unused
rows and columns must then be matched independently inside each block.

This is an exact bounded reference, not a general fast permanent or SAT
algorithm. Its dominant dependence is exponential in the number of nonzero
cross-block entries and in the largest block size. It uses only the Python
standard library and exact integer/rational arithmetic.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from fractions import Fraction
from itertools import permutations
from typing import Hashable, Sequence, Union


Exact = Union[int, Fraction]
_popcount = (int.bit_count if hasattr(int, 'bit_count')
             else lambda value: bin(value).count('1'))


class PermanentResourceLimit(RuntimeError):
    """Raised before returning a partial coefficient vector."""


@dataclass
class _WorkMeter:
    limit: int
    state_visit_limit: int
    transition_scan_limit: int
    operations: int = 0
    state_visits: int = 0
    transition_scans: int = 0

    def charge(self, amount: int = 1) -> None:
        if amount < 0 or self.operations + amount > self.limit:
            raise PermanentResourceLimit(
                f'exact arithmetic-operation budget {self.limit} exceeded')
        self.operations += amount

    def visit_state(self) -> None:
        if self.state_visits + 1 > self.state_visit_limit:
            raise PermanentResourceLimit(
                f'subset-DP state-visit budget {self.state_visit_limit} exceeded')
        self.state_visits += 1

    def scan_columns(self, amount: int) -> None:
        if amount < 0 or self.transition_scans + amount > self.transition_scan_limit:
            raise PermanentResourceLimit(
                'subset-DP transition-scan budget '
                f'{self.transition_scan_limit} exceeded')
        self.transition_scans += amount


@dataclass(frozen=True)
class SparseBoundaryResult:
    coefficients: tuple[Fraction, ...]
    cross_entries: int
    masks_examined: int
    matching_subsets: int
    arithmetic_operations: int
    dp_state_visits: int
    dp_transition_scans: int
    max_block_size: int

    def evaluate(self, z: Exact) -> Fraction:
        value = Fraction(0)
        point = Fraction(z)
        for coefficient in reversed(self.coefficients):
            value = value * point + coefficient
        return value

    @property
    def permanent_at_one(self) -> Fraction:
        return self.evaluate(1)

    def as_dict(self) -> dict[str, object]:
        return {
            'coefficients': [str(value) for value in self.coefficients],
            'permanent_at_one': str(self.permanent_at_one),
            'cross_entries': self.cross_entries,
            'masks_examined': self.masks_examined,
            'matching_subsets': self.matching_subsets,
            'exact_scalar_arithmetic_operations': self.arithmetic_operations,
            'subset_dp_state_visits': self.dp_state_visits,
            'subset_dp_transition_scans': self.dp_transition_scans,
            'horner_evaluation_operations_at_one': 2 * len(self.coefficients),
            'max_block_size': self.max_block_size,
            'claim': 'FINITE_SPARSE_BOUNDARY_PERMANENT_REFERENCE_ONLY',
        }


def _matrix_exact(matrix: Sequence[Sequence[Exact]]) -> tuple[tuple[Fraction, ...], ...]:
    rows = tuple(tuple(row) for row in matrix)
    n = len(rows)
    if any(len(row) != n for row in rows):
        raise ValueError('permanent matrix must be square')
    out: list[tuple[Fraction, ...]] = []
    for row in rows:
        values: list[Fraction] = []
        for value in row:
            if type(value) is int or isinstance(value, Fraction):
                values.append(Fraction(value))
            else:
                raise TypeError('matrix entries must be exact int or Fraction values')
        out.append(tuple(values))
    return tuple(out)


def _normalized_group_ids(block_labels: Sequence[Hashable], n: int) -> tuple[int, ...]:
    if len(block_labels) != n:
        raise ValueError('one block label is required for each row and column')
    label_to_id: dict[Hashable, int] = {}
    group_ids: list[int] = []
    try:
        for label in block_labels:
            if label not in label_to_id:
                label_to_id[label] = len(label_to_id)
            group_ids.append(label_to_id[label])
    except TypeError as exc:
        raise ValueError('block labels must be hashable') from exc
    return tuple(group_ids)


def _permanent_subset_dp(matrix: tuple[tuple[Fraction, ...], ...],
                         meter: _WorkMeter) -> Fraction:
    """Exact O(b*2**b) permanent for one square block."""
    n = len(matrix)
    if n == 0:
        return Fraction(1)
    dp = [Fraction(0)] * (1 << n)
    dp[0] = Fraction(1)
    for mask in range(1 << n):
        meter.visit_state()
        row = _popcount(mask)
        if row == n or dp[mask] == 0:
            continue
        prefix = dp[mask]
        meter.scan_columns(n)
        for column in range(n):
            bit = 1 << column
            if mask & bit:
                continue
            entry = matrix[row][column]
            if entry == 0:
                continue
            meter.charge(2)  # one exact multiplication and one exact addition
            dp[mask | bit] += prefix * entry
    return dp[-1]


def sparse_boundary_permanent_coefficients(
    matrix: Sequence[Sequence[Exact]],
    block_labels: Sequence[Hashable],
    *,
    max_dimension: int = 512,
    max_cross_entries: int = 20,
    max_block_size: int = 20,
    max_masks: int = 1 << 20,
    max_arithmetic_operations: int = 20_000_000,
    max_dp_state_visits: int = 20_000_000,
    max_dp_transition_scans: int = 100_000_000,
) -> SparseBoundaryResult:
    """Return coefficients of ``per(B + z*D)`` for a block diagonal ``B``.

    ``block_labels[i]`` assigns row ``i`` and column ``i`` to the same
    diagonal block. ``B[i,j]=matrix[i,j]`` when labels match and zero
    otherwise; ``D`` contains all nonzero entries whose labels differ.

    Every selected cross-block set must be a matching (no repeated row or
    column). For such a set, the remaining permanent factors by block. The
    routine rejects large boundaries/blocks before doing the search and raises
    ``PermanentResourceLimit`` without exposing partial coefficients.
    """
    if type(max_dimension) is not int or max_dimension < 0:
        raise ValueError('maximum matrix dimension must be a nonnegative integer')
    try:
        input_dimension = len(matrix)
    except TypeError as exc:
        raise TypeError('matrix must be a sized sequence of rows') from exc
    if input_dimension > max_dimension:
        raise PermanentResourceLimit(
            f'matrix dimension {input_dimension} exceeds cap {max_dimension}')
    exact = _matrix_exact(matrix)
    n = len(exact)
    if any(type(value) is not int or value < 0
           for value in (max_cross_entries, max_block_size, max_masks,
                         max_arithmetic_operations, max_dp_state_visits)):
        raise ValueError('resource limits must be nonnegative integers')
    if type(max_dp_transition_scans) is not int or max_dp_transition_scans < 1:
        raise ValueError('DP transition-scan budget must be a positive integer')
    if max_masks < 1 or max_arithmetic_operations < 1 or max_dp_state_visits < 1:
        raise ValueError('mask, arithmetic, and DP-state budgets must be positive')
    group_ids = _normalized_group_ids(block_labels, n)
    groups = tuple(range(max(group_ids, default=-1) + 1))
    rows_by_group = {group: tuple(i for i, group_id in enumerate(group_ids)
                                  if group_id == group) for group in groups}
    largest_block = max((len(rows_by_group[group]) for group in groups), default=0)
    if largest_block > max_block_size:
        raise PermanentResourceLimit(
            f'maximum block size {largest_block} exceeds cap {max_block_size}')

    cross = tuple((i, j, exact[i][j]) for i in range(n) for j in range(n)
                  if group_ids[i] != group_ids[j] and exact[i][j] != 0)
    k = len(cross)
    if k > max_cross_entries:
        raise PermanentResourceLimit(
            f'{k} nonzero cross-block entries exceed cap {max_cross_entries}')
    total_masks = 1 << k
    if total_masks > max_masks:
        raise PermanentResourceLimit(
            f'{total_masks} cross-entry masks exceed cap {max_masks}')

    # Each mask can trigger one subset DP per block. Bound loop/state visits
    # before enumeration, including sparse cases where arithmetic is skipped.
    state_visit_upper_bound = total_masks * sum(
        1 << len(rows_by_group[group]) for group in groups)
    if state_visit_upper_bound > max_dp_state_visits:
        raise PermanentResourceLimit(
            f'subset-DP state-visit estimate {state_visit_upper_bound} '
            f'exceeds cap {max_dp_state_visits}')

    # Each nonterminal reachable DP state scans every column in its residual
    # block. This bound assumes every mask triggers every block DP and every
    # state is reachable; it is intentionally conservative.
    transition_scan_upper_bound = total_masks * sum(
        len(rows_by_group[group]) * (1 << len(rows_by_group[group]))
        for group in groups)
    if transition_scan_upper_bound > max_dp_transition_scans:
        raise PermanentResourceLimit(
            f'subset-DP transition-scan estimate {transition_scan_upper_bound} '
            f'exceeds cap {max_dp_transition_scans}')

    meter = _WorkMeter(max_arithmetic_operations, max_dp_state_visits,
                       max_dp_transition_scans)
    degree_bound = min(n, k)
    coefficients = [Fraction(0)] * (degree_bound + 1)
    matching_subsets = 0

    for mask in range(total_masks):
        used_rows = 0
        used_columns = 0
        selected_count = 0
        selected_weight = Fraction(1)
        valid = True
        for edge_index, (row, column, weight) in enumerate(cross):
            if not (mask >> edge_index) & 1:
                continue
            row_bit = 1 << row
            column_bit = 1 << column
            if used_rows & row_bit or used_columns & column_bit:
                valid = False
                break
            used_rows |= row_bit
            used_columns |= column_bit
            selected_count += 1
            meter.charge()
            selected_weight *= weight
        if not valid:
            continue
        matching_subsets += 1

        block_product = Fraction(1)
        for group in groups:
            block_rows = rows_by_group[group]
            remaining_rows = tuple(i for i in block_rows
                                   if not (used_rows >> i) & 1)
            remaining_columns = tuple(i for i in block_rows
                                      if not (used_columns >> i) & 1)
            if len(remaining_rows) != len(remaining_columns):
                block_product = Fraction(0)
                break
            block = tuple(tuple(exact[i][j] for j in remaining_columns)
                          for i in remaining_rows)
            local = _permanent_subset_dp(block, meter)
            if local == 0:
                block_product = Fraction(0)
                break
            meter.charge()
            block_product *= local

        if block_product == 0:
            continue
        meter.charge(2)  # selected-weight/block-product multiply and coefficient add
        coefficients[selected_count] += selected_weight * block_product

    return SparseBoundaryResult(
        coefficients=tuple(coefficients),
        cross_entries=k,
        masks_examined=total_masks,
        matching_subsets=matching_subsets,
        arithmetic_operations=meter.operations,
        dp_state_visits=meter.state_visits,
        dp_transition_scans=meter.transition_scans,
        max_block_size=largest_block,
    )


def brute_force_permanent_polynomial(
    matrix: Sequence[Sequence[Exact]],
    block_labels: Sequence[Hashable],
    *,
    max_dimension: int = 9,
) -> tuple[Fraction, ...]:
    """Independent permutation enumeration for tiny differential tests only."""
    exact = _matrix_exact(matrix)
    n = len(exact)
    group_ids = _normalized_group_ids(block_labels, n)
    if n > max_dimension:
        raise ValueError(f'brute-force reference is capped at dimension {max_dimension}')
    cross_count = sum(exact[i][j] != 0 and group_ids[i] != group_ids[j]
                      for i in range(n) for j in range(n))
    coefficients = [Fraction(0)] * (min(n, cross_count) + 1)
    for permutation in permutations(range(n)):
        product = Fraction(1)
        degree = 0
        for row, column in enumerate(permutation):
            entry = exact[row][column]
            if entry == 0:
                product = Fraction(0)
                break
            product *= entry
            degree += group_ids[row] != group_ids[column]
        if product:
            coefficients[degree] += product
    return tuple(coefficients)


def _randomized_differential_cases(cases: int = 330,
                                   seed: int = 20261031) -> dict[str, int]:
    rng = random.Random(seed)
    max_cross = 0
    max_dimension = 0
    max_operations = 0
    max_state_visits = 0
    max_transition_scans = 0
    for _ in range(cases):
        n = rng.randint(2, 7)
        label_range = rng.randint(1, min(4, n))
        labels = tuple(rng.randrange(label_range) for _ in range(n))
        matrix = [[0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if labels[i] == labels[j] and rng.random() < 0.72:
                    matrix[i][j] = rng.choice((-4, -3, -2, -1, 1, 2, 3, 4))
        candidates = [(i, j) for i in range(n) for j in range(n)
                      if labels[i] != labels[j]]
        edge_count = rng.randint(0, min(11, len(candidates)))
        for i, j in rng.sample(candidates, edge_count):
            matrix[i][j] = rng.choice((-5, -4, -3, -2, -1, 1, 2, 3, 4, 5))
        actual = sparse_boundary_permanent_coefficients(
            matrix, labels, max_cross_entries=11,
            max_block_size=7, max_masks=1 << 11,
            max_arithmetic_operations=1_000_000)
        expected = brute_force_permanent_polynomial(matrix, labels)
        if actual.coefficients != expected:
            raise AssertionError(
                f'random differential mismatch: n={n}, labels={labels}, '
                f'got={actual.coefficients}, expected={expected}')
        max_cross = max(max_cross, actual.cross_entries)
        max_dimension = max(max_dimension, n)
        max_operations = max(max_operations, actual.arithmetic_operations)
        max_state_visits = max(max_state_visits, actual.dp_state_visits)
        max_transition_scans = max(max_transition_scans, actual.dp_transition_scans)
    return {'cases': cases, 'seed': seed, 'max_cross_entries': max_cross,
            'max_dimension': max_dimension, 'max_exact_arithmetic_operations': max_operations,
            'max_subset_dp_state_visits': max_state_visits,
            'max_subset_dp_transition_scans': max_transition_scans}


def _large_cycle_case() -> dict[str, object]:
    n = 64
    matrix = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1
    labels = tuple(range(n))  # singleton diagonal blocks
    edges = (
        (0, 1, 2), (1, 0, 3),
        (2, 3, 1), (3, 4, 2), (4, 2, 4),
        (5, 6, 1), (6, 7, 2), (7, 5, 3),
    )
    for row, column, weight in edges:
        matrix[row][column] = weight
    result = sparse_boundary_permanent_coefficients(
        matrix, labels, max_cross_entries=8, max_block_size=1,
        max_masks=1 << 8, max_arithmetic_operations=1_000_000)
    # The independent cycle-factor calculation is (1+6*z**2)(1+8*z**3)(1+6*z**3).
    expected = (Fraction(1), Fraction(0), Fraction(6), Fraction(14),
                Fraction(0), Fraction(84), Fraction(48), Fraction(0), Fraction(288))
    if result.coefficients != expected or result.permanent_at_one != 441:
        raise AssertionError('64x64 disjoint-cycle check failed')
    return {'dimension': n, 'cross_entries': result.cross_entries,
            'coefficients': [str(x) for x in result.coefficients],
            'permanent_at_one': str(result.permanent_at_one),
            'independent_cycle_product': '(1+6*z^2)(1+8*z^3)(1+6*z^3)',
            'arithmetic_operations': result.arithmetic_operations,
            'subset_dp_state_visits': result.dp_state_visits,
            'subset_dp_transition_scans': result.dp_transition_scans}


def self_test() -> dict[str, object]:
    example = (
        (1, 2, 3),
        (4, 1, 5),
        (6, 7, 1),
    )
    example_result = sparse_boundary_permanent_coefficients(
        example, (0, 1, 2), max_cross_entries=6, max_block_size=1)
    expected_example = (Fraction(1), Fraction(0), Fraction(61), Fraction(144))
    if example_result.coefficients != expected_example:
        raise AssertionError('bundled 3x3 coefficient check failed')
    if example_result.permanent_at_one != 206:
        raise AssertionError('bundled 3x3 permanent check failed')
    if example_result.coefficients != brute_force_permanent_polynomial(example, (0, 1, 2)):
        raise AssertionError('bundled example differs from permutation oracle')

    random_results = _randomized_differential_cases()
    large_result = _large_cycle_case()
    return {
        'schema': 'ETH_SAT_V13_SPARSE_BOUNDARY_PERMANENT_REFERENCE',
        'bundled_example': {
            'coefficients': [str(x) for x in example_result.coefficients],
            'permanent_at_one': str(example_result.permanent_at_one),
            'permutation_oracle': 'MATCH',
        },
        'randomized_differential': random_results,
        'large_cycle_case': large_result,
        'resource_caps_fail_closed': True,
        'arbitrary_dense_permanent_solved': False,
        'subexponential_sat_claim': False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true',
                        help='run exact example, 330 differential cases, and 64x64 check')
    args = parser.parse_args()
    if not args.self_test:
        parser.error('select --self-test')
    print(json.dumps(self_test(), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
