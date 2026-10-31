"""End-to-end deterministic subexponential #k-SAT counting pipeline.

The implementation follows the paper's proof structure: disjoint
sparsification, sparse-formula parity compression, then the exact sparse
polynomial common-zero counter. Practical work limits are explicit because
some of the proof's deterministic searches are intentionally enormous.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product
from math import comb, isqrt
from typing import Callable, Iterable, Iterator, Sequence

from .common_zeros import SparseSystemCountResult, count_sparse_polynomial_zeros
from .model import CNF
from .references import exhaustive_count
from .reductions import iter_sparsified_leaves, normalize_clause_family
from .sparse import F2Polynomial, SparsePolynomialSystem


@dataclass(frozen=True, slots=True)
class ParityCompressionResult:
    count: int
    clauses: int
    occurrence_bound: int
    initial_checks: int
    parity_checks: int
    common_zero_queries: int
    initial_row_supports: tuple[tuple[int, ...], ...]
    selected_row_supports: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class SubexponentialCountResult:
    count: int
    variables: int
    max_clause_width: int
    sparsification_sigma: Fraction | None
    leaves_processed: int
    used_finite_size_fallback: bool


def _signed_clauses(formula: CNF) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(-lit.variable if lit.negated else lit.variable for lit in clause)
        for clause in formula.clauses
    )


def _equation_for_row(
    clause_equations: Sequence[F2Polynomial], support: Iterable[int]
) -> F2Polynomial:
    if not clause_equations:
        raise ValueError("a parity row requires at least one clause")
    result = F2Polynomial.zero(clause_equations[0].num_variables)
    for clause_index in support:
        result = result + clause_equations[clause_index]
    return result


def _find_epsilon_biased_shifts(
    q: int,
    degree: int,
    *,
    B: int,
    mu: int,
    max_candidates: int | None,
) -> tuple[int, ...]:
    if q == 1:
        return (0,) * degree
    candidates = q**degree
    if max_candidates is not None and candidates > max_candidates:
        raise ValueError(
            "deterministic Tanner shift search needs "
            f"{candidates} candidates, above --max-construction-candidates="
            f"{max_candidates}"
        )
    denominator = 200 * B * mu
    for shifts in product(range(q), repeat=degree):
        balanced = True
        for character in range(1, q):
            bias = sum(
                1 if (character & shift).bit_count() % 2 == 0 else -1
                for shift in shifts
            )
            if abs(bias) * denominator > degree:
                balanced = False
                break
        if balanced:
            return tuple(shifts)
    raise ArithmeticError("the manuscript's biased-shift existence bound failed")


def _find_local_code_rows(
    degree: int,
    B: int,
    mu: int,
    *,
    max_candidates: int | None,
) -> tuple[int, ...]:
    rows = (degree + 8 * B - 1) // (8 * B)
    delta_numerator = degree
    delta_denominator = 100 * B * mu
    minimum_distance = (delta_numerator + delta_denominator - 1) // delta_denominator
    maximum_bad_weight = minimum_distance - 1
    if maximum_bad_weight <= 0:
        return (0,) * rows

    candidate_count = 1 << (rows * degree)
    if max_candidates is not None and candidate_count > max_candidates:
        raise ValueError(
            "deterministic Tanner local-code search needs "
            f"{candidate_count} candidates, above --max-construction-candidates="
            f"{max_candidates}"
        )
    row_mask = (1 << degree) - 1
    for candidate in range(candidate_count):
        local_rows = tuple(
            (candidate >> (row_index * degree)) & row_mask
            for row_index in range(rows)
        )
        valid = True
        for weight in range(1, min(maximum_bad_weight, degree) + 1):
            for indices in combinations(range(degree), weight):
                word = sum(1 << index for index in indices)
                if not any((row & word).bit_count() & 1 for row in local_rows):
                    valid = False
                    break
            if not valid:
                break
        if valid:
            return local_rows
    raise ArithmeticError("the local-code existence bound failed")


def build_initial_parity_checks(
    formula: CNF,
    *,
    occurrence_bound: int | None = None,
    max_construction_candidates: int | None = None,
) -> tuple[tuple[int, ...], ...]:
    """Construct the shortened Tanner-code checks from the manuscript.

    Rows are supports over zero-based clause indices. The exact searches have
    a guard by default; pass ``None`` to run them without a candidate cap.
    """
    m = len(formula.clauses)
    if m == 0:
        return ()
    if any(not clause for clause in formula.clauses):
        return ()
    observed: list[int] = [0] * formula.num_variables
    for clause in formula.clauses:
        for literal in clause:
            observed[literal.variable - 1] += 1
    B = occurrence_bound or max(observed, default=1)
    if B < 1 or any(value > B for value in observed):
        raise ValueError("occurrence_bound does not bound every variable")

    mu = m.bit_length()
    P = 20_000 * B * B * mu * mu
    D0 = 320_000 * B * B * mu**3
    degree = min(m, D0)
    q = 1
    while q * degree < m:
        q *= 2

    shifts = _find_epsilon_biased_shifts(
        q,
        degree,
        B=B,
        mu=mu,
        max_candidates=max_construction_candidates,
    )
    local_rows = _find_local_code_rows(
        degree,
        B,
        mu,
        max_candidates=max_construction_candidates,
    )

    output: list[tuple[int, ...]] = []
    for vertex in range(q):
        left_edges = tuple(vertex * degree + port for port in range(degree))
        right_edges = tuple(
            (vertex ^ shifts[port]) * degree + port for port in range(degree)
        )
        for edge_indices in (left_edges, right_edges):
            for local_row in local_rows:
                support = tuple(
                    edge_indices[port]
                    for port in range(degree)
                    if (local_row >> port) & 1 and edge_indices[port] < m
                )
                output.append(support)

    if len(output) > 3 * formula.num_variables:
        raise ArithmeticError("Tanner construction exceeded the proved 3n row bound")
    return tuple(output)


def _candidate_supports(
    num_clauses: int, max_list_length: int
) -> Iterator[tuple[int, ...]]:
    """Enumerate every distinct row representable by a list of given length."""
    for weight in range(min(num_clauses, max_list_length) + 1):
        yield from combinations(range(num_clauses), weight)


def _candidate_count(num_clauses: int, max_list_length: int) -> int:
    return sum(
        comb(num_clauses, weight)
        for weight in range(min(num_clauses, max_list_length) + 1)
    )


def count_sparse_formula(
    formula: CNF,
    *,
    max_construction_candidates: int | None = None,
    max_parity_candidates: int | None = None,
    max_fallback_variables: int | None = None,
    max_auxiliary_dimension: int | None = None,
    max_substitution_pairs: int | None = None,
    max_measurement_tuples: int | None = None,
    max_schedule_work: int | None = None,
    zero_counter: Callable[..., SparseSystemCountResult] = count_sparse_polynomial_zeros,
) -> ParityCompressionResult:
    """Count a bounded-occurrence CNF via deterministic parity compression."""
    normalized = normalize_clause_family(_signed_clauses(formula))
    formula = CNF.from_signed_clauses(formula.num_variables, normalized)
    n = formula.num_variables
    m = len(formula.clauses)
    if any(not clause for clause in formula.clauses):
        return ParityCompressionResult(0, m, 0, 0, 0, 0, (), ())
    if m == 0:
        return ParityCompressionResult(1 << n, 0, 0, 0, 0, 0, (), ())

    clause_system = SparsePolynomialSystem.from_cnf(formula)
    occurrence_counts = [0] * n
    for clause in formula.clauses:
        for literal in clause:
            occurrence_counts[literal.variable - 1] += 1
    B = max(1, max(occurrence_counts, default=0))

    # One violation equation per clause already gives O(n) equations here.
    if m <= n:
        counted = zero_counter(
            clause_system,
            max_fallback_variables=max_fallback_variables,
            max_auxiliary_dimension=max_auxiliary_dimension,
            max_substitution_pairs=max_substitution_pairs,
            max_measurement_tuples=max_measurement_tuples,
            max_schedule_work=max_schedule_work,
        )
        return ParityCompressionResult(
            counted.count, m, B, 0, 0, 1, (), ()
        )

    initial_rows = build_initial_parity_checks(
        formula,
        occurrence_bound=B,
        max_construction_candidates=max_construction_candidates,
    )
    selected_rows = list(initial_rows)
    equations = [
        _equation_for_row(clause_system.equations, row) for row in initial_rows
    ]
    search_width = 20_000 * B * B * (m.bit_length() ** 2)
    candidates = _candidate_count(m, search_width)
    if max_parity_candidates is not None and candidates > max_parity_candidates:
        raise ValueError(
            "deterministic parity-row selection needs "
            f"{candidates} distinct candidates per round, above "
            f"--max-parity-candidates={max_parity_candidates}"
        )

    common_zero_queries = 0
    for _ in range(3 * n):
        best_count: int | None = None
        best_support: tuple[int, ...] | None = None
        best_equation: F2Polynomial | None = None
        for support in _candidate_supports(m, search_width):
            candidate_equation = _equation_for_row(clause_system.equations, support)
            candidate_system = SparsePolynomialSystem(
                n, tuple(equations) + (candidate_equation,)
            )
            counted = zero_counter(
                candidate_system,
                max_fallback_variables=max_fallback_variables,
                max_auxiliary_dimension=max_auxiliary_dimension,
                max_substitution_pairs=max_substitution_pairs,
                max_measurement_tuples=max_measurement_tuples,
                max_schedule_work=max_schedule_work,
            )
            common_zero_queries += 1
            if best_count is None or counted.count < best_count:
                best_count = counted.count
                best_support = support
                best_equation = candidate_equation
        if best_count is None or best_support is None or best_equation is None:
            raise ArithmeticError("parity-row candidate set unexpectedly empty")
        selected_rows.append(best_support)
        equations.append(best_equation)

    return ParityCompressionResult(
        best_count,
        m,
        B,
        len(initial_rows),
        3 * n,
        common_zero_queries,
        initial_rows,
        tuple(selected_rows[len(initial_rows) :]),
    )


def _sparsification_scale(num_variables: int) -> int:
    lam = (num_variables - 1).bit_length()
    nu = (lam - 1).bit_length()
    if nu == 0:
        return 0
    return isqrt(lam // (nu**4))


def count_subexponential(
    formula: CNF,
    *,
    sparsification_sigma: Fraction | None = None,
    max_fallback_variables: int | None = None,
    max_construction_candidates: int | None = None,
    max_parity_candidates: int | None = None,
    max_auxiliary_dimension: int | None = None,
    max_substitution_pairs: int | None = None,
    max_measurement_tuples: int | None = None,
    max_schedule_work: int | None = None,
) -> SubexponentialCountResult:
    """Count a general fixed-width CNF using the paper's full reduction chain.

    The theorem's finite-size cases use direct counting. Configured fallback
    limits prevent accidentally launching an unbounded truth-table search.
    """
    n = formula.num_variables
    k = max(2, max((len(clause) for clause in formula.clauses), default=0))
    normalized = normalize_clause_family(_signed_clauses(formula), max_width=k)
    formula = CNF.from_signed_clauses(n, normalized)
    if any(not clause for clause in formula.clauses):
        return SubexponentialCountResult(0, n, k, None, 0, False)
    if not formula.clauses:
        return SubexponentialCountResult(1 << n, n, k, None, 0, False)

    scale = _sparsification_scale(n)
    if sparsification_sigma is None and (n < 20 or scale < 2):
        if max_fallback_variables is not None and n > max_fallback_variables:
            raise ValueError(
                "the manuscript uses a finite-size exact fallback for this input; "
                f"DPLL is above the configured {max_fallback_variables}-variable limit"
            )
        count = exhaustive_count(formula)
        return SubexponentialCountResult(count, n, k, None, 0, True)

    sigma = (
        Fraction(sparsification_sigma)
        if sparsification_sigma is not None
        else Fraction(1, scale)
    )
    if not 0 < sigma <= 1:
        raise ValueError("sparsification_sigma must lie in (0,1]")
    leaves_processed = 0
    total_count = 0
    for leaf in iter_sparsified_leaves(formula, k=k, sigma=sigma):
        result = count_sparse_formula(
            leaf,
            max_construction_candidates=max_construction_candidates,
            max_parity_candidates=max_parity_candidates,
            max_fallback_variables=max_fallback_variables,
            max_auxiliary_dimension=max_auxiliary_dimension,
            max_substitution_pairs=max_substitution_pairs,
            max_measurement_tuples=max_measurement_tuples,
            max_schedule_work=max_schedule_work,
        )
        total_count += result.count
        leaves_processed += 1
    return SubexponentialCountResult(
        total_count, n, k, sigma, leaves_processed, False
    )
