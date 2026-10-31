"""Exact polynomial #SAT baseline and Hermite reconstruction demo."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from .model import CNF, Literal
from .polynomial import (
    Poly,
    add,
    constant,
    hermite_interpolate,
    multiply,
    subtract,
    taylor_coefficients,
)

ONE = constant(1)
ZERO = constant(0)
ONE_MINUS_T: Poly = (Fraction(1), Fraction(-1))
T: Poly = (Fraction(0), Fraction(1))


@dataclass(frozen=True, slots=True)
class AlgebraicResult:
    count: int
    transformed_degree: int
    interpolation_nodes: tuple[int, ...]
    jet_order: int


def replacement_row(
    num_variables: int, clause_index: int, literal_index: int, literal: Literal
) -> tuple[Poly, ...]:
    """Return a degree-one row P(T) with P(0) equal to the literal's basis row.

    The nonzero endpoint moves mass to a deterministic second coordinate. This
    deliberately simple deformation demonstrates the polynomial interface; it
    is not the paper's spectral low-rank construction.
    """
    if not 1 <= literal.variable <= num_variables:
        raise ValueError("literal variable is outside the formula")
    source = literal.variable - 1
    if num_variables <= 1:
        target = source
    else:
        offset = 1 + ((clause_index + literal_index) % (num_variables - 1))
        target = (source + offset) % num_variables
    row = [ZERO for _ in range(num_variables)]
    row[source] = add(row[source], ONE_MINUS_T)
    row[target] = add(row[target], T)
    return tuple(row)


def _linear_form(row: tuple[Poly, ...], assignment: tuple[int, ...]) -> Poly:
    result = ZERO
    for coefficient, bit in zip(row, assignment):
        if bit:
            result = add(result, coefficient)
    return result


def _clause_factor(
    clause: tuple[Literal, ...],
    clause_index: int,
    assignment: tuple[int, ...],
    num_variables: int,
) -> Poly:
    false_product = ONE
    for literal_index, literal in enumerate(clause):
        row = replacement_row(num_variables, clause_index, literal_index, literal)
        value = _linear_form(row, assignment)
        if literal.negated:
            value = subtract(ONE, value)
        false_product = multiply(false_product, subtract(ONE, value))
    return subtract(ONE, false_product)


def transformed_sum_polynomial(formula: CNF) -> Poly:
    """Build H(T) by summing transformed clause products over all 2^n inputs.

    At T=0 the replacement rows are coordinate vectors, so H(0) is exactly
    the #SAT count. Construction intentionally retains exhaustive enumeration.
    """
    total = ZERO
    n = formula.num_variables
    for mask in range(1 << n):
        assignment = tuple((mask >> index) & 1 for index in range(n))
        term = ONE
        for clause_index, clause in enumerate(formula.clauses):
            term = multiply(
                term, _clause_factor(clause, clause_index, assignment, n)
            )
            if term == ZERO:
                break
        total = add(total, term)
    return total


def algebraic_count(formula: CNF, node_count: int = 2) -> AlgebraicResult:
    """Count with the polynomial baseline and exact Hermite reconstruction."""
    if node_count < 1:
        raise ValueError("node_count must be positive")
    polynomial = transformed_sum_polynomial(formula)
    nodes = tuple(range(1, node_count + 1))
    # QJ > deg(H), so the Q Taylor jets uniquely determine H.
    jet_order = max(1, (len(polynomial) + node_count - 1) // node_count)
    jets = tuple(taylor_coefficients(polynomial, node, jet_order) for node in nodes)
    reconstructed = hermite_interpolate(nodes, jets)
    value = reconstructed[0]
    if value.denominator != 1:
        raise ArithmeticError("exact interpolation returned a noninteger count")
    return AlgebraicResult(int(value), len(polynomial) - 1, nodes, jet_order)


def grouped_count(formula: CNF, group_size: int = 4) -> int:
    """Count by multiplying group-owned factors for each tuple of group states.

    This exposes grouped factor evaluation but still visits every global
    assignment. Groups are not assumed to disconnect the formula.
    """
    if group_size < 1:
        raise ValueError("group_size must be positive")
    n = formula.num_variables
    groups = tuple(
        tuple(range(start, min(start + group_size, n)))
        for start in range(0, n, group_size)
    )
    if not groups:
        groups = (tuple(),)
    variable_group = {
        variable: group_index
        for group_index, group in enumerate(groups)
        for variable in group
    }
    owned: list[list[tuple[Literal, ...]]] = [[] for _ in groups]
    for clause in formula.clauses:
        owner = variable_group[clause[0].variable - 1] if clause else 0
        owned[owner].append(clause)
    count = 0
    group_states = [tuple(product((0, 1), repeat=len(group))) for group in groups]
    for local_states in product(*group_states):
        assignment = [0] * n
        for group, state in zip(groups, local_states):
            for variable, bit in zip(group, state):
                assignment[variable] = bit
        if all(
            any(literal.value(assignment[literal.variable - 1]) for literal in clause)
            for clauses in owned
            for clause in clauses
        ):
            count += 1
    return count
