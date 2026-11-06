"""Numerical parameters of the shared-linear-summary construction.

Paper objects (vendored in `paper/`):

* `eq:parameter-QR` and `lem:incidence-parameters`
  (`main_full_version.tex` l. 2747-2847) -- the theorem-scale choice of
  `r, Q, R, tau, epsilon, D` and the interval `I`.
* `eq:overview-explicit-parameters` (l. 1357-1364) -- the bounded-occurrence
  specialisation with `beta = 1`.
* `eq:incidence-balance-hypotheses` (l. 2447) -- the two balancing
  inequalities.
* `eq:incidence-tail` (l. 2270) -- the binomial tail bound.
* `eq:hasse-order` (l. 1858) -- `q = floor(d_H/Q)`, `J = q+1`.

`theorem_parameters` follows the paper's formulas exactly and reports which
numerical hypotheses hold. For every size a finite reference can reach most
of them fail, which the paper anticipates: "only finitely many `n` fail
these checks" refers to the *asymptotic* regime, not to small `n`.
`scaled_parameters` lets a finite experiment pick `r, Q, R` directly.

Nothing here proves the paper's running-time bound. A tuple whose checks all
pass is a numerical preflight only. The construction's *correctness* does not
depend on any of these checks; only the cost estimate does.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isqrt


def ceil_log2(value: int) -> int:
    """Least `e` with ``value <= 2**e``, for ``value >= 1``."""
    if type(value) is not int or value < 1:
        raise ValueError('positive integer required')
    return (value - 1).bit_length()


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _ceil(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


@dataclass(frozen=True)
class FormParameters:
    """One numerical instantiation of the construction.

    ``M`` is the number of factor-variable incidences and ``d`` the degree of
    the factor product in the incidence indeterminates, so ``d_H = d*R`` bounds
    ``deg H`` (`eq:general-product-degree`).
    """

    n: int
    b: int
    w: int
    r: int
    Q: int
    R: int
    tau: Fraction
    epsilon: Fraction
    D: int
    A0: int
    M: int
    d: int

    def __post_init__(self):
        if any(type(v) is not int for v in (self.n, self.b, self.w, self.r,
                                           self.Q, self.R, self.D, self.A0,
                                           self.M, self.d)):
            raise ValueError('integer parameters required')
        if not (self.n >= 1 and self.b >= 1 and self.w >= 1):
            raise ValueError('n, b, w must be positive')
        if not (self.r >= 2 and self.Q >= 1 and self.R >= 1):
            raise ValueError('r >= 2 and Q, R >= 1 required')
        if not (0 < self.tau <= Fraction(1, 2)):
            raise ValueError('tau must lie in (0, 1/2]')
        if not (0 < self.epsilon <= Fraction(1, 2)):
            raise ValueError('epsilon must lie in (0, 1/2]')
        if self.D != self.r ** (2 * self.Q):
            raise ValueError('D must equal r**(2Q)')
        if self.d < 0:
            raise ValueError('the product degree must be nonnegative')

    @property
    def lam(self):
        return ceil_log2(self.n)

    @property
    def nu(self):
        return ceil_log2(self.lam) if self.lam >= 1 else 1

    @property
    def interval(self):
        """``I = {A0, ..., A0+R-1}`` from `eq:swaps-matrix-definition`."""
        return tuple(range(self.A0, self.A0 + self.R))

    @property
    def degree_bound(self):
        """``d_H = d*R``."""
        return self.d * self.R

    @property
    def q(self):
        """``q = floor(d_H / Q)`` (`eq:hasse-order`)."""
        return self.degree_bound // self.Q

    @property
    def J(self):
        """``J = q + 1``."""
        return self.q + 1

    @property
    def mean_negative(self):
        """``mu = Q(r-1)/(2r)``, the mean of ``Bin(Q, (r-1)/(2r))``."""
        return Fraction(self.Q * (self.r - 1), 2 * self.r)

    @property
    def tail_probability(self):
        """Exact ``Pr[Bin(Q, (r-1)/(2r)) not in I]`` as a Fraction."""
        p = Fraction(self.r - 1, 2 * self.r)
        total = Fraction(0)
        for j in range(self.Q + 1):
            if self.A0 <= j <= self.A0 + self.R - 1:
                continue
            count = 1
            for i in range(j):
                count = count * (self.Q - i) // (i + 1)
            total += count * p ** j * (1 - p) ** (self.Q - j)
        return total

    def check(self):
        """The paper's numerical hypotheses as an ordered ``(name, passed)``."""
        r, Q, R, D, lam = self.r, self.Q, self.R, self.D, self.lam
        return (
            ('r_ge_2', r >= 2),
            ('R_ge_32', R >= 32),
            ('6R_le_Q', 6 * R <= Q),
            ('interval_in_0_Q', 0 <= self.A0 and self.A0 + R - 1 <= Q),
            ('interval_covers_quarter_ball', self._covers_quarter_ball()),
            ('log2_D_le_lambda_over_128',
             128 * max(0, D.bit_length() - 1) <= lam),
            ('balance_2_b_plus_w_D2_le_M', 2 * (self.b + self.w) * D * D <= self.M),
            ('balance_2Qr2_le_n', 2 * Q * r * r <= self.n),
            ('tail_le_epsilon', self.tail_probability <= self.epsilon),
            ('tau_le_half', self.tau <= Fraction(1, 2)),
            ('R_le_Q', self.R <= Q),
        )

    def _covers_quarter_ball(self):
        """`I` contains every integer within `R/4` of `mu` (l. 2818-2832)."""
        mu, radius = self.mean_negative, Fraction(self.R, 4)
        low, high = _ceil(mu - radius), _floor(mu + radius)
        return (0 <= low and high <= self.Q and
                self.A0 <= low and high <= self.A0 + self.R - 1)

    def failed_checks(self):
        return tuple(name for name, ok in self.check() if not ok)

    def all_checks_pass(self):
        return not self.failed_checks()

    def summary(self):
        return {
            'n': self.n, 'b': self.b, 'w': self.w, 'M': self.M,
            'lambda': self.lam, 'nu': self.nu,
            'r': self.r, 'Q': self.Q, 'R': self.R,
            'tau': str(self.tau), 'epsilon': str(self.epsilon),
            'D': self.D, 'A0': self.A0, 'interval': list(self.interval),
            'mean_negative': str(self.mean_negative),
            'tail_probability': str(self.tail_probability),
            'd': self.d, 'd_H': self.degree_bound, 'q': self.q, 'J': self.J,
            'checks': {name: ok for name, ok in self.check()},
            'failed_checks': list(self.failed_checks()),
            'runtime_bound_proven': False,
        }


def theorem_parameters(n: int, b: int, w: int, M: int, d: int, *,
                       beta: int = 1) -> dict:
    """The paper's `eq:parameter-QR` choice, with its checks evaluated.

    Returns a summary dict. ``parameters`` is a `FormParameters` only when
    ``D = r**(2Q)`` fits the finite budget; at theorem scale ``D`` has hundreds
    of millions of bits, so the summary then reports ``D_bits`` and
    ``D_materialised: False`` instead. The formula conformance is checkable in
    either case.

    ``status`` is ``INCONCLUSIVE_PARAMETERS`` when the formula degenerates
    (``r < 2`` or ``Q <= R``), which is the early-failure case in the proof of
    `lem:incidence-parameters`.
    """
    if type(beta) is not int or beta < 1:
        raise ValueError('beta must be a positive integer')
    lam = ceil_log2(n)
    if lam < 1:
        return {'status': 'INCONCLUSIVE_PARAMETERS',
                'reason': 'n = 1 gives lambda = 0; the paper assumes n >= 20'}
    return theorem_parameters_from_lambda(lam, b, w, M, d, beta=beta)


def theorem_parameters_from_lambda(lam: int, b: int, w: int, M: int, d: int, *,
                                   beta: int = 1) -> dict:
    """`eq:parameter-QR` from `lambda = ceil(log2 n)` directly.

    Lets the formulas be checked at theorem scale, where `n = 2**lambda` is not
    representable but `lambda`, `nu`, `r`, `Q`, `R` all are.
    """
    if type(lam) is not int or lam < 1:
        raise ValueError('lambda must be a positive integer')
    nu = ceil_log2(lam)
    root = isqrt(lam)
    r = root // (nu * nu)
    Q = lam // (128 * nu)
    R = (beta + 3) * root
    tau = Fraction(1, r * lam) if r else None
    epsilon = Fraction(1, b * r * r * lam) if r else None
    A0 = _floor(Fraction(Q * (r - 1), 2 * r) - Fraction(R - 1, 2)) if r else 0
    base = {'lambda': lam, 'nu': nu, 'r': r, 'Q': Q, 'R': R,
            'tau': None if tau is None else str(tau),
            'epsilon': None if epsilon is None else str(epsilon),
            'A0': A0, 'beta': beta}
    if r < 2:
        return dict(base, status='INCONCLUSIVE_PARAMETERS',
                    reason='r < 2: the formula needs lambda >= 4*nu**4')
    if Q <= R:
        return dict(base, status='INCONCLUSIVE_PARAMETERS',
                    reason='Q <= R: no Taylor truncation is available')
    # All balance checks are compared in log2 form so that theorem scale
    # (lambda = 2**34) never materialises `n` or `D`.
    #
    # `lambda = ceil(log2 n)` gives only `n > 2**(lambda-1)`, so a sufficient
    # bound must compare against `lambda - 1`, not `lambda`. Using `lambda`
    # would accept tuples for which `2Qr**2 > n` still holds.
    log2_D_upper = 2 * Q * ceil_log2(r)
    checks = {
        'r_ge_2': r >= 2,
        'R_ge_32': R >= 32,
        '6R_le_Q': 6 * R <= Q,
        'interval_in_0_Q': 0 <= A0 and A0 + R - 1 <= Q,
        'log2_D_le_lambda_over_128': 128 * log2_D_upper <= lam,
        # 2(b+w)D**2 <= M, using M >= n > 2**(lam-1).
        'balance_2_b_plus_w_D2_le_M':
            2 * log2_D_upper + ceil_log2(2 * (b + w)) <= lam - 1,
        # 2Qr**2 <= n, again with n > 2**(lam-1).
        'balance_2Qr2_le_n': ceil_log2(2 * Q * r * r) <= lam - 1,
        'tau_le_half': tau is not None and tau <= Fraction(1, 2),
    }
    D_bits = log2_D_upper
    # Only build a concrete FormParameters when both `D` and `n = 2**lam` are
    # representable; at theorem scale `lam` itself is astronomically large.
    materialised = D_bits <= 20 and lam <= 64
    parameters = None
    if materialised:
        parameters = FormParameters(n=1 << lam, b=b, w=w, r=r, Q=Q, R=R,
                                    tau=tau, epsilon=epsilon, D=r ** (2 * Q),
                                    A0=A0, M=M, d=d)
        checks = dict(parameters.check())
    return dict(base, status='THEOREM_PARAMETERS_COMPUTED',
                D_bits=D_bits, D_materialised=materialised,
                parameters=parameters, checks=checks,
                runtime_bound_proven=False)


def scaled_parameters(n: int, b: int, w: int, M: int, d: int, *,
                      r: int, Q: int, R: int,
                      tau: Fraction | None = None,
                      epsilon: Fraction | None = None) -> FormParameters:
    """Caller-chosen ``r, Q, R`` for a finite experiment.

    The paper's ``r, Q, R`` are tuned for ``n`` far beyond what a finite
    reference can execute, so an experiment picks its own. ``tau`` and
    ``epsilon`` default to the paper's formulas; they are reported by
    `FormParameters.check`, never enforced.
    """
    if type(r) is not int or r < 2:
        raise ValueError('r must be an integer at least two')
    if type(Q) is not int or Q < 1:
        raise ValueError('Q must be a positive integer')
    if type(R) is not int or R < 1 or R > Q:
        raise ValueError('R must satisfy 1 <= R <= Q')
    D = r ** (2 * Q)
    if D > 1 << 20:
        raise ValueError('D = r**(2Q) exceeds the finite reference budget')
    # n = 1 gives lambda = 0 and the paper's tau = 1/(r*lambda) is undefined.
    # tau and epsilon are cost parameters only -- they never enter the counting
    # identity -- so the scale is clamped to one rather than dividing by zero.
    lam = max(ceil_log2(n), 1)
    tau = Fraction(1, r * lam) if tau is None else Fraction(tau)
    epsilon = (Fraction(1, b * r * r * lam) if epsilon is None
               else Fraction(epsilon))
    A0 = _floor(Fraction(Q * (r - 1), 2 * r) - Fraction(R - 1, 2))
    return FormParameters(n=n, b=b, w=w, r=r, Q=Q, R=R, tau=tau,
                          epsilon=epsilon, D=D, A0=A0, M=M, d=d)
