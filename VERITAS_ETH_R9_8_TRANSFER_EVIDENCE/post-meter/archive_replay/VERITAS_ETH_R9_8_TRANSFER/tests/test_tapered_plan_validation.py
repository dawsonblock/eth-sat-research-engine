from dataclasses import replace
from fractions import Fraction

import pytest

from veritas.research.eth_interpolation.tapered_hermite import (
    make_tapered_plan, reconstruct_tapered, sample_integer_polynomial,
    validate_tapered_plan,
)


@pytest.mark.parametrize('M,a,u,p', [(1, 1, 1, 5), (2, 2, 2, 7), (1, 3, 1, 3)])
def test_independent_plan_validation_and_polynomial_recovery(M, a, u, p):
    plan = make_tapered_plan(M=M, a=a, u=u, p=p)
    validate_tapered_plan(plan)
    coefficients = tuple((i % 7) - 3 for i in range(plan.degree_bound + 1))
    jets = sample_integer_polynomial(plan, coefficients)
    assert reconstruct_tapered(plan, jets) == coefficients[0] % (1 << p)


def test_plan_verifier_rejects_forged_schedule_and_recovery_data():
    plan = make_tapered_plan(M=1, a=1, u=1, p=5)
    first = plan.nodes[0]
    bad_weights = list(plan.recovery_plan.weights)
    bad_weights[0] += Fraction(1)
    bad_samples = list(plan.recovery_plan.samples_used)
    bad_samples[0] = bad_samples[-1]
    variants = [
        replace(plan, alpha=plan.alpha * 2),
        replace(plan, degree_bound=plan.degree_bound - 1),
        replace(plan, claim='UNIVERSAL_THEOREM'),
        replace(plan, nodes=(replace(first, precision_bits=first.precision_bits - 1),) + plan.nodes[1:]),
        replace(plan, nodes=(replace(first, multiplicity=first.multiplicity + 1),) + plan.nodes[1:]),
        replace(plan, recovery_plan=replace(plan.recovery_plan, weights=tuple(bad_weights))),
        replace(plan, recovery_plan=replace(plan.recovery_plan, samples_used=tuple(bad_samples))),
        replace(plan, recovery_plan=replace(plan.recovery_plan, guard_bits=0)),
        replace(plan, necessary_precision=tuple((t, 0) for t, _ in plan.necessary_precision)),
    ]
    for forged in variants:
        with pytest.raises(ValueError):
            validate_tapered_plan(forged)
