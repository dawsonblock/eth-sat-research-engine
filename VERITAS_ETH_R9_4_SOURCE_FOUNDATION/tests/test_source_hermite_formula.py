"""Independent exact checks of the manuscript's full-node Hermite formula."""
from dataclasses import replace
from fractions import Fraction
from math import comb
from random import Random

import pytest

from veritas.research.eth_interpolation.source_hermite import (
    make_source_tapered_plan, reconstruct_source_tapered, validate_source_tapered_plan,
)
from veritas.research.eth_interpolation.tapered_hermite import (
    sample_integer_polynomial, v2_fraction, make_tapered_plan,
)


def direct_source_formula(nodes, alpha, polynomial):
    """Evaluate the paper's formula with repeated linear-series division.

    This independently works with polynomial jets and the original product;
    it does not use the implementation's rational recovery weights.
    """
    total = Fraction(0)
    for node in nodes:
        t, q = node.t, node.multiplicity
        jet = [sum((c * comb(k, j) * t**(k-j) * alpha**j
                    for k, c in enumerate(polynomial) if k >= j), Fraction(0))
               for j in range(q)]
        factor_at_zero = Fraction(1)
        for other in nodes:
            if other.t == t:
                continue
            delta = t - other.t
            factor_at_zero *= Fraction(-other.t, delta) ** other.multiplicity
            ratio = Fraction(alpha, delta)
            # Divide by (1+ratio*z) one factor at a time modulo z**q.
            for _ in range(other.multiplicity):
                quotient = [jet[0]]
                for j in range(1, q):
                    quotient.append(jet[j] - ratio*quotient[j-1])
                jet = quotient
        point = Fraction(-t, alpha)
        total += factor_at_zero * sum((value*point**j for j, value in enumerate(jet)), Fraction(0))
    return total


@pytest.mark.parametrize('M,a,u,p', [(1,1,1,5), (2,1,1,7), (1,2,1,6), (2,2,2,5), (1,3,1,4)])
def test_source_formula_matches_independent_rational_oracle_and_random_polynomials(M,a,u,p):
    plan = make_source_tapered_plan(M=M, a=a, u=u, p=p)
    L, h = 1 << a, (3*M + u-1)//u
    for node in plan.nodes:
        i = (abs(node.t) & -abs(node.t)).bit_length() - 1
        assert node.multiplicity == h*(u-i)
        assert node.precision_bits == p + 8*h*(L >> i) + 8*M*(a+1)
    rng = Random(50000+M*1000+a*100+u*10+p)
    for _ in range(5):
        # Odd denominators give valid two-adic coefficients.
        polynomial = tuple(Fraction(rng.randrange(-10, 11), rng.choice((1,3,5)))
                           for _ in range(plan.degree_bound+1))
        assert direct_source_formula(plan.nodes, plan.alpha, polynomial) == polynomial[0]
        jets = sample_integer_polynomial(plan, polynomial)
        expected = polynomial[0].numerator * pow(polynomial[0].denominator, -1, 1 << p) % (1 << p)
        assert reconstruct_source_tapered(plan, jets) == expected
    assert sum(len(row) for _, row in plan.weights) > plan.degree_bound + 1
    assert plan.claim == 'FINITE_SOURCE_HERMITE_FORMULA_ONLY'


def test_source_formula_uses_all_nodes_not_old_prefix_functional():
    plan = make_source_tapered_plan(M=1, a=1, u=1, p=5)
    old = make_tapered_plan(M=1, a=1, u=1, p=5)
    assert len(plan.weights) == 2 and all(any(row) for _, row in plan.weights)
    assert len(plan.weights[0][1]) + len(plan.weights[1][1]) > len(old.recovery_plan.weights)
    assert plan.weights[0][1][0] != old.recovery_plan.weights[0]


def test_source_precision_is_coefficientwise_and_forgery_is_rejected():
    plan = make_source_tapered_plan(M=1,a=1,u=1,p=5)
    jets = sample_integer_polynomial(plan, (19, -23, 7, 9))
    node_bits = {node.t: tuple(max(0, plan.target_bits - v2_fraction(w)) if w else 0
                              for w in row)
                 for node, (_, row) in zip(plan.nodes, plan.weights)}
    reduced = {t: tuple(v % (1 << bits) for v, bits in zip(jets[t], node_bits[t]))
               for t in jets}
    assert reconstruct_source_tapered(plan, reduced, coefficient_precisions=node_bits) == 19
    t, j = next((t, j) for t, bits in node_bits.items() for j, b in enumerate(bits) if b > 0)
    bits = dict(node_bits); mutable = list(bits[t]); mutable[j] -= 1; bits[t] = tuple(mutable)
    changed = dict(reduced); mutable = list(changed[t]); mutable[j] %= 1 << bits[t][j]; changed[t] = tuple(mutable)
    with pytest.raises(ValueError, match='insufficient coefficient-dependent'):
        reconstruct_source_tapered(plan, changed, coefficient_precisions=bits)
    t, row = plan.weights[0]
    forged = replace(plan, weights=((t, (row[0]+1,) + row[1:]),) + plan.weights[1:])
    with pytest.raises(ValueError, match='weights differ'):
        reconstruct_source_tapered(forged, jets)
    nonexact = replace(plan, weights=((t, (float(row[0]),) + row[1:]),) + plan.weights[1:])
    with pytest.raises(ValueError, match='immutable exact fractions'):
        reconstruct_source_tapered(nonexact, jets)
    with pytest.raises(ValueError, match='schedule mismatch'):
        validate_source_tapered_plan(replace(plan, nodes=(replace(plan.nodes[0], multiplicity=4),) + plan.nodes[1:]))
    with pytest.raises(ValueError, match='exactly the source nodes'):
        reconstruct_source_tapered(plan, {})


def test_source_formula_fails_closed_at_resource_caps():
    with pytest.raises(ValueError, match='term cap'):
        make_source_tapered_plan(M=2, a=1, u=1, p=5, max_terms=1)
    with pytest.raises(ValueError, match='precision exceeds cap'):
        make_source_tapered_plan(M=1, a=1, u=1, p=5, max_precision_bits=5)
    with pytest.raises(ValueError, match='outside supported bounds'):
        make_source_tapered_plan(M=1, a=4, u=1, p=5)
