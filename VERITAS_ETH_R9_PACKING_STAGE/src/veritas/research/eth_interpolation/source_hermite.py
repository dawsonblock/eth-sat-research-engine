"""Bounded exact implementation of the pinned tapered Hermite formula.

Implements eq:tensor-hermite-origin over Q, with q_t and p_t from
lem:tapered-hermite. Bounds and exact rational calculations make this a finite
reference. No claim about asymptotic time, memory or the general theorem is
made. Scalar coordinates are reconstructed independently.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import comb

from .tapered_hermite import TaperedNode, v2_integer, v2_fraction, _fraction_mod_odd


@dataclass(frozen=True)
class SourceTaperedPlan:
    wires: int
    packets_exponent: int
    u: int
    target_bits: int
    alpha: int
    degree_bound: int
    nodes: tuple[TaperedNode, ...]
    weights: tuple[tuple[int, tuple[Fraction, ...]], ...]
    guard_bits: int
    claim: str = 'FINITE_SOURCE_HERMITE_FORMULA_ONLY'


def _parameters(M, a, u, p, max_precision_bits, max_terms):
    if any(type(x) is not int for x in (M, a, u, p, max_precision_bits, max_terms)):
        raise ValueError('integer parameters required')
    if (not 1 <= M <= 32 or not 1 <= a <= 3 or not 1 <= u <= min(a, M) or
            not 1 <= p <= 1024 or not 1 <= max_precision_bits <= 4096 or
            not 1 <= max_terms <= 256):
        raise ValueError('finite source Hermite parameters outside supported bounds')
    L = 1 << a
    degree = M * (2 * L - 1)
    if degree > 31:
        raise ValueError('finite source Hermite degree cap exceeded')
    h = (3 * M + u - 1) // u
    nodes = []
    for t in range(-L, L):
        if t:
            valuation = v2_integer(t)
            if valuation < u:
                q = h * (u - valuation)
                precision = p + 8 * h * (L >> valuation) + 8 * M * (a + 1)
                if precision > max_precision_bits:
                    raise ValueError('source node precision exceeds cap')
                nodes.append(TaperedNode(t, valuation, q, precision))
    if sum(node.multiplicity for node in nodes) > max_terms:
        raise ValueError('source Hermite term cap exceeded')
    if sum(node.multiplicity for node in nodes) <= degree:
        raise ValueError('insufficient source Hermite multiplicity')
    return 2 * L, degree, tuple(nodes)


def _functional(nodes, alpha, degree):
    weights = []
    for node in nodes:
        t, q = node.t, node.multiplicity
        # Coefficients of 1/E_t(t+alpha*z) modulo z**q.
        inverse = [Fraction(1)] + [Fraction(0)] * (q - 1)
        E_at_zero = Fraction(1)
        for other in nodes:
            if other.t == t:
                continue
            delta = t - other.t
            E_at_zero *= Fraction(-other.t, delta) ** other.multiplicity
            ratio = Fraction(alpha, delta)
            factor = [Fraction((-1)**k * comb(other.multiplicity+k-1, k)) * ratio**k
                      for k in range(q)]
            product = [Fraction(0)] * q
            for i, left in enumerate(inverse):
                if left:
                    for k in range(q-i):
                        product[i+k] += left * factor[k]
            inverse = product
        evaluation = Fraction(-t, alpha)
        values = []
        for j in range(min(q, degree + 1)):
            value = E_at_zero * sum((inverse[k] * evaluation**(j+k)
                                     for k in range(q-j)), Fraction(0))
            values.append(value)
        weights.append((t, tuple(values)))
    return tuple(weights)


def make_source_tapered_plan(*, M, a, u, p, max_precision_bits=1024, max_terms=128):
    alpha, degree, nodes = _parameters(M, a, u, p, max_precision_bits, max_terms)
    weights = _functional(nodes, alpha, degree)
    guard = max((max(0, -v2_fraction(w)) for _, row in weights for w in row if w), default=0)
    plan = SourceTaperedPlan(M, a, u, p, alpha, degree, nodes, weights, guard)
    validate_source_tapered_plan(plan, max_precision_bits=max_precision_bits, max_terms=max_terms)
    return plan


def validate_source_tapered_plan(plan, *, max_precision_bits=4096, max_terms=256):
    """Check source parameters, exact formula, precision and monomial identity."""
    if not isinstance(plan, SourceTaperedPlan) or plan.claim != 'FINITE_SOURCE_HERMITE_FORMULA_ONLY':
        raise ValueError('source Hermite plan required')
    alpha, degree, nodes = _parameters(plan.wires, plan.packets_exponent, plan.u,
                                       plan.target_bits, max_precision_bits, max_terms)
    if (type(plan.alpha) is not int or type(plan.degree_bound) is not int or
            type(plan.nodes) is not tuple or
            any(not isinstance(node, TaperedNode) or any(type(x) is not int for x in
                (node.t, node.valuation, node.multiplicity, node.precision_bits)) for node in plan.nodes) or
            plan.alpha != alpha or plan.degree_bound != degree or plan.nodes != nodes):
        raise ValueError('source Hermite schedule mismatch')
    if (type(plan.weights) is not tuple or len(plan.weights) != len(nodes) or
            any(type(item) is not tuple or len(item) != 2 or type(item[0]) is not int or
                type(item[1]) is not tuple or any(type(weight) is not Fraction for weight in item[1])
                for item in plan.weights)):
        raise ValueError('source Hermite weights require immutable exact fractions')
    expected = _functional(nodes, alpha, degree)
    if plan.weights != expected:
        raise ValueError('source Hermite weights differ from prescribed formula')
    guard = max((max(0, -v2_fraction(w)) for _, row in expected for w in row if w), default=0)
    if type(plan.guard_bits) is not int or plan.guard_bits != guard:
        raise ValueError('source Hermite guard mismatch')
    for node, (t, row) in zip(nodes, expected):
        if any(w and node.precision_bits < max(0, plan.target_bits-v2_fraction(w)) for w in row):
            raise ValueError('source Hermite node precision is insufficient')
    # Independent functional check on a basis of the degree-bounded space.
    for k in range(degree + 1):
        recovered = sum((weight * comb(k, j) * t**(k-j) * alpha**j
                         for t, row in expected for j, weight in enumerate(row) if j <= k),
                        Fraction(0))
        if recovered != int(k == 0):
            raise ValueError('source Hermite functional does not recover monomials')


def reconstruct_source_tapered(plan, jets, *, coefficient_precisions=None):
    validate_source_tapered_plan(plan)
    return _reconstruct_source_tapered_validated(plan, jets, coefficient_precisions=coefficient_precisions)


def _reconstruct_source_tapered_validated(plan, jets, *, coefficient_precisions=None):
    if not isinstance(jets, dict) or any(type(t) is not int for t in jets) or set(jets) != {n.t for n in plan.nodes}:
        raise ValueError('jets must cover exactly the source nodes')
    if coefficient_precisions is not None and (not isinstance(coefficient_precisions, dict) or
            any(type(t) is not int for t in coefficient_precisions) or
            set(coefficient_precisions) != {n.t for n in plan.nodes}):
        raise ValueError('precision metadata must cover exactly the source nodes')
    shift = plan.guard_bits
    modulus_bits = plan.target_bits + shift
    modulus = 1 << modulus_bits
    accumulator = 0
    for node, (t, row) in zip(plan.nodes, plan.weights):
        values = jets[t]
        if not isinstance(values, (tuple, list)) or len(values) < len(row):
            raise ValueError('insufficient node coefficients')
        bits = ((node.precision_bits,) * len(row) if coefficient_precisions is None
                else coefficient_precisions[t])
        if (not isinstance(bits, (tuple, list)) or len(bits) < len(row) or
                any(type(b) is not int or not 0 <= b <= node.precision_bits for b in bits[:len(row)])):
            raise ValueError('invalid coefficient precision metadata')
        for value, precision, weight in zip(values, bits, row):
            if type(value) is not int or value < 0 or value >= 1 << precision:
                raise ValueError('coefficient is not a canonical residue')
            if weight and precision < max(0, plan.target_bits-v2_fraction(weight)):
                raise ValueError('insufficient coefficient-dependent input precision')
            accumulator = (accumulator + _fraction_mod_odd(weight * (1 << shift), modulus_bits) * value) % modulus
    if accumulator % (1 << shift):
        raise ValueError('incompatible nonintegral source Hermite data')
    return (accumulator >> shift) % (1 << plan.target_bits)
