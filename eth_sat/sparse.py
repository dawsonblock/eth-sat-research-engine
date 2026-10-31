"""Sparse multilinear polynomial systems over F2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .model import CNF

Monomial = tuple[int, ...]


@dataclass(frozen=True, slots=True)
class F2Polynomial:
    """A Boolean polynomial as a list of squarefree monomials.

    Variables use zero-based indices. Repeated variables inside a monomial
    collapse by ``x_i**2 = x_i`` and repeated monomials cancel modulo two.
    """

    num_variables: int
    monomials: tuple[Monomial, ...]

    def __post_init__(self) -> None:
        if self.num_variables < 0:
            raise ValueError("num_variables must be nonnegative")
        parity: set[Monomial] = set()
        for source in self.monomials:
            monomial = tuple(sorted(set(source)))
            if any(index < 0 or index >= self.num_variables for index in monomial):
                raise ValueError("monomial contains an invalid variable index")
            if monomial in parity:
                parity.remove(monomial)
            else:
                parity.add(monomial)
        object.__setattr__(self, "monomials", tuple(sorted(parity)))

    @classmethod
    def zero(cls, num_variables: int) -> "F2Polynomial":
        return cls(num_variables, ())

    @classmethod
    def one(cls, num_variables: int) -> "F2Polynomial":
        return cls(num_variables, ((),))

    @property
    def degree(self) -> int:
        return max((len(monomial) for monomial in self.monomials), default=-1)

    @property
    def scope(self) -> tuple[int, ...]:
        return tuple(sorted({index for monomial in self.monomials for index in monomial}))

    def evaluate(self, assignment: Iterable[int | bool]) -> int:
        bits = tuple(int(value) for value in assignment)
        if len(bits) != self.num_variables or any(bit not in (0, 1) for bit in bits):
            raise ValueError("assignment must be a Boolean vector of the declared width")
        value = 0
        for monomial in self.monomials:
            term = 1
            for index in monomial:
                term &= bits[index]
            value ^= term
        return value

    def __add__(self, other: "F2Polynomial") -> "F2Polynomial":
        if self.num_variables != other.num_variables:
            raise ValueError("polynomials must have the same variable count")
        return F2Polynomial(self.num_variables, self.monomials + other.monomials)

    def __mul__(self, other: "F2Polynomial") -> "F2Polynomial":
        if self.num_variables != other.num_variables:
            raise ValueError("polynomials must have the same variable count")
        products = tuple(
            tuple(sorted(set(left).union(right)))
            for left in self.monomials
            for right in other.monomials
        )
        return F2Polynomial(self.num_variables, products)

    def restrict(self, fixed: Mapping[int, int | bool]) -> "F2Polynomial":
        """Substitute fixed bits and compact the remaining variable indices."""
        normalized = {int(index): int(value) for index, value in fixed.items()}
        if any(index < 0 or index >= self.num_variables for index in normalized):
            raise ValueError("fixed variable index is outside the polynomial")
        if any(value not in (0, 1) for value in normalized.values()):
            raise ValueError("fixed values must be Boolean")
        free_variables = tuple(
            index for index in range(self.num_variables) if index not in normalized
        )
        new_index = {old: new for new, old in enumerate(free_variables)}
        restricted: list[Monomial] = []
        for monomial in self.monomials:
            if any(index in normalized and not normalized[index] for index in monomial):
                continue
            restricted.append(tuple(new_index[index] for index in monomial if index not in normalized))
        return F2Polynomial(len(free_variables), tuple(restricted))


@dataclass(frozen=True, slots=True)
class SparsePolynomialSystem:
    """A finite list of polynomial equations ``P_i(x)=0`` over F2."""

    num_variables: int
    equations: tuple[F2Polynomial, ...]

    def __post_init__(self) -> None:
        if self.num_variables < 0:
            raise ValueError("num_variables must be nonnegative")
        equations = tuple(self.equations)
        if any(equation.num_variables != self.num_variables for equation in equations):
            raise ValueError("every equation must use the declared variable count")
        object.__setattr__(self, "equations", equations)

    @classmethod
    def from_monomials(
        cls,
        num_variables: int,
        equations: Iterable[Iterable[Iterable[int]]],
    ) -> "SparsePolynomialSystem":
        return cls(
            num_variables,
            tuple(
                F2Polynomial(num_variables, tuple(tuple(term) for term in equation))
                for equation in equations
            ),
        )

    @classmethod
    def from_cnf(cls, formula: CNF) -> "SparsePolynomialSystem":
        """Encode each clause's violation indicator as one F2 equation."""
        equations: list[F2Polynomial] = []
        for clause in formula.clauses:
            violation = F2Polynomial.one(formula.num_variables)
            for literal in clause:
                variable = literal.variable - 1
                factor = (
                    F2Polynomial(formula.num_variables, ((), (variable,)))
                    if not literal.negated
                    else F2Polynomial(formula.num_variables, ((variable,),))
                )
                violation = violation * factor
            equations.append(violation)
        return cls(formula.num_variables, tuple(equations))

    @property
    def max_degree(self) -> int:
        return max((equation.degree for equation in self.equations), default=0)

    @property
    def max_monomials(self) -> int:
        return max((len(equation.monomials) for equation in self.equations), default=0)

    @property
    def scopes(self) -> tuple[tuple[int, ...], ...]:
        return tuple(equation.scope for equation in self.equations)

    def evaluate(self, assignment: Iterable[int | bool]) -> bool:
        bits = tuple(assignment)
        return all(equation.evaluate(bits) == 0 for equation in self.equations)

    def restrict(self, fixed: Mapping[int, int | bool]) -> "SparsePolynomialSystem":
        if any(index < 0 or index >= self.num_variables for index in fixed):
            raise ValueError("fixed variable index is outside the system")
        if any(int(value) not in (0, 1) for value in fixed.values()):
            raise ValueError("fixed values must be Boolean")
        restricted = tuple(equation.restrict(fixed) for equation in self.equations)
        num_variables = self.num_variables - len(fixed)
        return SparsePolynomialSystem(num_variables, restricted)

