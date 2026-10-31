"""Exact arithmetic in Q[z,V]/(z^J,V^ell)."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from .truncated import TruncatedPolynomial


@dataclass(frozen=True, slots=True)
class BivariateTruncatedPolynomial:
    """Dense rational coefficients indexed by z degree, then V degree."""

    coefficients: tuple[tuple[Fraction, ...], ...]
    z_order: int
    v_order: int

    def __post_init__(self) -> None:
        if self.z_order < 1 or self.v_order < 1:
            raise ValueError("both truncation orders must be positive")
        rows: list[tuple[Fraction, ...]] = []
        for z_degree in range(self.z_order):
            source = self.coefficients[z_degree] if z_degree < len(self.coefficients) else ()
            row = [Fraction(value) for value in source[: self.v_order]]
            row.extend(Fraction(0) for _ in range(self.v_order - len(row)))
            rows.append(tuple(row))
        object.__setattr__(self, "coefficients", tuple(rows))

    @classmethod
    def zero(cls, z_order: int, v_order: int) -> "BivariateTruncatedPolynomial":
        return cls((), z_order, v_order)

    @classmethod
    def one(cls, z_order: int, v_order: int) -> "BivariateTruncatedPolynomial":
        return cls.constant(1, z_order, v_order)

    @classmethod
    def constant(
        cls, value: int | Fraction, z_order: int, v_order: int
    ) -> "BivariateTruncatedPolynomial":
        return cls(((Fraction(value),),), z_order, v_order)

    @classmethod
    def from_z_polynomial(
        cls,
        polynomial: TruncatedPolynomial,
        v_order: int,
        *,
        v_degree: int = 0,
    ) -> "BivariateTruncatedPolynomial":
        if not 0 <= v_degree < v_order:
            raise ValueError("V degree is outside the truncation range")
        rows = []
        for coefficient in polynomial.coefficients:
            row = [Fraction(0)] * v_order
            row[v_degree] = coefficient
            rows.append(tuple(row))
        return cls(tuple(rows), polynomial.order, v_order)

    def _coerce(self, other: object) -> "BivariateTruncatedPolynomial":
        if isinstance(other, BivariateTruncatedPolynomial):
            if (other.z_order, other.v_order) != (self.z_order, self.v_order):
                raise ValueError("bivariate polynomials must use matching truncation orders")
            return other
        if isinstance(other, (int, Fraction)):
            return BivariateTruncatedPolynomial.constant(
                other, self.z_order, self.v_order
            )
        return NotImplemented

    def __add__(self, other: object) -> "BivariateTruncatedPolynomial":
        right = self._coerce(other)
        if right is NotImplemented:
            return NotImplemented
        return BivariateTruncatedPolynomial(
            tuple(
                tuple(a + b for a, b in zip(left_row, right_row))
                for left_row, right_row in zip(self.coefficients, right.coefficients)
            ),
            self.z_order,
            self.v_order,
        )

    def __radd__(self, other: object) -> "BivariateTruncatedPolynomial":
        return self.__add__(other)

    def __neg__(self) -> "BivariateTruncatedPolynomial":
        return BivariateTruncatedPolynomial(
            tuple(tuple(-value for value in row) for row in self.coefficients),
            self.z_order,
            self.v_order,
        )

    def __sub__(self, other: object) -> "BivariateTruncatedPolynomial":
        right = self._coerce(other)
        if right is NotImplemented:
            return NotImplemented
        return self + (-right)

    def __rsub__(self, other: object) -> "BivariateTruncatedPolynomial":
        left = self._coerce(other)
        if left is NotImplemented:
            return NotImplemented
        return left - self

    def __mul__(self, other: object) -> "BivariateTruncatedPolynomial":
        right = self._coerce(other)
        if right is NotImplemented:
            return NotImplemented
        output = [
            [Fraction(0)] * self.v_order for _ in range(self.z_order)
        ]
        for left_z, left_row in enumerate(self.coefficients):
            for right_z, right_row in enumerate(right.coefficients):
                z_degree = left_z + right_z
                if z_degree >= self.z_order:
                    break
                for left_v, left_value in enumerate(left_row):
                    if not left_value:
                        continue
                    for right_v, right_value in enumerate(right_row):
                        v_degree = left_v + right_v
                        if v_degree >= self.v_order:
                            break
                        if right_value:
                            output[z_degree][v_degree] += left_value * right_value
        return BivariateTruncatedPolynomial(
            tuple(tuple(row) for row in output), self.z_order, self.v_order
        )

    def __rmul__(self, other: object) -> "BivariateTruncatedPolynomial":
        return self.__mul__(other)

    def __bool__(self) -> bool:
        return any(value for row in self.coefficients for value in row)

    def coefficient(self, z_degree: int, v_degree: int) -> Fraction:
        if not 0 <= z_degree < self.z_order or not 0 <= v_degree < self.v_order:
            raise IndexError("coefficient degree is outside the truncation range")
        return self.coefficients[z_degree][v_degree]

    def sum_over_v(self) -> TruncatedPolynomial:
        """Apply the paper's final linear coefficient-sum map in V."""
        return TruncatedPolynomial(
            tuple(sum(row, Fraction(0)) for row in self.coefficients),
            self.z_order,
        )

