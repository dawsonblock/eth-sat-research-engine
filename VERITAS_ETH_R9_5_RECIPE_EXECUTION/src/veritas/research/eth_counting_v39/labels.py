"""Deterministic variable and factor schedules (`lem:incidence-labels`).

Paper objects (vendored in `paper/`):

* `subsec:choosing-labels` (l. 2423-2530) -- the schedules
  `a_v, d_f in [r]^Q`, the statistics `Phi` and `Xi`, and the claim that
  fixing them one at a time does not increase the conditional expectation of
  `Phi/(M(b+w)) + Xi/(Qn)`.
* `eq:incidence-balance-hypotheses` (l. 2447) -- when the derived bounds
  `h <= 2M/D` and `|S_{t,g}| <= 2n/r` hold.

The paper's construction computes conditional expectations by enumerating at
most `D^2` assignments per indicator. This implementation evaluates the same
expectations in closed form instead: every indicator depends on at most two
schedule vectors, each uniform on `[r]^Q`, so the conditional probability is a
power of `1/r^Q` times a fixed-value test. The result is the same exact
rational number, at `O(M^2 + Q n^2)` per candidate instead of `O(D^2)`.

The schedules this returns are *not* guaranteed to meet the paper's balance
bounds at finite size; `schedule_statistics` reports the actual values. The
counting algorithm's correctness does not depend on those bounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from .parameters import FormParameters


class ScheduleBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class Schedules:
    """The schedules plus the statistics the paper bounds."""

    r: int
    Q: int
    D: int
    variables: tuple          # a_v, one tuple of Q group indices per variable
    factors: tuple            # d_f, one tuple per factor
    empty_scope_factors: tuple
    n: int
    M: int
    b: int
    w: int

    def variable_group(self, variable, point):
        """`a_v(point)` for a one-based `point`."""
        return self.variables[variable][point - 1]

    def factor_group(self, factor, point):
        """`d_f(point)` for a one-based `point`."""
        return self.factors[factor][point - 1]

    def label(self, factor, variable):
        """`u_{f,v} = (a_v, d_f)` as a sequence of `Q` pairs `(a_v(s), d_f(s))`.

        This is the `B`-index form: `B = ([r]^Q)^2` is written as `Q` copies
        of `[r]^2`, one per evaluation point.
        """
        a, d = self.variables[variable], self.factors[factor]
        return tuple((a[s], d[s]) for s in range(self.Q))

    def group_members(self, point, group):
        """`S_{t,g} = {v : a_v(t) = g}`."""
        return tuple(v for v in range(self.n)
                     if self.variables[v][point - 1] == group)

    def label_multiplicities(self, incidences):
        counts = {}
        for factor, variable in incidences:
            key = self.label(factor, variable)
            counts[key] = counts.get(key, 0) + 1
        return counts

    def statistics(self, incidences):
        """Actual `h`, worst group size, `Phi` and `Xi`."""
        counts = self.label_multiplicities(incidences)
        h = max(counts.values(), default=0)
        worst_group = 0
        for point in range(1, self.Q + 1):
            for group in range(self.r):
                worst_group = max(worst_group, len(self.group_members(point, group)))
        phi = sum((count - Fraction(self.M, self.D)) ** 2 for count in counts.values())
        xi = Fraction(0)
        for point in range(1, self.Q + 1):
            for group in range(self.r):
                xi += (len(self.group_members(point, group)) - Fraction(self.n, self.r)) ** 2
        return {'h': h, 'max_group': worst_group,
                'phi': phi, 'xi': xi,
                'h_bound_met': h * self.D <= 2 * self.M,
                'group_bound_met': worst_group * self.r <= 2 * self.n}


def _probability_equal(left, right, fixed, K, r, Q, point=None):
    """`Pr[component left == component right | fixed]` as a Fraction.

    `left` and `right` are schedule components: `('a', v)` or `('d', f)`.
    `point` selects one coordinate when the comparison is per point; with
    `point=None` the whole length-`Q` vector is compared.
    """
    if left == right:
        return Fraction(1)
    if point is None:
        # Compare whole vectors: probability (1/K) per free component.
        free = 0
        for component in (left, right):
            if component in fixed:
                continue
            free += 1
        if left in fixed and right in fixed:
            return Fraction(1) if fixed[left] == fixed[right] else Fraction(0)
        return Fraction(1, K ** free)
    # Compare a single coordinate.
    if left in fixed and right in fixed:
        return Fraction(1) if fixed[left][point] == fixed[right][point] else Fraction(0)
    if left in fixed or right in fixed:
        return Fraction(1, r)
    return Fraction(1, r)


def _phi_expectation(incidences, fixed, K, M, D):
    total = Fraction(0)
    for factor, variable in incidences:
        left = (('a', variable), ('d', factor))
        for other_factor, other_variable in incidences:
            right = (('a', other_variable), ('d', other_factor))
            probability = (_probability_equal(left[0], right[0], fixed, K, 1, 1) *
                           _probability_equal(left[1], right[1], fixed, K, 1, 1))
            total += probability
    return total - Fraction(M * M, D)


def _xi_expectation(n, Q, r, fixed):
    total = Fraction(0)
    for point in range(Q):
        for variable in range(n):
            left = ('a', variable)
            for other in range(n):
                right = ('a', other)
                total += _probability_equal(left, right, fixed, 1, r, Q, point)
    return total - Fraction(Q * n * n, r)


def _objective(incidences, fixed, K, M, D, n, Q, r, b, w):
    phi = _phi_expectation(incidences, fixed, K, M, D)
    xi = _xi_expectation(n, Q, r, fixed)
    return phi / (M * (b + w)) + xi / (Q * n)


def choose_schedules(n: int, factors, *, r: int, Q: int, D: int, M: int,
                     b: int, w: int, max_work: int = 2_000_000,
                     empty_scope_factors=()) -> Schedules:
    """Greedily fix `a_v` then `d_f`, minimising the paper's objective.

    `factors` is a sequence of variable tuples (the factor scopes). Factors
    with empty scope get the constant schedule `d_f = (1, ..., 1)`.
    """
    if type(max_work) is not int or max_work < 1:
        raise ValueError('positive work budget required')
    if r ** Q > max_work:
        raise ScheduleBudgetExceeded('r**Q exceeds the schedule work budget')
    K = r ** Q
    incidences = tuple((f, v) for f, scope in enumerate(factors) for v in scope)
    fixed = {}
    work = 0
    candidates = tuple(product(range(r), repeat=Q))
    order = [('a', v) for v in range(n)]
    order += [('d', f) for f, scope in enumerate(factors) if scope]
    for component in order:
        best = None
        for candidate in candidates:
            work += 1
            if work > max_work:
                raise ScheduleBudgetExceeded('schedule search exceeded its work budget')
            fixed[component] = candidate
            value = _objective(incidences, fixed, K, M, D, n, Q, r, b, w)
            if best is None or value < best[0]:
                best = (value, candidate)
        fixed[component] = best[1]
    variables = tuple(fixed[('a', v)] for v in range(n))
    factors_schedule = tuple(
        (1,) * Q if not scope else fixed[('d', f)]
        for f, scope in enumerate(factors))
    return Schedules(r=r, Q=Q, D=D, variables=variables,
                     factors=factors_schedule,
                     empty_scope_factors=tuple(empty_scope_factors),
                     n=n, M=M, b=b, w=w)


def build_schedules(instance, parameters: FormParameters, *,
                    max_work: int = 2_000_000) -> Schedules:
    """Choose schedules for a factor instance under one parameter set."""
    return choose_schedules(instance.n, instance.scopes, r=parameters.r,
                            Q=parameters.Q, D=parameters.D,
                            M=instance.M, b=instance.b, w=instance.w,
                            max_work=max_work,
                            empty_scope_factors=instance.empty_scopes)
