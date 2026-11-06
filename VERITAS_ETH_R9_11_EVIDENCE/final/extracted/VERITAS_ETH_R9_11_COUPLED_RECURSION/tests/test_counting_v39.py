"""Tests for the shared-linear-summary construction (`sec:counting`, `sec:construction`).

The end-to-end tests compare the full pipeline against exhaustive enumeration,
which is the only independent oracle available at these sizes. The component
tests check each paper lemma against a direct computation:

* `lem:swaps-support`, `lem:swaps-matrix`, `eq:swaps-row` -- the auxiliary
  rows, including the paper's worked Remark.
* `lem:incidence-labels` -- determinism and the reported statistics.
* `lem:measurement-separation` -- the group sum against a direct sum.
* `lem:boolean-differences` -- the inclusion-exclusion identity itself.
* `eq:full-taylor-sum` -- `H(t+z)` against direct evaluation.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import product
from random import Random

import pytest

from veritas.research.eth_counting_v39 import (
    FactorInstance, PolynomialFactor, build_auxiliary_layout, build_embedded_forms,
    build_schedules, cnf_instance, count_cnf, count_instance,
    enumerate_restriction_pairs,
    ring_from_constant, ring_mul, ring_zero, scaled_parameters, separation_sum,
    solve_exact, taylor_equations, taylor_series, theorem_parameters,
    theorem_parameters_from_lambda, verify_layout,
)
from veritas.research.eth_counting_v39.auxiliary import _binomial_polynomial
from veritas.research.eth_counting_v39.layout import in_row_space


def brute_force(instance):
    total = 0
    for bits in product((0, 1), repeat=instance.n):
        value = 1
        for scope, factor in zip(instance.scopes, instance.factors):
            value *= factor.evaluate([bits[v] for v in scope])
        total += value
    return total


# --------------------------------------------------------------------------
# Parameters (`lem:incidence-parameters`, `eq:parameter-QR`).
# --------------------------------------------------------------------------

def test_theorem_parameters_follow_the_paper_formulas():
    """`eq:parameter-QR` at theorem scale, without materialising `n` or `D`."""
    from math import isqrt
    lam = 2 ** 34
    nu = 34                                   # ceil(log2(2**34))
    root = isqrt(lam)
    result = theorem_parameters_from_lambda(lam, b=3, w=3, M=3, d=3, beta=1)
    assert result['status'] == 'THEOREM_PARAMETERS_COMPUTED'
    assert result['r'] == root // (nu * nu)
    assert result['Q'] == lam // (128 * nu)
    assert result['R'] == 4 * root
    assert result['tau'] == str(Fraction(1, result['r'] * lam))
    assert result['epsilon'] == str(Fraction(1, 3 * result['r'] ** 2 * lam))
    assert result['D_materialised'] is False
    assert result['D_bits'] == 2 * result['Q'] * (result['r'] - 1).bit_length()
    # Every numerical hypothesis of lem:incidence-parameters holds here.
    assert all(result['checks'].values()), result['checks']


def test_theorem_parameters_report_degeneracy_instead_of_clamping():
    result = theorem_parameters(n=64, b=3, w=3, M=192, d=192)
    assert result['status'] == 'INCONCLUSIVE_PARAMETERS'
    assert 'r < 2' in result['reason']


def test_scaled_parameters_reject_out_of_range_choices():
    with pytest.raises(ValueError):
        scaled_parameters(4, 3, 3, 12, 12, r=1, Q=2, R=2)
    with pytest.raises(ValueError):
        scaled_parameters(4, 3, 3, 12, 12, r=2, Q=2, R=3)


def test_parameter_summary_reports_the_truncation():
    p = scaled_parameters(4, 3, 3, 12, 12, r=2, Q=2, R=2)
    assert p.degree_bound == 24
    assert p.q == 12
    assert p.J == 13
    assert p.interval == (0, 1)
    assert p.summary()['runtime_bound_proven'] is False


# --------------------------------------------------------------------------
# Auxiliary rows (`eq:swaps-row`, `lem:swaps-matrix`, `lem:swaps-support`).
# --------------------------------------------------------------------------

def test_paper_remark_row_is_reproduced_exactly():
    """The worked example in `main_full_version.tex` l. 2381-2400."""
    p = scaled_parameters(4, 3, 3, 12, 12, r=2, Q=2, R=2)
    layout = build_auxiliary_layout(p)
    # Label (00, 11): a_u = (0,0), d_u = (1,1).
    u = layout.encode([(0, 1), (0, 1)])
    polynomial = layout.row_polynomial(u)
    zero = layout.encode([(0, 1), (0, 1)])      # zeta_0
    one = layout.encode([(1, 0), (0, 1)])       # zeta_1
    two = layout.encode([(0, 1), (1, 0)])       # zeta_2
    assert polynomial[zero] == (Fraction(1),)
    assert polynomial[one] == (Fraction(0), Fraction(-1, 2))
    assert polynomial[two] == (Fraction(0), Fraction(-1),)
    # At T=1 and T=2 the paper's displayed values follow.
    assert layout.evaluate_row(u, 1) == {
        zero: Fraction(1), one: Fraction(-1, 2), two: Fraction(-1)}
    assert layout.evaluate_row(u, 2) == {
        zero: Fraction(1), one: Fraction(-1), two: Fraction(-2)}


@pytest.mark.parametrize('r,Q,R', [(2, 2, 1), (2, 2, 2), (2, 3, 2), (2, 3, 3),
                                   (3, 2, 2), (3, 3, 2)])
def test_auxiliary_structural_checks(r, Q, R):
    p = scaled_parameters(4, 3, 3, 12, 12, r=r, Q=Q, R=R)
    layout = build_auxiliary_layout(p)
    assert layout.check_row_normalisation()      # P_u(0) = delta_u
    assert layout.check_degree_bound()           # deg P_u <= R-1
    assert layout.check_support_bound()          # lem:swaps-support
    assert layout.check_kernel_fixed()           # lem:swaps-matrix
    assert len(layout.measurement_rows) <= layout.D


def test_measurement_rows_are_the_binomial_tail():
    """`c_B <= D * Pr[W not in I]`, and the count matches it exactly."""
    for r, Q, R in ((2, 2, 2), (2, 3, 2), (3, 2, 2)):
        p = scaled_parameters(4, 3, 3, 12, 12, r=r, Q=Q, R=R)
        layout = build_auxiliary_layout(p)
        assert len(layout.measurement_rows) == p.tail_probability * p.D


def test_binomial_polynomial_interpolates_the_alternating_signs():
    for R, A0 in ((2, 0), (3, 1), (4, 2)):
        coefficients = _binomial_polynomial(R, A0)
        for j in range(A0, A0 + R):
            value = sum(c * Fraction(j) ** k for k, c in enumerate(coefficients))
            assert value == (1 if j % 2 == 0 else -1)


# --------------------------------------------------------------------------
# Schedules (`lem:incidence-labels`).
# --------------------------------------------------------------------------

def test_schedules_are_deterministic_and_well_formed():
    instance = cnf_instance([[1, 2, 3], [2, -3]], 4)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=2, Q=2, R=2)
    first = build_schedules(instance, p)
    second = build_schedules(instance, p)
    assert first.variables == second.variables
    assert first.factors == second.factors
    assert len(first.variables) == instance.n
    assert all(0 <= group < p.r for schedule in first.variables for group in schedule)
    assert all(0 <= group < p.r for schedule in first.factors for group in schedule)


def test_schedule_statistics_are_reported_not_assumed():
    instance = cnf_instance([[1, 2, 3], [2, -3]], 4)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=2, Q=2, R=2)
    schedules = build_schedules(instance, p)
    stats = schedules.statistics(instance.incidence_list())
    assert stats['h'] >= 1
    assert stats['phi'] >= 0
    assert stats['xi'] >= 0
    assert isinstance(stats['h_bound_met'], bool)


# --------------------------------------------------------------------------
# `lem:measurement-separation`.
# --------------------------------------------------------------------------

def _direct_sum(forms, point, J=1):
    """`sum_x prod_f Phi_f((<P_{f,v}(t), x>)_v)` by brute force over `x`."""
    instance = forms.instance
    total = ring_zero(J)
    for bits in product((0, 1), repeat=instance.n):
        product_value = ring_from_constant(1, J)
        for factor, scope in enumerate(instance.scopes):
            values = []
            for variable in scope:
                base = Fraction(0)
                for column, coefficient in forms.row_at(factor, variable, point).items():
                    if bits[column]:
                        base += coefficient
                values.append(ring_from_constant(base, J))
            term = ring_zero(J)
            for exponents, coefficient in instance.factors[factor].terms:
                value = ring_from_constant(coefficient, J)
                for exponent, entry in zip(exponents, values):
                    for _ in range(exponent):
                        value = ring_mul(value, entry)
                term = tuple(a + b for a, b in zip(term, value))
            product_value = ring_mul(product_value, term)
        total = tuple(a + b for a, b in zip(total, product_value))
    return total


@pytest.mark.parametrize('n,clauses,r,Q,R', [
    (3, [[1, 2]], 2, 2, 2),
    (3, [[1, 2, 3]], 2, 2, 2),
    (4, [[1, 2], [-1, 3], [2, -3]], 2, 2, 2),
    (4, [[1, 2], [3, 4]], 3, 2, 2),
])
def test_separation_matches_the_direct_sum(n, clauses, r, Q, R):
    instance = cnf_instance(clauses, n)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=r, Q=Q, R=R)
    schedules = build_schedules(instance, p)
    forms = build_embedded_forms(instance, p, schedules, build_auxiliary_layout(p))
    for point in range(1, p.Q + 1):
        result = separation_sum(forms, point, J=1, max_work=5_000_000)
        assert result.value == _direct_sum(forms, point, J=1)


# --------------------------------------------------------------------------
# `lem:boolean-differences` and `eq:full-taylor-sum`.
# --------------------------------------------------------------------------

def test_boolean_differences_identity_on_random_polynomials():
    """`eq:boolean-differences` checked against direct substitution."""
    random = Random(7717)
    for _ in range(40):
        n = random.randrange(1, 4)
        q = random.randrange(0, n + 1)
        # p_x for each Boolean x, as a polynomial of degree at most q.
        polynomials = []
        for _ in range(2 ** n):
            terms = {}
            for exponents in product(range(q + 1), repeat=n):
                if sum(exponents) <= q and random.randrange(3):
                    terms[exponents] = Fraction(random.randrange(-3, 4))
            polynomials.append(terms)

        def evaluate(terms, point):
            total = Fraction(0)
            for exponents, coefficient in terms.items():
                value = coefficient
                for exponent, bit in zip(exponents, point):
                    if exponent:
                        value *= Fraction(bit) ** exponent
                total += value
            return total

        direct = sum(evaluate(polynomials[x], tuple((x >> i) & 1 for i in range(n)))
                     for x in range(2 ** n))
        recovered = Fraction(0)
        for E, U in enumerate_restriction_pairs(n, q):
            indicator = tuple(1 if index in U else 0 for index in range(n))
            sign = -1 if (len(E) - len(U)) % 2 else 1
            for x in range(2 ** n):
                if all(x >> index & 1 for index in E):
                    recovered += sign * evaluate(polynomials[x], indicator)
        assert direct == recovered


@pytest.mark.parametrize('n,clauses,r,Q,R', [
    (3, [[1, 2]], 2, 2, 2),
    (4, [[1, 2], [-1, 3], [2, -3]], 2, 2, 2),
])
def test_taylor_series_matches_direct_evaluation(n, clauses, r, Q, R):
    """`H(t+z) mod z^J` from `eq:full-taylor-sum` against direct expansion."""
    instance = cnf_instance(clauses, n)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=r, Q=Q, R=R)
    schedules = build_schedules(instance, p)
    forms = build_embedded_forms(instance, p, schedules, build_auxiliary_layout(p))
    J = p.J
    for point in range(1, p.Q + 1):
        series = taylor_series(forms, point, J=J, max_work=20_000_000,
                               max_pairs=200_000).series
        direct = _direct_shifted(forms, point, J)
        assert series == direct


def _direct_shifted(forms, point, J):
    """`H(t+z) mod z^J` by substituting `P_{f,v}(t+z)` and summing over `x`."""
    instance = forms.instance
    total = ring_zero(J)
    for bits in product((0, 1), repeat=instance.n):
        product_value = ring_from_constant(1, J)
        for factor, scope in enumerate(instance.scopes):
            values = []
            for variable in scope:
                value = ring_zero(J)
                for column, coefficients in forms.row(factor, variable).items():
                    if not bits[column]:
                        continue
                    # p(point+z) = sum_k c_k (point+z)^k, truncated at J.
                    for k, coefficient in enumerate(coefficients):
                        if not coefficient:
                            continue
                        for j in range(k + 1):
                            if j >= J:
                                break
                            binomial = 1
                            for i in range(j):
                                binomial = binomial * (k - i) // (i + 1)
                            term = coefficient * binomial * Fraction(point) ** (k - j)
                            value = tuple(
                                value[i] + (term if i == j else 0) for i in range(J))
                values.append(value)
            term = ring_zero(J)
            for exponents, coefficient in instance.factors[factor].terms:
                value = ring_from_constant(coefficient, J)
                for exponent, entry in zip(exponents, values):
                    for _ in range(exponent):
                        value = ring_mul(value, entry)
                term = tuple(a + b for a, b in zip(term, value))
            product_value = ring_mul(product_value, term)
        total = tuple(a + b for a, b in zip(total, product_value))
    return total


# --------------------------------------------------------------------------
# `def:layout`.
# --------------------------------------------------------------------------

@pytest.mark.parametrize('n,clauses,r,Q,R', [
    (3, [[1, 2]], 2, 2, 2),
    (4, [[1, 2], [-1, 3], [2, -3]], 2, 2, 2),
    (4, [[1, 2], [3, 4]], 3, 2, 2),
])
def test_layout_replays_the_design(n, clauses, r, Q, R):
    instance = cnf_instance(clauses, n)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=r, Q=Q, R=R)
    schedules = build_schedules(instance, p)
    forms = build_embedded_forms(instance, p, schedules, build_auxiliary_layout(p))
    report = verify_layout(forms)
    assert report.valid_identity is True
    assert report.factor_assignment is True
    assert report.coefficient_bound is True
    assert report.design_valid is True
    assert report.summary()['runtime_bound_proven'] is False


def test_row_space_test_is_exact():
    assert in_row_space([{0: Fraction(1), 1: Fraction(1)}],
                        {0: Fraction(2), 1: Fraction(2)})
    assert in_row_space([{0: Fraction(1)}, {1: Fraction(1)}],
                        {0: Fraction(1), 1: Fraction(1)})
    assert in_row_space([{0: Fraction(1), 1: Fraction(1)},
                         {1: Fraction(1), 2: Fraction(1)}],
                        {0: Fraction(1), 2: Fraction(-1)})
    assert not in_row_space([{0: Fraction(1)}], {1: Fraction(1)})
    assert not in_row_space([{0: Fraction(1), 1: Fraction(1)}], {1: Fraction(1)})


# --------------------------------------------------------------------------
# End to end: `H(0) = Z`.
# --------------------------------------------------------------------------

CASES = [
    (2, [[1, 2]]),
    (3, [[1, 2]]),
    (2, [[1, 2], [-1, -2]]),
    (3, [[1, 2, 3]]),
    (3, [[1, 2], [2, 3]]),
    (4, [[1, 2], [3, 4]]),
    (4, [[1, 2, 3], [2, 3, 4]]),
    (4, [[1, 2], [-1, 3], [2, -3]]),
    (5, [[1, 2], [2, 3], [3, 4], [4, 5]]),
    (4, [[1], [-1]]),
    (4, [[1, 2], [-1, -2], [1, -2]]),
    (6, [[1, 2], [3, 4], [5, 6]]),
]


@pytest.mark.parametrize('n,clauses', CASES)
@pytest.mark.parametrize('r,Q,R', [(2, 2, 2), (2, 3, 2), (3, 2, 2)])
def test_count_matches_brute_force(n, clauses, r, Q, R):
    instance = cnf_instance(clauses, n)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=r, Q=Q, R=R)
    result = count_instance(instance, p, max_work=50_000_000, max_pairs=5_000_000)
    assert result.value == brute_force(instance)
    assert result.layout['valid_identity'] is True


@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_random_bounded_occurrence_cnfs(seed):
    random = Random(seed)
    for _ in range(6):
        n = random.randrange(2, 6)
        occurrences = [0] * n
        clauses = []
        for _ in range(random.randrange(1, 4)):
            chosen = []
            for _ in range(random.randrange(1, 4)):
                free = [v for v in range(n) if occurrences[v] < 3 and v not in chosen]
                if not free:
                    break
                variable = random.choice(free)
                chosen.append(variable)
                occurrences[variable] += 1
            if chosen:
                clauses.append([(v + 1) if random.randrange(2) else -(v + 1)
                                for v in chosen])
        instance = cnf_instance(clauses, n)
        p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                              instance.d, r=2, Q=2, R=2)
        result = count_instance(instance, p, max_work=50_000_000,
                                max_pairs=5_000_000)
        assert result.value == brute_force(instance)


def test_constant_zero_instance_counts_zero():
    instance = cnf_instance([[]], 2)
    assert instance.constant_zero is True
    p = scaled_parameters(2, 1, 1, 2, 2, r=2, Q=2, R=2)
    result = count_instance(instance, p)
    assert result.value == 0


def test_contradictory_unit_clauses_count_zero():
    instance = cnf_instance([[1], [-1]], 2)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=2, Q=2, R=2)
    assert count_instance(instance, p, max_work=50_000_000).value == 0


def test_empty_and_tautological_clauses_are_normalised():
    instance = cnf_instance([[1, -1], [2]], 3)
    # The tautology is dropped, so variable 0 is unused and gets a dummy factor.
    assert instance.scopes[0] == (1,)
    assert (0,) in instance.scopes
    assert brute_force(instance) == 4


def test_recovery_is_exact_for_a_full_count():
    instance = cnf_instance([[1, 2]], 3)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=2, Q=2, R=2)
    result = count_instance(instance, p, max_work=50_000_000)
    assert result.value == 6
    assert isinstance(result.value, int)


# --------------------------------------------------------------------------
# Fail-closed budgets.
# --------------------------------------------------------------------------

def test_budgets_fail_closed():
    from veritas.research.eth_counting_v39 import SeparationBudgetExceeded
    instance = cnf_instance([[1, 2, 3]], 3)
    p = scaled_parameters(instance.n, instance.b, instance.w, instance.M,
                          instance.d, r=2, Q=2, R=2)
    schedules = build_schedules(instance, p)
    forms = build_embedded_forms(instance, p, schedules, build_auxiliary_layout(p))
    with pytest.raises(SeparationBudgetExceeded):
        separation_sum(forms, 1, J=1, max_work=1)


def test_solver_rejects_an_underdetermined_system():
    from veritas.research.eth_counting_v39 import CountingFailure
    with pytest.raises(CountingFailure):
        solve_exact([[Fraction(1), Fraction(0)]], [Fraction(1)], 3)


def test_solver_rejects_an_inconsistent_system():
    from veritas.research.eth_counting_v39 import CountingFailure
    with pytest.raises(CountingFailure):
        solve_exact([[Fraction(1)], [Fraction(1)]], [Fraction(1), Fraction(2)], 1)


def test_taylor_equations_have_the_shifted_binomial_structure():
    rows = taylor_equations((2,), 3, 4)
    # [z^0] H(2+z) = h0 + 2 h1 + 4 h2 + 8 h3 + 16 h4
    assert rows[0][2] == [Fraction(1), Fraction(2), Fraction(4),
                          Fraction(8), Fraction(16)]
    # [z^1] H(2+z) = h1 + 4 h2 + 12 h3 + 32 h4
    assert rows[1][2] == [Fraction(0), Fraction(1), Fraction(4),
                          Fraction(12), Fraction(32)]


# --------------------------------------------------------------------------
# Regression tests for repaired mathematical edge cases.
# --------------------------------------------------------------------------

@pytest.mark.parametrize('clauses,n,expected', [
    ([], 2, 4),                # no clauses: every assignment satisfies
    ([], 4, 16),
    ([[1, -1]], 1, 2),         # only a tautology, so every variable is unused
    ([[1, -1]], 3, 8),
])
def test_zero_product_degree_is_supported(clauses, n, expected):
    """A clause-free instance has `d = 0`, so `d_H = 0` and `J = 1`.

    `d = 0` is the correct degree of a product of constant factors; the
    earlier code rejected it as "not positive", which broke the empty and
    all-tautology cases even though their counts are trivial.
    """
    instance = cnf_instance(clauses, n)
    assert instance.d == 0
    result = count_cnf(clauses, n, r=2, Q=2, R=2, max_work=20_000_000,
                       max_pairs=1_000_000)
    assert result.value == expected
    assert result.degree_bound == 0
    assert result.truncation == 1


@pytest.mark.parametrize('clauses,expected', [
    ([[1]], 1),
    ([[1], [-1]], 0),
    ([[1, -1]], 2),
])
def test_single_variable_does_not_divide_by_zero(clauses, expected):
    """`n = 1` gives `lambda = ceil(log2 1) = 0`, so `tau = 1/(r*lambda)` is undefined.

    `tau` and `epsilon` are cost parameters only; they never enter the
    counting identity. The scale is clamped instead of dividing by zero.
    """
    result = count_cnf(clauses, 1, r=2, Q=2, R=2, max_work=20_000_000,
                       max_pairs=1_000_000)
    assert result.value == expected
    assert result.parameters['lambda'] == 0


def test_theorem_scale_balance_checks_are_sound():
    """The log-form balance test must never accept a tuple the exact test rejects.

    `lambda = ceil(log2 n)` implies only `n > 2**(lambda-1)`, so a sufficient
    bound has to compare against `lambda - 1`. Comparing against `lambda`
    would accept tuples with `2Qr**2 > n`.
    """
    from veritas.research.eth_counting_v39.parameters import ceil_log2

    random = Random(90210)
    checked = 0
    for _ in range(400):
        lam = random.randrange(2, 40)
        n = random.randrange(1 << (lam - 1), 1 << lam) + 1
        assert ceil_log2(n) == lam
        r = random.randrange(2, 40)
        Q = random.randrange(1, 12)
        # The log-form predicate the theorem-scale report uses.
        if ceil_log2(2 * Q * r * r) <= lam - 1:
            assert 2 * Q * r * r <= n, (n, r, Q)
            checked += 1
    assert checked > 0
