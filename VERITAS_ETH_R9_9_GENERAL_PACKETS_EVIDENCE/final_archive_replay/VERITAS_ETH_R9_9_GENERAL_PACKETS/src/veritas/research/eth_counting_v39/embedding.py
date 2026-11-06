"""Placement of incidences into copies, and the actual rows and measurements.

Paper objects (vendored in `paper/`):

* `subsec:embedding` (l. 2532-2622) -- `h` copies of `B`, the copy assignment
  `c(f,v)`, the transferred rows `eq:overview-transferred-row`, and the split
  of each measurement into its per-group restrictions.
* `def:layout` (l. 1714-1760) -- the resulting rows `P_{f,v}`, partitions
  `S_{t,g}`, factor assignments `sigma_f`, and matrices `C_{t,g}`.

A copy of `B` is an array of `D` positions; position `w` either holds one
original variable or is unused. Rows and measurements on the copy are pushed
forward to the original variables by summing the coefficients of every
position that holds the same variable, which is the paper's "substituting
variables, combining repeated copies, and restricting to a group".
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class EmbeddedForms:
    """The `def:layout` data for one instance and parameter set."""

    instance: object
    parameters: object
    schedules: object
    auxiliary: object
    incidence_label: tuple      # indexed like instance.incidence_list()
    incidence_copy: tuple
    copy_content: tuple         # (h, D) of variable index or None
    rows: tuple                 # (f, v) -> {variable: coefficient tuple in T}
    group_rows: tuple           # (t-1, g) -> tuple of {variable: int}
    copies: int

    def row(self, factor, variable):
        return self.rows[(factor, variable)]

    def row_at(self, factor, variable, point):
        """`P_{f,v}(point)` as a sparse `{variable: Fraction}`."""
        result = {}
        for column, coefficients in self.row(factor, variable).items():
            value = Fraction(0)
            power = Fraction(1)
            for coefficient in coefficients:
                value += coefficient * power
                power *= point
            if value:
                result[column] = value
        return result

    def shift(self, factor, variable, point):
        """`Delta P_{f,v}(z) = P_{f,v}(point+z) - P_{f,v}(point)` coefficients.

        Returns `{variable: coefficient tuple}`, always with zero constant
        term, because every entry of `Delta P` is divisible by `z`.
        """
        result = {}
        for column, coefficients in self.row(factor, variable).items():
            shifted = _shift_minus_value(coefficients, point)
            if any(shifted):
                result[column] = shifted
        return result

    def measurement_rows(self, point, group):
        """`C_{t,g}` rows, one-based `point`."""
        return self.group_rows[point - 1][group]

    def group_members(self, point, group):
        """`S_{t,g}`, one-based `point`."""
        return tuple(v for v in range(self.instance.n)
                     if self.schedules.variable_group(v, point) == group)

    def factor_group(self, factor, point):
        return self.schedules.factor_group(factor, point)


def _shift_minus_value(coefficients, point):
    """Coefficients of `p(point+z) - p(point)` as a tuple."""
    degree = len(coefficients)
    shifted = [Fraction(0)] * degree
    # p(point+z) = sum_k c_k (point+z)^k; expand each (point+z)^k.
    for k, coefficient in enumerate(coefficients):
        if not coefficient:
            continue
        for j in range(k + 1):
            shifted[j] += coefficient * _binomial(k, j) * Fraction(point) ** (k - j)
    shifted[0] -= sum(coefficient * Fraction(point) ** k
                      for k, coefficient in enumerate(coefficients))
    while shifted and shifted[-1] == 0:
        shifted.pop()
    return tuple(shifted)


def _binomial(n, k):
    value = 1
    for i in range(k):
        value = value * (n - i) // (i + 1)
    return value


def build_embedded_forms(instance, parameters, schedules, auxiliary):
    """Place every incidence in a copy and push rows/measurements to variables."""
    incidences = instance.incidence_list()
    labels = []
    for factor, variable in incidences:
        labels.append(auxiliary.encode(schedules.label(factor, variable)))
    # Group incidences by label and hand out copies so that (copy, label) is unique.
    by_label = {}
    for index, label in enumerate(labels):
        by_label.setdefault(label, []).append(index)
    copies = max((len(group) for group in by_label.values()), default=1)
    copy_of = [0] * len(incidences)
    content = [[None] * auxiliary.D for _ in range(copies)]
    for label, members in by_label.items():
        for copy_index, incidence_index in enumerate(members):
            copy_of[incidence_index] = copy_index
            factor, variable = incidences[incidence_index]
            content[copy_index][label] = variable
    content = tuple(tuple(row) for row in content)

    rows = {}
    for incidence_index, (factor, variable) in enumerate(incidences):
        label = labels[incidence_index]
        copy_index = copy_of[incidence_index]
        polynomial = auxiliary.row_polynomial(label)
        accumulator = {}
        for position, coefficients in polynomial.items():
            target = content[copy_index][position]
            if target is None:
                continue
            current = accumulator.get(target, ())
            length = max(len(current), len(coefficients))
            merged = [Fraction(0)] * length
            for degree, value in enumerate(current):
                merged[degree] += value
            for degree, value in enumerate(coefficients):
                merged[degree] += value
            accumulator[target] = tuple(merged)
        rows[(factor, variable)] = {column: value for column, value in
                                    accumulator.items() if any(value)}

    group_rows = []
    measurement_rows = auxiliary.measurement_rows
    for point in range(parameters.Q):
        per_group = []
        for group in range(parameters.r):
            matrix = []
            for copy_index in range(copies):
                for measurement in measurement_rows:
                    row = {}
                    for position, coefficient in measurement.items():
                        target = content[copy_index][position]
                        if target is None:
                            continue
                        if auxiliary.group_of(position, point) != group:
                            continue
                        row[target] = row.get(target, 0) + coefficient
                    row = {variable: value for variable, value in row.items() if value}
                    if row:
                        matrix.append(row)
            per_group.append(tuple(matrix))
        group_rows.append(tuple(per_group))

    return EmbeddedForms(instance=instance, parameters=parameters,
                         schedules=schedules, auxiliary=auxiliary,
                         incidence_label=tuple(labels),
                         incidence_copy=tuple(copy_of),
                         copy_content=content, rows=rows,
                         group_rows=tuple(group_rows), copies=copies)
