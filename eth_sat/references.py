"""Independent reference counters for small formulas."""

from __future__ import annotations

from itertools import product

from .model import CNF


_NUMPY_MIN_VARIABLES = 12  # below this the pure-Python loop is already instant
_NUMPY_LOW_BITS = 20  # enumerate 2**20 assignments per vectorised block


def _exhaustive_count_python(formula: CNF) -> int:
    count = 0
    for assignment in product((False, True), repeat=formula.num_variables):
        if formula.is_satisfied(assignment):
            count += 1
    return count


def _exhaustive_count_numpy(formula: CNF, np) -> int:
    """Vectorised truth table: the low bits are array lanes, the high bits are looped."""
    n = formula.num_variables
    low = min(n, _NUMPY_LOW_BITS)
    lanes = np.arange(1 << low, dtype=np.uint32)
    bit = [((lanes >> j) & 1).astype(bool) for j in range(low)]
    clauses = [
        [(literal.variable - 1, not literal.negated) for literal in clause]
        for clause in formula.clauses
    ]
    total = 0
    for high in range(1 << (n - low)):
        alive = np.ones(1 << low, dtype=bool)
        for clause in clauses:
            satisfied = np.zeros(1 << low, dtype=bool)
            constant_true = False
            for variable, positive in clause:
                if variable < low:
                    satisfied |= bit[variable] if positive else ~bit[variable]
                elif bool((high >> (variable - low)) & 1) == positive:
                    constant_true = True
                    break
            if constant_true:
                continue
            alive &= satisfied
            if not alive.any():
                break
        total += int(alive.sum())
    return total


def exhaustive_count(formula: CNF) -> int:
    """Direct truth-table count; intentionally independent of algebraic code.

    Uses NumPy when it is installed (13-37x faster for 16-22 variables); the result is
    identical to the pure-Python loop, which remains the fallback.
    """
    if formula.num_variables >= _NUMPY_MIN_VARIABLES:
        try:
            import numpy as np
        except ImportError:
            pass
        else:
            return _exhaustive_count_numpy(formula, np)
    return _exhaustive_count_python(formula)


def dpll_count(formula: CNF) -> int:
    """Exact recursive DPLL count with unit propagation and free-variable counts."""
    clauses = tuple(
        tuple(
            (literal.variable - 1, not literal.negated) for literal in clause
        )
        for clause in formula.clauses
    )
    n = formula.num_variables

    def recurse(seed: tuple[int, ...]) -> int:
        assignment = list(seed)
        while True:
            changed = False
            for clause in clauses:
                satisfied = False
                unknown: list[tuple[int, bool]] = []
                for variable, polarity in clause:
                    value = assignment[variable]
                    if value < 0:
                        unknown.append((variable, polarity))
                    elif bool(value) == polarity:
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not unknown:
                    return 0
                if len(unknown) == 1:
                    variable, polarity = unknown[0]
                    forced = int(polarity)
                    if assignment[variable] >= 0 and assignment[variable] != forced:
                        return 0
                    if assignment[variable] < 0:
                        assignment[variable] = forced
                        changed = True
            if not changed:
                break

        unsatisfied: list[tuple[tuple[int, bool], ...]] = []
        for clause in clauses:
            if any(
                assignment[variable] >= 0
                and bool(assignment[variable]) == polarity
                for variable, polarity in clause
            ):
                continue
            unsatisfied.append(clause)
        if not unsatisfied:
            return 1 << sum(value < 0 for value in assignment)

        # Branch on a still-unassigned variable with the most unresolved uses.
        frequencies = [0] * n
        for clause in unsatisfied:
            for variable, _ in clause:
                if assignment[variable] < 0:
                    frequencies[variable] += 1
        variable = max(range(n), key=lambda index: frequencies[index])
        if frequencies[variable] == 0:
            return 0
        total = 0
        for bit in (0, 1):
            child = assignment.copy()
            child[variable] = bit
            total += recurse(tuple(child))
        return total

    return recurse(tuple([-1] * n))
