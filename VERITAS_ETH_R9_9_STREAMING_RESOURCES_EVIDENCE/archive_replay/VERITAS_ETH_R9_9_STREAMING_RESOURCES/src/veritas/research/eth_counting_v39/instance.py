"""Polynomial factor instances for the shared-linear-summary construction.

Paper objects (vendored in `paper/`):

* `eq:general-product-sum` and `eq:general-product-degree`
  (`main_full_version.tex` l. 1677-1697) -- the target sum `Z` and the degree
  `d` of the factor product in the incidence indeterminates.
* `eq:factor-incidences` (l. 2098-2106) -- the scope and incidence bounds
  `w` and `b`, and the convention `n <= M <= b n`.
* `subsec:preview-encoding` (l. 575-632) -- the clause polynomial
  `Phi_e = 1 - prod_v (1 - L_{e,v})` and the dummy clauses.

The factors here are general rational polynomials over their scopes, as
`sec:counting` allows. `clause_factor` gives the satisfaction indicator, and
`cnf_instance` applies the paper's normalisations (drop tautologies, collapse
repeated literals, one dummy clause per unused variable).
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product


@dataclass(frozen=True)
class PolynomialFactor:
    """A rational polynomial in a fixed, ordered scope."""

    scope: tuple
    terms: tuple          # ((exponent tuple over scope, Fraction), ...)
    label: str = ''

    def __post_init__(self):
        if type(self.scope) is not tuple or len(set(self.scope)) != len(self.scope):
            raise ValueError('factor scope must be a tuple of distinct variables')
        for exponents, coefficient in self.terms:
            if len(exponents) != len(self.scope):
                raise ValueError('exponent tuple must match the scope')
            if any(type(e) is not int or e < 0 for e in exponents):
                raise ValueError('exponents must be nonnegative integers')
            if type(coefficient) is not Fraction:
                raise ValueError('coefficients must be Fractions')

    @property
    def degree(self):
        return max((sum(exponents) for exponents, _ in self.terms), default=0)

    def evaluate(self, values):
        """Evaluate at one rational value per scope entry."""
        if len(values) != len(self.scope):
            raise ValueError('one value per scope entry required')
        total = Fraction(0)
        for exponents, coefficient in self.terms:
            term = coefficient
            for exponent, value in zip(exponents, values):
                if exponent:
                    term *= value ** exponent
            total += term
        return total


@dataclass(frozen=True)
class FactorInstance:
    """`(n, (I_f), (Phi_f))` with the incidence statistics the paper needs."""

    n: int
    scopes: tuple
    factors: tuple
    b: int
    w: int
    M: int
    empty_scopes: tuple = ()
    constant_zero: bool = False

    def __post_init__(self):
        if type(self.n) is not int or self.n < 1:
            raise ValueError('positive variable count required')
        if len(self.scopes) != len(self.factors):
            raise ValueError('one factor per scope required')
        if self.M != sum(len(scope) for scope in self.scopes):
            raise ValueError('M must equal the number of incidences')
        if self.constant_zero:
            return
        if not (1 <= self.b and 1 <= self.w):
            raise ValueError('incidence bounds must be positive')
        if not (self.n <= self.M <= self.b * self.n):
            raise ValueError('the paper requires n <= M <= b*n')

    @property
    def d(self):
        """Degree of the factor product in the incidence indeterminates."""
        return sum(factor.degree for factor in self.factors)

    def incidence_list(self):
        return tuple((f, v) for f, scope in enumerate(self.scopes) for v in scope)

    def factor_for(self, factor):
        return self.factors[factor]


def _clause_polynomial(scope, signs):
    """`1 - prod_v (1 - L_v)` as a polynomial in `scope` order.

    `signs[position]` is true for a positive literal, so the factor is
    `1 - X_v`; a negative literal contributes `X_v`.
    """
    product_terms = {(0,) * len(scope): Fraction(1)}
    for position, positive in enumerate(signs):
        options = ((0, Fraction(1)), (1, Fraction(-1))) if positive else ((1, Fraction(1)),)
        expanded = {}
        for exponents, coefficient in product_terms.items():
            for shift, weight in options:
                updated = list(exponents)
                updated[position] += shift
                key = tuple(updated)
                expanded[key] = expanded.get(key, Fraction(0)) + coefficient * weight
        product_terms = expanded
    result = {key: -value for key, value in product_terms.items()}
    zero = (0,) * len(scope)
    result[zero] = result.get(zero, Fraction(0)) + 1
    return tuple(sorted((key, value) for key, value in result.items() if value))


def clause_factor(scope, literals, label=''):
    """Satisfaction indicator for one clause, as a rational polynomial."""
    return PolynomialFactor(tuple(scope), _clause_polynomial(scope, literals),
                            label=label)


def cnf_instance(clauses, n: int, *, max_width=3, max_occurrences=3):
    """Build the paper's normalised factor instance for a CNF.

    `clauses` is a sequence of literal lists; a literal is a signed integer
    with `abs(value)` the variable index in `1..n`. The returned instance uses
    zero-based variable indices in `0..n-1`.
    """
    if type(n) is not int or n < 1:
        raise ValueError('positive variable count required')
    scopes, factors, labels = [], [], []
    occurrences = [0] * (n + 1)
    constant_zero = False
    for index, clause in enumerate(clauses):
        literals = []
        seen = {}
        tautology = False
        for literal in clause:
            if type(literal) is not int or literal == 0 or abs(literal) > n:
                raise ValueError('literal outside the declared variables')
            variable, positive = abs(literal), literal > 0
            if variable in seen:
                if seen[variable] != positive:
                    tautology = True
                continue
            seen[variable] = positive
            literals.append((variable, positive))
        if tautology:
            continue
        if not literals:
            constant_zero = True
            continue
        if len(literals) > max_width:
            raise ValueError('clause width exceeds the declared bound')
        ordered = sorted(variable for variable, _ in literals)
        order = [next(position for position, (variable, _) in enumerate(literals)
                      if variable == target) for target in ordered]
        signs = tuple(literals[position][1] for position in order)
        for variable in ordered:
            occurrences[variable] += 1
            if occurrences[variable] > max_occurrences:
                raise ValueError('variable occurrence bound exceeded')
        scope = tuple(variable - 1 for variable in ordered)
        scopes.append(scope)
        factors.append(clause_factor(scope, signs, label=f'clause:{index}'))
        labels.append(f'clause:{index}')
    for variable in range(1, n + 1):
        if occurrences[variable] == 0:
            scopes.append((variable - 1,))
            factors.append(PolynomialFactor((variable - 1,),
                                            (((0,), Fraction(1)),),
                                            label=f'dummy:{variable}'))
            labels.append(f'dummy:{variable}')
    M = sum(len(scope) for scope in scopes)
    b = max([0] + [occurrences[v] for v in range(1, n + 1)])
    w = max([0] + [len(scope) for scope in scopes])
    empty = tuple(index for index, scope in enumerate(scopes) if not scope)
    return FactorInstance(n=n, scopes=tuple(scopes), factors=tuple(factors),
                          b=max(b, 1), w=max(w, 1), M=M, empty_scopes=empty,
                          constant_zero=constant_zero)
