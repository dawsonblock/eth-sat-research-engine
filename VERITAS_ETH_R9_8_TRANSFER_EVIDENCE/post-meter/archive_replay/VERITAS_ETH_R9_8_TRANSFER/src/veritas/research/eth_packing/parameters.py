"""Appendix D manuscript parameters, kept separate from scaled research.

Source reading: the Oct. 25 manuscript's public quantitative-contraction.tex
uses FLOOR in u_d, not CEILING (as incorrectly asserted by v2.6/v2.7).
The main-branch URL is mutable; numerical eligibility != proof certification.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

EPSILON_DENOMINATOR = 131072
MANUSCRIPT_R = 64
SOURCE_URL = ('https://github.com/openai/math/blob/main/preprints/'
              'The-Exponential-Time-Hypothesis-is-False-October-25-2026/'
              'build/quantitative-contraction.tex')

@dataclass(frozen=True)
class Parameters:
    s: int
    depth: int
    mode: str
    r: int
    log2_s_ceil: int
    u: int
    a: int
    packet_size: int
    theorem_parameters: bool
    eligible: bool
    reason: str
    source_status: str = 'UNPINNED_PUBLIC_MAIN_REFERENCE'

    def to_dict(self) -> dict:
        return asdict(self)


def manuscript_parameters(s: int, depth: int = 0, *, M: int | None = None,
                          delta: int | None = None) -> Parameters:
    if type(s) is not int or s < 2 or type(depth) is not int or depth < 0:
        raise ValueError('s>=2 and nonnegative integral depth required')
    lam = (s - 1).bit_length()
    def floor_u(d):
        return lam // (EPSILON_DENOMINATOR << d)
    u = floor_u(depth)
    a = 2 * sum(floor_u(j) for j in range(depth + 1))
    # Avoid constructing absurdly large integers when no finite experiment can run.
    if a > 32768:
        raise ValueError('parameter bit-size exceeds bounded reference limit')
    L = 1 << a
    D = MANUSCRIPT_R ** (2 * a)
    if (M is None) != (delta is None):
        raise ValueError('M and delta must be supplied together')
    if M is not None and (type(M) is not int or M < 0 or
                          type(delta) is not int or delta < 0):
        raise ValueError('M and delta must be nonnegative integers')
    numerical = bool(M is not None and u > 0 and
                     M >= 2 * D * D * delta and M >= L * D and 2 * L <= delta)
    return Parameters(s, depth, 'MANUSCRIPT_EXACT', MANUSCRIPT_R, lam, u, a,
        L, True, numerical,
        ('D.6 numerical tests satisfied, but full theorem NOT certified; '
         if numerical else 'D.6 not established; ') +
        'source is a mutable branch reference; theorem hypotheses and a '
        'pinned-source audit remain separate obligations')


def scaled_parameters(s: int, a: int = 2, r: int = 4,
                      depth: int = 0) -> Parameters:
    if type(s) is not int or s < 1 or type(a) is not int or not 1 <= a <= 5:
        raise ValueError('scaled s>=1 and 1<=a<=5 required')
    if type(r) is not int or not 2 <= r <= 64 or type(depth) is not int or depth < 0:
        raise ValueError('scaled 2<=r<=64 and depth>=0 required')
    return Parameters(s, depth, 'EXPERIMENTAL_SCALED', r, (s - 1).bit_length(),
        1, a, 1 << a, False, False,
        'scaled experiment: no ETH theorem or asymptotic guarantee',
        'EXPERIMENTAL_ONLY')
