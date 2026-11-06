"""The group-sum algorithm of `lem:measurement-separation`.

Paper objects (vendored in `paper/`):

* `lem:measurement-separation` (`main_full_version.tex` l. 1781-1872) --
  the identity `Z_E = sum_{y in Y} prod_g Sigma_g(y)` with
  `Sigma_g(y) = sum_{u in X_{g,E}(y_g)} A_g(u + sum_{h!=g} xbar_h)`.
* `eq:group-sum` (l. 1830) and `eq:group-polynomial` (l. 1965) -- the group
  contribution and its Taylor-corrected form `A_{g,U}(x;z)`.

Values live in `Q[z]/(z**J)`; the paper allows any commutative `Q`-algebra,
and a truncated polynomial ring is one. The lemma is used at `E = empty` for
`H(t)` and at general `E` for the restricted Taylor sums.

Every measurement tuple that no Boolean assignment realises contributes zero,
so this implementation iterates over the tuples that actually occur instead of
the full box `{-D,...,D}^c`. That is an optimisation, not a change of identity:
a missing tuple has an empty `X_g(y_g)` and contributes zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


def ring_zero(J):
    return (Fraction(0),) * J


def ring_one(J):
    return (Fraction(1),) + (Fraction(0),) * (J - 1)


def ring_add(left, right):
    return tuple(a + b for a, b in zip(left, right))


def ring_sub(left, right):
    return tuple(a - b for a, b in zip(left, right))


def ring_mul(left, right):
    size = len(left)
    result = [Fraction(0)] * size
    for i, a in enumerate(left):
        if not a:
            continue
        for j, b in enumerate(right):
            if i + j >= size:
                break
            if b:
                result[i + j] += a * b
    return tuple(result)


def ring_from_constant(value, J):
    return (Fraction(value),) + (Fraction(0),) * (J - 1)


def ring_from_polynomial(coefficients, J):
    result = list(coefficients[:J])
    result += [Fraction(0)] * (J - len(result))
    return tuple(result)


def ring_scale(value, scalar):
    return tuple(coefficient * scalar for coefficient in value)


def ring_pow(value, exponent):
    result = ring_one(len(value))
    base = value
    while exponent:
        if exponent & 1:
            result = ring_mul(result, base)
        base = ring_mul(base, base)
        exponent >>= 1
    return result


def evaluate_factor(factor, values):
    """Evaluate a `PolynomialFactor` at ring elements."""
    size = len(values[0])
    total = ring_zero(size)
    for exponents, coefficient in factor.terms:
        term = ring_from_constant(coefficient, size)
        for exponent, value in zip(exponents, values):
            if exponent:
                term = ring_mul(term, ring_pow(value, exponent))
        total = ring_add(total, term)
    return total


class SeparationBudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class SeparationResult:
    value: tuple
    measurement_tuples: int
    assignments_examined: int
    factors_evaluated: int


def separation_sum(forms, point, *, E=(), J=1, max_work=1_000_000,
                   correction=None) -> SeparationResult:
    """Compute `Z_E` in `Q[z]/(z**J)`.

    `correction(factor, variable)` returns the ring element added to
    `⟨P_{f,v}(t), x⟩`; the default is zero, which is the `H(t)` case. The
    Taylor case passes `⟨Delta P_{f,v}(z), 1_U⟩`, which is independent of
    `x` and of the group, exactly as the paper requires.
    """
    instance = forms.instance
    parameters = forms.parameters
    r, n = parameters.r, instance.n
    if correction is None:
        def correction(factor, variable):
            return ring_zero(J)
    assigned = {factor: forms.factor_group(factor, point)
                for factor in range(len(instance.scopes))}
    rows_at = {(factor, variable): forms.row_at(factor, variable, point)
               for factor in range(len(instance.scopes))
               for variable in instance.scopes[factor]}

    # Per group: the members, every assignment, its measurement vector, the
    # bucket of assignments realising that vector, and the linear-value tables.
    members = [forms.group_members(point, group) for group in range(r)]
    position = [{variable: index for index, variable in enumerate(block)}
                for block in members]
    measurements = []
    buckets = []
    local = []
    representative_value = []
    for group in range(r):
        block = members[group]
        rows = forms.measurement_rows(point, group)
        vectors = []
        bucket = {}
        for mask in range(1 << len(block)):
            vector = tuple(sum(coefficient for variable, coefficient in row.items()
                               if mask >> position[group][variable] & 1)
                           for row in rows)
            vectors.append(vector)
            bucket.setdefault(vector, []).append(mask)
        measurements.append(tuple(vectors))
        buckets.append({key: tuple(value) for key, value in bucket.items()})
        table = {}
        for factor in range(len(instance.scopes)):
            if assigned[factor] != group:
                continue
            for variable in instance.scopes[factor]:
                row = rows_at[(factor, variable)]
                table[(factor, variable)] = tuple(
                    sum(coefficient for other, coefficient in row.items()
                        if other in position[group]
                        and mask >> position[group][other] & 1)
                    for mask in range(1 << len(block)))
        local.append(table)
        # The same rows, viewed as functions of another group's representative.
        rep_table = {}
        for factor in range(len(instance.scopes)):
            for variable in instance.scopes[factor]:
                row = rows_at[(factor, variable)]
                rep_table[(factor, variable)] = tuple(
                    sum(coefficient for other, coefficient in row.items()
                        if other in position[group]
                        and mask >> position[group][other] & 1)
                    for mask in range(1 << len(block)))
        representative_value.append(rep_table)

    keys = [sorted(bucket) for bucket in buckets]
    total = ring_zero(J)
    tuples_seen = assignments_examined = factors_evaluated = 0
    work = 0
    state = [0] * r
    while True:
        work += 1
        if work > max_work:
            raise SeparationBudgetExceeded('separation exceeded its work budget')
        tuples_seen += 1
        representatives = [buckets[group][keys[group][state[group]]][0]
                           for group in range(r)]
        # Total of every row over all representative bits, minus the group's own.
        totals = {}
        for group in range(r):
            for key, values in representative_value[group].items():
                current = totals.get(key)
                totals[key] = (values[representatives[group]] if current is None
                               else current + values[representatives[group]])
        product = ring_one(J)
        for group in range(r):
            allowed = buckets[group][keys[group][state[group]]]
            if E:
                allowed = tuple(mask for mask in allowed
                                if all(mask >> position[group][v] & 1
                                       for v in E if v in position[group]))
            if not allowed:
                product = ring_zero(J)
                break
            block = ring_zero(J)
            for mask in allowed:
                work += 1
                assignments_examined += 1
                if work > max_work:
                    raise SeparationBudgetExceeded('separation exceeded its work budget')
                group_product = ring_one(J)
                for factor in range(len(instance.scopes)):
                    if assigned[factor] != group:
                        continue
                    values = []
                    for variable in instance.scopes[factor]:
                        key = (factor, variable)
                        base = local[group][key][mask]
                        other = totals.get(key, Fraction(0))
                        other -= representative_value[group][key][representatives[group]]
                        value = ring_from_constant(base + other, J)
                        values.append(ring_add(value, correction(factor, variable)))
                    group_product = ring_mul(group_product,
                                             evaluate_factor(instance.factors[factor],
                                                             values))
                    factors_evaluated += 1
                block = ring_add(block, group_product)
            product = ring_mul(product, block)
        total = ring_add(total, product)
        cursor = r - 1
        while cursor >= 0:
            state[cursor] += 1
            if state[cursor] < len(keys[cursor]):
                break
            state[cursor] = 0
            cursor -= 1
        if cursor < 0:
            break
    return SeparationResult(value=total, measurement_tuples=tuples_seen,
                            assignments_examined=assignments_examined,
                            factors_evaluated=factors_evaluated)
