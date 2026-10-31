"""Exact univariate polynomials in Q[z]/(z**order)."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable


@dataclass(frozen=True, slots=True)
class TruncatedPolynomial:
    """Fixed-width rational coefficient vector with multiplication truncated."""

    coefficients: tuple[Fraction, ...]
    order: int

    def __post_init__(self) -> None:
        if self.order < 1:
            raise ValueError("truncation order must be positive")
        values = [Fraction(value) for value in self.coefficients[: self.order]]
        values.extend(Fraction(0) for _ in range(self.order - len(values)))
        object.__setattr__(self, "coefficients", tuple(values))

    @classmethod
    def from_coefficients(
        cls, coefficients: Iterable[int | Fraction], order: int
    ) -> "TruncatedPolynomial":
        return cls(tuple(Fraction(value) for value in coefficients), order)

    @classmethod
    def constant(
        cls, value: int | Fraction, order: int
    ) -> "TruncatedPolynomial":
        return cls((Fraction(value),), order)

    @classmethod
    def zero(cls, order: int) -> "TruncatedPolynomial":
        return cls.constant(0, order)

    @classmethod
    def one(cls, order: int) -> "TruncatedPolynomial":
        return cls.constant(1, order)

    def _coerce(self, other: object) -> "TruncatedPolynomial":
        if isinstance(other, TruncatedPolynomial):
            if other.order != self.order:
                raise ValueError("truncated polynomials must use the same order")
            return other
        if isinstance(other, (int, Fraction)):
            return TruncatedPolynomial.constant(other, self.order)
        return NotImplemented

    def __add__(self, other: object) -> "TruncatedPolynomial":
        right = self._coerce(other)
        if right is NotImplemented:
            return NotImplemented
        return TruncatedPolynomial(
            tuple(a + b for a, b in zip(self.coefficients, right.coefficients)),
            self.order,
        )

    def __radd__(self, other: object) -> "TruncatedPolynomial":
        return self.__add__(other)

    def __neg__(self) -> "TruncatedPolynomial":
        return TruncatedPolynomial(tuple(-value for value in self.coefficients), self.order)

    def __sub__(self, other: object) -> "TruncatedPolynomial":
        right = self._coerce(other)
        if right is NotImplemented:
            return NotImplemented
        return self + (-right)

    def __rsub__(self, other: object) -> "TruncatedPolynomial":
        left = self._coerce(other)
        if left is NotImplemented:
            return NotImplemented
        return left - self

    def __mul__(self, other: object) -> "TruncatedPolynomial":
        right = self._coerce(other)
        if right is NotImplemented:
            return NotImplemented
        output = [Fraction(0)] * self.order
        for left_degree, left_value in enumerate(self.coefficients):
            if not left_value:
                continue
            for right_degree, right_value in enumerate(right.coefficients):
                degree = left_degree + right_degree
                if degree >= self.order:
                    break
                if right_value:
                    output[degree] += left_value * right_value
        return TruncatedPolynomial(tuple(output), self.order)

    def __rmul__(self, other: object) -> "TruncatedPolynomial":
        return self.__mul__(other)

    def __bool__(self) -> bool:
        return any(self.coefficients)

    def coefficient(self, degree: int) -> Fraction:
        if not 0 <= degree < self.order:
            raise IndexError("degree is outside the truncated polynomial")
        return self.coefficients[degree]
