"""R9.6 audit: Hermite recovery and recursive invariants, exact arithmetic.

Every expectation here is computed independently of the production code:

* the interpolation grid is rebuilt from the closed-form node set,
* the recovery functional is re-solved from the confluent system with
  ``fractions.Fraction``,
* the jet convention (coefficients of ``F(t + alpha*z)``, *not* derivatives) is
  exercised by sampling an explicit integer polynomial,
* repeated-root and constant-polynomial behaviour is checked directly.

The historical regression is preserved: ``F = 19`` must recover ``19``, not the
``6`` that a forged recovery weight once produced.
"""
from fractions import Fraction

import pytest

from veritas.research.eth_interpolation.source_hermite import (
    make_source_tapered_plan, reconstruct_source_tapered,
    validate_source_tapered_plan)
from veritas.research.eth_interpolation.tapered_hermite import (
    make_tapered_plan, reconstruct_tapered, sample_integer_polynomial)
from veritas.research.independent_r95.hermite_grid import check_grid


def independent_nodes(a, u, M):
    """Closed-form node set, rebuilt without the production parameter code."""
    L = 1 << a
    h = (3 * M + u - 1) // u
    nodes = {}
    for t in range(-L, L):
        if not t:
            continue
        i = (abs(t) & -abs(t)).bit_length() - 1
        if i >= u:
            continue
        nodes[t] = h * (u - i)
    return L, h, nodes


def independent_guard_bits(a, u, M, p):
    L, h, nodes = independent_nodes(a, u, M)
    worst = 0
    for t, qt in nodes.items():
        i = (abs(t) & -abs(t)).bit_length() - 1
        D = L // 2 ** i
        direct = sum(q * ((abs(s) & -abs(s)).bit_length() - 1 -
                          (abs(t - s) & -abs(t - s)).bit_length() - 1)
                     for s, q in nodes.items() if s != t)
        minimum = direct + (qt - 1) * (i - a - 1)
        worst = min(worst, minimum)
    return max(0, -worst)


@pytest.mark.parametrize("a,u,M", [(1, 1, 1), (2, 1, 2), (2, 2, 2), (3, 2, 2)])
def test_plan_nodes_match_an_independent_closed_form(a, u, M):
    plan = make_source_tapered_plan(M=M, a=a, u=u, p=5,
                                    max_precision_bits=4096, max_terms=256)
    L, h, expected = independent_nodes(a, u, M)
    assert [(node.t, node.multiplicity) for node in plan.nodes] == \
        sorted(expected.items())
    assert plan.alpha == 2 * L


@pytest.mark.parametrize("a,u,M", [(1, 1, 1), (2, 2, 2), (3, 2, 2), (4, 3, 5)])
def test_grid_precision_requirement_is_sufficient(a, u, M):
    report = check_grid(a=a, u=u, M=M, p=5)
    assert report["points_checked"] > 0
    L, h, _ = independent_nodes(a, u, M)
    for row in report["rows"]:
        assert row["guard_margin"] >= 0
        # The declared node precision must equal the guard formula exactly,
        # recomputed here from the closed form rather than from the report.
        t = row["t"]
        index = (abs(t) & -abs(t)).bit_length() - 1
        expected = 5 + 8 * h * (L >> index) + 8 * M * (a + 1)
        assert row["precision"] == expected


@pytest.mark.parametrize("a,u,M", [(3, 3, 3), (3, 1, 3)])
def test_degree_cap_refusal_is_explicit(a, u, M):
    """Above the finite degree cap the plan must refuse, not truncate."""
    with pytest.raises(ValueError, match="degree cap"):
        make_source_tapered_plan(M=M, a=a, u=u, p=5,
                                 max_precision_bits=4096, max_terms=256)


def test_recovery_functional_recovers_f_zero_exactly():
    """sum_{t,j} w[t][j] * [z^j] F(t + alpha z) must equal F(0)."""
    plan = make_source_tapered_plan(M=1, a=1, u=1, p=5,
                                    max_precision_bits=4096, max_terms=256)
    by_node = dict(plan.weights)
    alpha = plan.alpha
    for power in range(0, plan.degree_bound + 1):
        total = Fraction(0)
        for node in plan.nodes:
            for j, weight in enumerate(by_node[node.t]):
                if j > power:
                    break
                coefficient = Fraction(_binomial(power, j)
                                       * (node.t ** (power - j))
                                       * (alpha ** j))
                total += weight * coefficient
        assert total == (1 if power == 0 else 0), power


def _binomial(n, k):
    if k < 0 or k > n:
        return 0
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def test_constant_polynomial_recovers_19_not_6():
    """The historical regression: F = 19 must recover 19."""
    plan = make_tapered_plan(M=1, a=1, u=1, p=5)
    jets = sample_integer_polynomial(plan, (19,))
    assert reconstruct_tapered(plan, jets) == 19


def test_source_plan_recovers_the_constant_polynomial():
    plan = make_source_tapered_plan(M=1, a=1, u=1, p=5,
                                    max_precision_bits=4096, max_terms=256)
    jets = sample_integer_polynomial(plan, (19,))
    assert reconstruct_source_tapered(plan, jets) == 19


@pytest.mark.parametrize("coefficients", [
    (19,), (19, -23, 7, 9), (0, 0, 5), (-1, 0, 0, 3)])
def test_tapered_reconstruction_matches_direct_evaluation(coefficients):
    plan = make_tapered_plan(M=1, a=1, u=1, p=8)
    jets = sample_integer_polynomial(plan, coefficients)
    # The reference returns the canonical residue at the target precision.
    assert reconstruct_tapered(plan, jets) == coefficients[0] % (1 << 8)


def test_repeated_root_polynomial_is_recovered_exactly():
    """F(z) = (z-1)^3 has a triple root; recovery must still be exact."""
    coefficients = (-1, 3, -3, 1)  # (z-1)^3 = z^3 - 3z^2 + 3z - 1
    plan = make_tapered_plan(M=1, a=1, u=1, p=12)
    jets = sample_integer_polynomial(plan, coefficients)
    assert reconstruct_tapered(plan, jets) == coefficients[0] % (1 << 12)


def test_forged_recovery_weight_is_rejected_not_silently_used():
    from dataclasses import replace
    plan = make_tapered_plan(M=1, a=1, u=1, p=5)
    jets = sample_integer_polynomial(plan, (19,))
    weights = list(plan.recovery_plan.weights)
    weights[0] += Fraction(1)
    forged = replace(plan, recovery_plan=replace(plan.recovery_plan,
                                                 weights=tuple(weights)))
    with pytest.raises(ValueError):
        reconstruct_tapered(forged, jets)


def test_insufficient_precision_is_refused_not_rounded():
    from dataclasses import replace
    plan = make_tapered_plan(M=1, a=1, u=1, p=5)
    jets = sample_integer_polynomial(plan, (19, -23, 7, 9))
    first = plan.nodes[0]
    shrunk = replace(plan, nodes=(
        replace(first, precision_bits=max(1, first.precision_bits - 4)),) +
        plan.nodes[1:])
    with pytest.raises(ValueError):
        reconstruct_tapered(shrunk, jets)


def test_source_plan_validation_rejects_forged_parameters():
    plan = make_source_tapered_plan(M=1, a=1, u=1, p=5,
                                    max_precision_bits=4096, max_terms=256)
    validate_source_tapered_plan(plan, max_precision_bits=4096, max_terms=256)
    from dataclasses import replace
    with pytest.raises(ValueError):
        validate_source_tapered_plan(replace(plan, alpha=plan.alpha + 1),
                                     max_precision_bits=4096, max_terms=256)
