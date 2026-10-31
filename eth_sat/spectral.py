"""Exact dense implementation of the manuscript's auxiliary spectral object.

The public builder defaults to a small dimension guard for interactive
experiments. The full research counter can disable that guard and constructs
the exact matrix, eigenbasis, measurements, and replacement polynomials over
Q. The implementation is dense; it has no matrix-free execution path.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from math import prod
from typing import Iterator, Sequence

from .polynomial import Poly, add, constant, multiply, scale

Pair = tuple[int, int]
AuxiliaryLabel = tuple[Pair, ...]


@dataclass(frozen=True, slots=True)
class SpectralParameters:
    """Small integer parameters for the auxiliary construction.

    ``interval_start`` selects R consecutive eigenvalue indices in [0, Q].
    The paper's asymptotic parameter and tail-bound checks are deliberately not
    inferred here; this class validates only the finite algebraic construction.
    """

    r: int
    q: int
    degree_window: int
    interval_start: int | None = None

    def __post_init__(self) -> None:
        if self.r < 2:
            raise ValueError("r must be at least 2")
        if self.q < 2:
            raise ValueError("q must be at least 2")
        if not 1 <= self.degree_window < self.q:
            raise ValueError("degree_window must satisfy 1 <= R < Q")
        start = self.interval_start
        if start is None:
            mean = Fraction(self.q * (self.r - 1), 2 * self.r)
            centered_fraction = mean - Fraction(self.degree_window - 1, 2)
            centered = centered_fraction.numerator // centered_fraction.denominator
            start = min(max(centered, 0), self.q - self.degree_window + 1)
            object.__setattr__(self, "interval_start", start)
        elif not isinstance(start, int) or isinstance(start, bool):
            raise ValueError("interval_start must be an integer")
        if not 0 <= start <= self.q - self.degree_window + 1:
            raise ValueError("the interpolation interval must lie in [0, Q]")

    @property
    def interval(self) -> tuple[int, ...]:
        return tuple(
            range(int(self.interval_start), int(self.interval_start) + self.degree_window)
        )

    @property
    def auxiliary_dimension(self) -> int:
        return self.r ** (2 * self.q)


@dataclass(frozen=True, slots=True)
class LocalEigenvector:
    """Sparse local vector on [r] x [r] with swap eigenvalue +/-1."""

    entries: tuple[tuple[Pair, int], ...]
    eigenvalue: int


@dataclass(frozen=True, slots=True)
class SpectralEigenvector:
    """Sparse tensor-product eigenvector and its W0 eigenvalue."""

    entries: tuple[tuple[int, int], ...]  # (coordinate index, coefficient)
    negative_count: int


def local_eigenbasis(r: int) -> tuple[LocalEigenvector, ...]:
    """Return the orthogonal swap eigenbasis described in the manuscript."""
    if r < 2:
        raise ValueError("r must be at least 2")
    basis: list[LocalEigenvector] = []
    for a in range(r):
        basis.append(LocalEigenvector((((a, a), 1),), 1))
    for a in range(r):
        for b in range(a + 1, r):
            basis.append(LocalEigenvector((((a, b), 1), ((b, a), 1)), 1))
            basis.append(LocalEigenvector((((a, b), 1), ((b, a), -1)), -1))
    return tuple(basis)


def _interpolate_signed_values(nodes: Sequence[int]) -> Poly:
    """Interpolate f(j)=(-1)^j exactly at integer nodes."""
    result = constant(0)
    for index, node in enumerate(nodes):
        basis = constant(1)
        denominator = 1
        for other_index, other in enumerate(nodes):
            if other_index == index:
                continue
            basis = multiply(basis, (Fraction(-other), Fraction(1)))
            denominator *= node - other
        result = add(result, scale(basis, Fraction((-1) ** node, denominator)))
    return result


def _multiply_subset_polynomial_by_w(
    polynomial: dict[int, Fraction], q: int
) -> dict[int, Fraction]:
    """Multiply a polynomial in commuting involutions by W0."""
    output: defaultdict[int, Fraction] = defaultdict(Fraction)
    half = Fraction(1, 2)
    for mask, coefficient in polynomial.items():
        for position in range(q):
            output[mask] += coefficient * half
            output[mask ^ (1 << position)] -= coefficient * half
    return {mask: value for mask, value in output.items() if value}


def _partial_swap_coefficients(f: Poly, q: int) -> tuple[tuple[int, Fraction], ...]:
    """Expand f(W0) in products of the commuting swap involutions."""
    power: dict[int, Fraction] = {0: Fraction(1)}
    output: defaultdict[int, Fraction] = defaultdict(Fraction)
    for degree, coefficient in enumerate(f):
        if coefficient:
            for mask, value in power.items():
                output[mask] += coefficient * value
        if degree + 1 < len(f):
            power = _multiply_subset_polynomial_by_w(power, q)
    return tuple(sorted((mask, value) for mask, value in output.items() if value))


class SpectralReference:
    """Dense, exact auxiliary spectral construction for small test dimensions."""

    def __init__(self, parameters: SpectralParameters, max_dimension: int | None = 64):
        if max_dimension is not None and max_dimension < 1:
            raise ValueError("max_dimension must be positive")
        self.parameters = parameters
        dimension = 1
        for _ in range(2 * parameters.q):
            dimension *= parameters.r
            if max_dimension is not None and dimension > max_dimension:
                raise ValueError(
                    "auxiliary dimension exceeds dense reference limit "
                    f"{max_dimension}; use smaller r,Q"
                )
        self.dimension = dimension

        pair_values = tuple(product(range(parameters.r), repeat=2))
        self.coordinates: tuple[AuxiliaryLabel, ...] = tuple(
            product(pair_values, repeat=parameters.q)
        )
        self.coordinate_index = {
            label: index for index, label in enumerate(self.coordinates)
        }
        self.f: Poly = _interpolate_signed_values(parameters.interval)
        self.partial_swap_terms = _partial_swap_coefficients(self.f, parameters.q)
        self.m0: tuple[tuple[Fraction, ...], ...] = self._build_m0()
        self.eigenbasis: tuple[SpectralEigenvector, ...] = tuple(
            self._build_eigenbasis()
        )
        self.measurements: tuple[tuple[int, ...], ...] = tuple(
            tuple(vector[index] for index in range(self.dimension))
            for eigenvector in self.eigenbasis
            if eigenvector.negative_count not in parameters.interval
            for vector in (self._dense_eigenvector(eigenvector),)
        )

    def _build_m0(self) -> tuple[tuple[Fraction, ...], ...]:
        """Build V0 f(W0) using its bounded partial-swap expansion."""
        q = self.parameters.q
        matrix = [
            [Fraction(0) for _ in range(self.dimension)]
            for _ in range(self.dimension)
        ]
        for row_index, label in enumerate(self.coordinates):
            for unchanged_mask, coefficient in self.partial_swap_terms:
                # V0 toggles every position. A monomial in f(W0) toggles the
                # positions set in unchanged_mask, leaving its complement swapped.
                target = tuple(
                    pair if unchanged_mask & (1 << position) else (pair[1], pair[0])
                    for position, pair in enumerate(label)
                )
                column_index = self.coordinate_index[target]
                matrix[row_index][column_index] += coefficient
        return tuple(tuple(row) for row in matrix)

    def _build_eigenbasis(self) -> Iterator[SpectralEigenvector]:
        local = local_eigenbasis(self.parameters.r)
        for choices in product(local, repeat=self.parameters.q):
            negative_count = sum(choice.eigenvalue == -1 for choice in choices)
            entries: list[tuple[int, int]] = []
            supports = [choice.entries for choice in choices]
            for selected in product(*supports):
                label = tuple(pair for pair, _ in selected)
                coefficient = prod(value for _, value in selected)
                entries.append((self.coordinate_index[label], coefficient))
            yield SpectralEigenvector(tuple(sorted(entries)), negative_count)

    def _dense_eigenvector(self, vector: SpectralEigenvector) -> tuple[int, ...]:
        output = [0] * self.dimension
        for index, coefficient in vector.entries:
            output[index] = coefficient
        return tuple(output)

    def apply_m0(self, vector: Sequence[int | Fraction]) -> tuple[Fraction, ...]:
        if len(vector) != self.dimension:
            raise ValueError("vector length does not match auxiliary dimension")
        return tuple(
            sum((entry * Fraction(value) for entry, value in zip(row, vector)), Fraction(0))
            for row in self.m0
        )

    def measurement_component(self, row_index: int) -> tuple[Fraction, ...]:
        """Return e_u^T(I-M0), which must be a combination of C rows."""
        if not 0 <= row_index < self.dimension:
            raise IndexError("auxiliary row index is out of range")
        return tuple(
            Fraction(int(column == row_index)) - self.m0[row_index][column]
            for column in range(self.dimension)
        )

    def replacement_components(
        self, row_index: int
    ) -> tuple[tuple[Fraction, ...], tuple[Poly, ...]]:
        """Return the measurement row and local-coordinate polynomial row."""
        measurement_row = self.measurement_component(row_index)
        owner_label = self.coordinates[row_index]
        local_row = [constant(0) for _ in range(self.dimension)]
        for column_index, coefficient in enumerate(self.m0[row_index]):
            if not coefficient:
                continue
            label = self.coordinates[column_index]
            exceptional_positions = [
                position
                for position, (candidate_pair, owner_pair) in enumerate(
                    zip(label, owner_label)
                )
                if candidate_pair[0] != owner_pair[1]
            ]
            multiplier = constant(1)
            for position in exceptional_positions:
                point = position + 1  # evaluation points are 1-based
                multiplier = multiply(
                    multiplier, (Fraction(1), Fraction(-1, point))
                )
            local_row[column_index] = add(
                local_row[column_index], scale(multiplier, coefficient)
            )
        return measurement_row, tuple(local_row)

    def replacement_row(self, row_index: int) -> tuple[Poly, ...]:
        """Return P_u(T) as a row of exact rational polynomials."""
        measurement_row, local_row = self.replacement_components(row_index)
        return tuple(
            add((measurement_coefficient,), local_polynomial)
            for measurement_coefficient, local_polynomial in zip(
                measurement_row, local_row
            )
        )

    def verify_partial_swap_support(self) -> bool:
        """Check both the expansion degree and induced mismatch bound."""
        maximum = self.parameters.degree_window - 1
        if any(mask.bit_count() > maximum for mask, _ in self.partial_swap_terms):
            return False
        for row_index, source in enumerate(self.coordinates):
            for column_index, coefficient in enumerate(self.m0[row_index]):
                if not coefficient:
                    continue
                target = self.coordinates[column_index]
                mismatches = sum(
                    target_pair[0] != source_pair[1]
                    for target_pair, source_pair in zip(target, source)
                )
                if mismatches > maximum:
                    return False
        return True

    def verify_eigenbasis(self) -> bool:
        """Check every tensor eigenvector and its exact M0 eigenvalue."""
        if len(self.eigenbasis) != self.dimension:
            return False
        interval = self.parameters.interval
        for vector in self.eigenbasis:
            eigenvalue = Fraction((-1) ** vector.negative_count) * sum(
                coefficient
                * self._integer_power(vector.negative_count, degree)
                for degree, coefficient in enumerate(self.f)
            )
            expected = tuple(
                eigenvalue * value
                for value in self._dense_eigenvector(vector)
            )
            if self.apply_m0(self._dense_eigenvector(vector)) != expected:
                return False
            if vector.negative_count in interval and eigenvalue != 1:
                return False
        return True

    @staticmethod
    def _integer_power(value: int, degree: int) -> int:
        return value**degree

    def verify_measurement_rowspace(self) -> tuple[int, ...]:
        """Return rows e_u^T(I-M0) not spanned by the exceptional basis rows."""
        from .verifier import matrix_rank, row_space_contains

        correction_rows = tuple(
            self.measurement_component(row_index)
            for row_index in range(self.dimension)
        )
        base_rank = matrix_rank(self.measurements, width=self.dimension)
        if matrix_rank(
            [*self.measurements, *correction_rows], width=self.dimension
        ) == base_rank:
            return ()
        return tuple(
            row_index
            for row_index, row in enumerate(correction_rows)
            if not row_space_contains(
                self.measurements, row
            )
        )

    def verify_replacement_identities(self) -> tuple[str, ...]:
        """Check interpolation at zero, degree, and local support at all points."""
        errors: list[str] = []
        maximum_degree = self.parameters.degree_window - 1
        for row_index, owner_label in enumerate(self.coordinates):
            measurement_row, local_row = self.replacement_components(row_index)
            at_zero = tuple(
                measurement_row[column]
                + local_row[column][0]
                for column in range(self.dimension)
            )
            expected = tuple(Fraction(int(column == row_index)) for column in range(self.dimension))
            if at_zero != expected:
                errors.append(f"row {row_index} does not restore its basis vector at zero")
            for column, polynomial in enumerate(local_row):
                degree = len(polynomial) - 1 if any(polynomial) else -1
                if degree > maximum_degree:
                    errors.append(f"row {row_index}, column {column} exceeds degree bound")
            for point_index in range(self.parameters.q):
                evaluation_point = point_index + 1
                for column, polynomial in enumerate(local_row):
                    if not _evaluate(polynomial, evaluation_point):
                        continue
                    candidate_label = self.coordinates[column]
                    if candidate_label[point_index][0] != owner_label[point_index][1]:
                        errors.append(
                            f"row {row_index} uses an out-of-group coordinate at point "
                            f"{evaluation_point}"
                        )
        return tuple(errors)


def _evaluate(poly: Sequence[Fraction], point: int | Fraction) -> Fraction:
    value = Fraction(0)
    x = Fraction(point)
    for coefficient in reversed(poly):
        value = value * x + coefficient
    return value


def build_spectral_reference(
    r: int,
    q: int,
    degree_window: int,
    *,
    interval_start: int | None = None,
    max_dimension: int | None = 64,
) -> SpectralReference:
    """Construct and return the guarded tiny exact spectral reference."""
    return SpectralReference(
        SpectralParameters(r, q, degree_window, interval_start),
        max_dimension=max_dimension,
    )
