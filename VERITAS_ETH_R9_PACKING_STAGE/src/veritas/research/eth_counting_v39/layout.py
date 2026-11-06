"""Verification of Definition `def:layout`.

Paper objects (vendored in `paper/`):

* `def:layout` (`main_full_version.tex` l. 1714-1760) -- the five required
  properties: small groups, a factor assignment, few bounded measurements,
  the kernel condition, and the coefficient bound.
* `lem:measurement-separation` (l. 1781-1872) -- the invariance hypothesis
  that item 4 supplies.

Items 1-3 and 5 are *cost* hypotheses: they are what makes the running-time
estimate work. Item 4 is the only one the counting identity needs. This module
therefore reports all five, and distinguishes "the identity is valid" from
"the paper's cost hypotheses happen to hold at this finite size".
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import factorial, log2


def _echelon(rows):
    """Exact row-echelon basis of sparse `Fraction` rows."""
    basis = {}
    for row in rows:
        vector = {column: Fraction(value) for column, value in row.items() if value}
        while vector:
            pivot = min(vector)
            if pivot in basis:
                factor = vector[pivot]
                for column, value in basis[pivot].items():
                    vector[column] = vector.get(column, Fraction(0)) - factor * value
                vector = {column: value for column, value in vector.items() if value}
            else:
                scale = vector[pivot]
                basis[pivot] = {column: value / scale for column, value in vector.items()}
                break
    return basis


def in_row_space(rows, target):
    """True when `target` lies in the span of `rows` (exact arithmetic)."""
    basis = _echelon(rows)
    vector = {column: Fraction(value) for column, value in target.items() if value}
    while vector:
        pivot = min(vector)
        if pivot not in basis:
            return False
        factor = vector[pivot]
        for column, value in basis[pivot].items():
            vector[column] = vector.get(column, Fraction(0)) - factor * value
        vector = {column: value for column, value in vector.items() if value}
    return True


@dataclass(frozen=True)
class LayoutReport:
    """The five `def:layout` items, plus what they do and do not imply."""

    valid_identity: bool          # item 4 holds everywhere
    small_groups: bool            # item 1 size bound
    factor_assignment: bool       # item 2
    bounded_measurements: bool    # item 3
    coefficient_bound: bool       # item 5
    details: dict

    @property
    def design_valid(self):
        return self.valid_identity and self.factor_assignment

    @property
    def cost_hypotheses_hold(self):
        return self.small_groups and self.bounded_measurements

    def summary(self):
        return {
            'valid_identity': self.valid_identity,
            'small_groups': self.small_groups,
            'factor_assignment': self.factor_assignment,
            'bounded_measurements': self.bounded_measurements,
            'coefficient_bound': self.coefficient_bound,
            'design_valid': self.design_valid,
            'cost_hypotheses_hold': self.cost_hypotheses_hold,
            'runtime_bound_proven': False,
            **self.details,
        }


def verify_layout(forms, *, max_kernel_checks: int = 200_000) -> LayoutReport:
    """Replay every `def:layout` requirement on constructed data."""
    instance = forms.instance
    parameters = forms.parameters
    n, r, Q, R, D = (instance.n, parameters.r, parameters.Q,
                     parameters.R, parameters.D)

    # Item 2: one group assignment per factor at every point.
    factor_assignment = all(
        0 <= forms.factor_group(factor, point) < r
        for factor in range(len(instance.scopes))
        for point in range(1, Q + 1))

    # Item 1: partitions with |S_{t,g}| <= 2n/r.
    worst_group, partitions = 0, True
    for point in range(1, Q + 1):
        members = [forms.group_members(point, group) for group in range(r)]
        joined = sorted(v for block in members for v in block)
        partitions = partitions and joined == list(range(n))
        worst_group = max(worst_group, max((len(block) for block in members),
                                           default=0))
    small_groups = partitions and worst_group * r <= 2 * n

    # Item 3: integer rows, absolute row sums at most D, and the total bound.
    total_rows, worst_row = 0, 0
    integer_rows = True
    for point in range(1, Q + 1):
        for group in range(r):
            for row in forms.measurement_rows(point, group):
                total_rows += 1
                integer_rows = integer_rows and all(
                    type(value) is int for value in row.values())
                worst_row = max(worst_row, sum(abs(value) for value in row.values()))
    bounded_measurements = (integer_rows and worst_row <= D and
                            total_rows <= 2 * parameters.tau * n)

    # Item 4: the kernel condition, checked per factor, variable, point, group.
    identity_ok = True
    kernel_checks = 0
    for point in range(1, Q + 1):
        assigned = [forms.factor_group(factor, point)
                    for factor in range(len(instance.scopes))]
        for factor, scope in enumerate(instance.scopes):
            if not scope:
                continue
            group = assigned[factor]
            for variable in scope:
                full = forms.row_at(factor, variable, point)
                for other in range(r):
                    if other == group:
                        continue
                    members = set(forms.group_members(point, other))
                    restricted = {column: value for column, value in full.items()
                                  if column in members}
                    if not restricted:
                        continue
                    kernel_checks += 1
                    if kernel_checks > max_kernel_checks:
                        raise ValueError('layout kernel check budget exceeded')
                    if not in_row_space(forms.measurement_rows(point, other),
                                        restricted):
                        identity_ok = False

    # Rows must restore the variables at zero and respect the degree bound.
    zero_ok, degree_ok = True, True
    for (factor, variable), polynomial in forms.rows.items():
        at_zero = forms.row_at(factor, variable, 0)
        zero_ok = zero_ok and at_zero == {variable: Fraction(1)}
        degree_ok = degree_ok and all(len(coefficients) <= R
                                      for coefficients in polynomial.values())

    # Item 5: a common denominator making every coefficient integral.
    denominator = factorial(R - 1) * factorial(Q)
    integral = True
    max_bits = 0
    for polynomial in forms.rows.values():
        for coefficients in polynomial.values():
            for coefficient in coefficients:
                scaled = coefficient * denominator
                integral = integral and scaled.denominator == 1
                max_bits = max(max_bits, abs(scaled.numerator).bit_length())
    bit_bound = 4 * (Q * max(1, int(log2(Q + 1))) + max(1, D.bit_length())) + 16
    coefficient_bound = (integral and zero_ok and degree_ok and max_bits <= bit_bound)

    return LayoutReport(
        valid_identity=identity_ok,
        small_groups=small_groups,
        factor_assignment=factor_assignment,
        bounded_measurements=bounded_measurements,
        coefficient_bound=coefficient_bound,
        details={
            'n': n, 'r': r, 'Q': Q, 'R': R, 'D': D,
            'copies': forms.copies,
            'measurement_rows_total': total_rows,
            'measurement_row_absolute_sum_max': worst_row,
            'group_size_max': worst_group,
            'group_size_bound': (2 * n) // r if r else 0,
            'common_denominator': str(denominator),
            'coefficient_max_bits': max_bits,
            'coefficient_bit_bound': bit_bound,
            'kernel_checks': kernel_checks,
            'rows_restore_variables_at_zero': zero_ok,
            'rows_meet_degree_bound': degree_ok,
        })
