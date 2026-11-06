"""Coefficient-level guard checks for the bounded Hermite reference."""

import pytest

from veritas.research.eth_interpolation.tapered_hermite import (
    make_tapered_plan, reconstruct_tapered, sample_integer_polynomial,
)


def fixture():
    plan = make_tapered_plan(M=1, a=1, u=1, p=5)
    samples = sample_integer_polynomial(plan, (19, -23, 7, 9))
    # For these nodes the exact recovery weights are 7/8, 3/16, 1/32,
    # and 1/8. Their individual sufficient precisions are 8, 9, 10, 8.
    bits = {-1: (8, 9, 10), 1: (8, 0, 0)}
    residues = {t: tuple(value % (1 << precision)
                         for value, precision in zip(samples[t], precisions))
                for t, precisions in bits.items()}
    return plan, residues, bits


def test_coefficientwise_guard_allows_mixed_precisions():
    plan, residues, bits = fixture()
    assert reconstruct_tapered(plan, residues, coefficient_precisions=bits) == 19


def test_coefficientwise_guard_rejects_insufficient_or_forged_metadata():
    plan, residues, bits = fixture()
    insufficient = {-1: (8, 9, 9), 1: bits[1]}
    altered = dict(residues)
    altered[-1] = (residues[-1][0], residues[-1][1], residues[-1][2] % (1 << 9))
    with pytest.raises(ValueError, match='insufficient coefficient-dependent'):
        reconstruct_tapered(plan, altered, coefficient_precisions=insufficient)
    with pytest.raises(ValueError, match='precision metadata'):
        reconstruct_tapered(plan, residues, coefficient_precisions={-1: bits[-1]})
    with pytest.raises(ValueError, match='declared precision'):
        reconstruct_tapered(plan, {-1: residues[-1], 1: (residues[1][0], 1, 0)},
                            coefficient_precisions=bits)
