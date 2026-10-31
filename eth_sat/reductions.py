"""Count-preserving CNF reductions from the manuscript."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb
from typing import Iterator, Sequence

from .model import CNF

SignedClause = tuple[int, ...]
ClauseFamily = tuple[SignedClause, ...]


@dataclass(frozen=True, slots=True)
class SparsificationParameters:
    k: int
    sigma: Fraction
    threshold_base: int
    occurrence_bound: int
    depth_constant: int
    branch_constant: int


def normalize_clause_family(
    clauses: Sequence[Sequence[int]], *, max_width: int | None = None
) -> ClauseFamily:
    """Remove tautologies, repeated literals, duplicates and subsumed clauses."""
    normalized: set[frozenset[int]] = set()
    for source in clauses:
        clause = frozenset(source)
        if any(-literal in clause for literal in clause):
            continue
        if max_width is not None and len(clause) > max_width:
            raise ValueError("clause exceeds max_width")
        normalized.add(clause)
    if frozenset() in normalized:
        return ((),)

    kept: list[frozenset[int]] = []
    for clause in sorted(normalized, key=lambda item: (len(item), tuple(sorted(item)))):
        redundant = False
        ordered = tuple(sorted(clause))
        for size in range(len(ordered)):
            if any(frozenset(subset) in kept for subset in combinations(ordered, size)):
                redundant = True
                break
        if not redundant:
            kept.append(clause)
    return tuple(tuple(sorted(clause)) for clause in kept)


def choose_sparsification_parameters(
    k: int, sigma: Fraction | int
) -> SparsificationParameters:
    """Choose the exact power-of-two thresholds from the appendix."""
    sigma = Fraction(sigma)
    if k < 2:
        raise ValueError("k must be at least 2")
    if not 0 < sigma <= 1:
        raise ValueError("sigma must lie in (0,1]")
    gamma = 2 * (3 ** (k - 1) - 1)
    base = 1
    while base < max(2, gamma):
        base *= 2
    while True:
        depth_constant = 4 * sum((3 * base) ** degree for degree in range(k - 1))
        logarithm = _ceil_log2(4 * depth_constant * base)
        if gamma * logarithm * sigma.denominator <= sigma.numerator * base:
            break
        base *= 2
    occurrence_bound = 2 * sum(base**degree for degree in range(k))
    return SparsificationParameters(
        k=k,
        sigma=sigma,
        threshold_base=base,
        occurrence_bound=occurrence_bound,
        depth_constant=depth_constant,
        branch_constant=gamma,
    )


def _ceil_log2(value: int) -> int:
    if value < 1:
        raise ValueError("logarithm input must be positive")
    return (value - 1).bit_length()


def _branch_choice(
    clauses: ClauseFamily, k: int, threshold_base: int
) -> tuple[int, frozenset[int], tuple[SignedClause, ...]] | None:
    by_width: dict[int, list[frozenset[int]]] = {}
    for clause in clauses:
        by_width.setdefault(len(clause), []).append(frozenset(clause))
    for width in range(1, k + 1):
        width_clauses = by_width.get(width, [])
        counts: dict[frozenset[int], int] = {}
        for clause in width_clauses:
            literals = tuple(sorted(clause))
            for size in range(1, width):
                for subset in combinations(literals, size):
                    shared = frozenset(subset)
                    counts[shared] = counts.get(shared, 0) + 1
        candidates = [
            shared
            for shared, count in counts.items()
            if count >= threshold_base ** (width - len(shared))
        ]
        if candidates:
            shared = min(candidates, key=lambda item: (-len(item), tuple(sorted(item))))
            selected = tuple(
                tuple(sorted(clause)) for clause in width_clauses if shared.issubset(clause)
            )
            return width, shared, selected
    return None


def _split_clause_family(
    clauses: ClauseFamily,
    k: int,
    threshold_base: int,
) -> tuple[ClauseFamily, ClauseFamily] | None:
    choice = _branch_choice(clauses, k, threshold_base)
    if choice is None:
        return None
    _width, shared, selected = choice
    selected_set = set(selected)
    other = [clause for clause in clauses if clause not in selected_set]
    child_a = normalize_clause_family((*other, tuple(sorted(shared))), max_width=k)
    petals = [tuple(sorted(set(clause).difference(shared))) for clause in selected]
    negative_units = [(-literal,) for literal in sorted(shared)]
    child_b = normalize_clause_family((*other, *petals, *negative_units), max_width=k)
    return child_a, child_b


def iter_sparsified_leaves(
    formula: CNF,
    *,
    k: int,
    sigma: Fraction | int,
) -> Iterator[CNF]:
    """Yield disjoint sparsification leaves in deterministic depth-first order."""
    parameters = choose_sparsification_parameters(k, sigma)
    root = normalize_clause_family(
        tuple(
            tuple(-literal.variable if literal.negated else literal.variable for literal in clause)
            for clause in formula.clauses
        ),
        max_width=k,
    )
    stack: list[ClauseFamily] = [root]
    while stack:
        clauses = stack.pop()
        split = _split_clause_family(
            clauses, k, parameters.threshold_base
        )
        if split is None:
            yield CNF.from_signed_clauses(formula.num_variables, clauses)
            continue
        child_a, child_b = split
        stack.append(child_b)
        stack.append(child_a)


def to_3cnf_with_unique_extensions(formula: CNF) -> CNF:
    """Replace wide clauses with OR-gate constraints, preserving the count."""
    clauses: list[SignedClause] = []
    next_variable = formula.num_variables
    for clause in formula.clauses:
        literals = tuple(
            -literal.variable if literal.negated else literal.variable
            for literal in clause
        )
        if len(literals) <= 3:
            clauses.append(literals)
            continue
        left = literals[0]
        right = literals[1]
        next_variable += 1
        output = next_variable
        _append_or_gate(clauses, left, right, output)
        for literal in literals[2:-2]:
            left = output
            right = literal
            next_variable += 1
            output = next_variable
            _append_or_gate(clauses, left, right, output)
        clauses.append((output, literals[-2], literals[-1]))
    normalized = normalize_clause_family(clauses, max_width=3)
    return CNF.from_signed_clauses(next_variable, normalized)


def _append_or_gate(clauses: list[SignedClause], left: int, right: int, output: int) -> None:
    clauses.extend(((-left, output), (-right, output), (left, right, -output)))


def copy_occurrences_to_three_cnf(formula: CNF) -> CNF:
    """Use an implication cycle so each copied variable occurs at most thrice."""
    clauses: list[list[int]] = [
        [
            -literal.variable if literal.negated else literal.variable
            for literal in clause
        ]
        for clause in formula.clauses
    ]
    positions: dict[int, list[tuple[int, int]]] = {
        variable: [] for variable in range(1, formula.num_variables + 1)
    }
    for clause_index, clause in enumerate(clauses):
        for position, literal in enumerate(clause):
            positions[abs(literal)].append((clause_index, position))

    next_variable = formula.num_variables
    for variable in range(1, formula.num_variables + 1):
        occurrences = positions[variable]
        if len(occurrences) < 2:
            continue
        copies = [variable]
        for _ in range(len(occurrences) - 1):
            next_variable += 1
            copies.append(next_variable)
        for (clause_index, position), copy in zip(occurrences, copies):
            sign = 1 if clauses[clause_index][position] > 0 else -1
            clauses[clause_index][position] = sign * copy
        for index, copy in enumerate(copies):
            successor = copies[(index + 1) % len(copies)]
            clauses.append([-copy, successor])

    normalized = normalize_clause_family(clauses, max_width=3)
    return CNF.from_signed_clauses(next_variable, normalized)


def reduce_to_three_occurrence_cnf(formula: CNF) -> CNF:
    """Apply the count-preserving gate and variable-copy reductions."""
    return copy_occurrences_to_three_cnf(to_3cnf_with_unique_extensions(formula))

