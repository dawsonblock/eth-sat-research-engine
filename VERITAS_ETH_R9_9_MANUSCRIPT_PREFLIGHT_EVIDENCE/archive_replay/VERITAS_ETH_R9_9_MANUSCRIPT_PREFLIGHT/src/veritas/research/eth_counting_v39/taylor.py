"""Taylor data from fixed Boolean substitutions (`subsec:fixed-boolean-substitutions`).

Paper objects (vendored in `paper/`):

* `eq:jet-substitution`, `eq:auxiliary-polynomial`, `eq:degree-cost`
  (`main_full_version.tex` l. 1886-1925) -- `Delta P_{f,v}`, `G_x(X,z)`, and
  `deg_X([z^j]G_x) <= j`.
* `lem:boolean-differences` and `eq:boolean-differences` (l. 1933-1960) --
  the inclusion-exclusion identity that recovers `X = x` from fixed
  substitutions `X = 1_U` and restrictions `x_i = 1` on `i in E`.
* `eq:full-taylor-sum` (l. 1985) -- the resulting expression for `H(t+z)`.
* `eq:hasse-order` (l. 1858) -- `q` and `J`.

The algorithm never builds a polynomial in the `n` indeterminates: it sets
`X = 1_U` first and keeps only the `J` coefficients of `z`.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .separation import (SeparationBudgetExceeded, ring_add, ring_from_polynomial,
                         ring_mul, ring_scale, ring_zero, separation_sum)


def enumerate_restriction_pairs(n, q):
    """Every `(E, U)` with `|E| <= q` and `U` a subset of `E`."""
    limit = min(q, n)
    pairs = []
    for mask in range(1 << n):
        size = bin(mask).count('1')
        if size > limit:
            continue
        E = tuple(index for index in range(n) if mask >> index & 1)
        subset = mask
        while True:
            U = tuple(index for index in range(n) if subset >> index & 1)
            pairs.append((E, U))
            if subset == 0:
                break
            subset = (subset - 1) & mask
    return pairs


@dataclass(frozen=True)
class TaylorResult:
    series: tuple
    pairs: int
    measurement_tuples: int
    assignments_examined: int


def taylor_series(forms, point, *, J=None, max_work=2_000_000,
                  max_pairs=200_000) -> TaylorResult:
    """`H(t+z) mod z**J` from `eq:full-taylor-sum`."""
    parameters = forms.parameters
    instance = forms.instance
    if J is None:
        J = parameters.J
    if type(J) is not int or J < 1:
        raise ValueError('positive truncation order required')
    q = J - 1
    pairs = enumerate_restriction_pairs(instance.n, q)
    if len(pairs) > max_pairs:
        raise SeparationBudgetExceeded(
            f'{len(pairs)} restriction pairs exceed the finite budget')
    # Delta P_{f,v}(z) pushed onto the original variables, once per point.
    shifts = {(factor, variable): forms.shift(factor, variable, point)
              for factor in range(len(instance.scopes))
              for variable in instance.scopes[factor]}
    total = ring_zero(J)
    tuples = examined = 0
    for E, U in pairs:
        selected = set(U)

        def correction(factor, variable, _selected=selected):
            coefficients = [Fraction(0)] * J
            for column, values in shifts[(factor, variable)].items():
                if column not in _selected:
                    continue
                for degree, value in enumerate(values):
                    if degree < J:
                        coefficients[degree] += value
            return ring_from_polynomial(coefficients, J)

        result = separation_sum(forms, point, E=E, J=J, max_work=max_work,
                                correction=correction)
        tuples += result.measurement_tuples
        examined += result.assignments_examined
        sign = -1 if (len(E) - len(U)) % 2 else 1
        total = ring_add(total, ring_scale(result.value, Fraction(sign)))
    return TaylorResult(series=total, pairs=len(pairs),
                        measurement_tuples=tuples, assignments_examined=examined)
