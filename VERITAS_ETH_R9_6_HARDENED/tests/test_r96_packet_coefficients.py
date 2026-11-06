"""R9.6 regression tests: bounded exact packet coefficient extraction.

Red test (R9.5): ``evaluate_compiled`` visited ``product(*row_choices)`` before
any pruning.  The valid instance ``[z](1-z)^15 == -15 == 1 (mod 8)`` with a
degree-2 extension and two jet coordinates exhausted the 5,000,000-unit default
work budget and returned no value.

Green test (R9.6): the first-order product rule and the truncated sparse DP
both return the exact coefficient, and a deliberately naive Cartesian reference
plus the independent integer-polynomial oracle agree on randomized inputs.
"""
from itertools import product
import random

import pytest

from veritas.research.tapered_v4.packet_coefficients import (
    first_order, row_factors, sparse_dp, target_coefficient, unpruned_reference)
from veritas.research.tapered_v4.source_recipes import (
    SCHEMA, Arithmetic, EntryBudget, EntryLimits, compile_entry,
    evaluate_compiled, evaluate_source_entry)
from veritas.research.tapered_v4.source_state import (
    SourceAdmissionError, SourceTensorReference)
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.independent_r95.recipe_oracle import evaluate_reference


def reference(data, *, arity, precision=3, polynomial=7, jet_length=1):
    import json
    payload = {"schema": SCHEMA, "kind": "packet", "arity": arity,
               "creation_precision": precision, "polynomial": polynomial,
               "jet_length": jet_length, "data": data}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    return SourceTensorReference(arity, precision, polynomial, jet_length,
                                 SCHEMA + ":packet", raw)


def unit_jet(jet_length, extension_degree):
    return [[1] + [0] * (extension_degree - 1) for _ in range(jet_length)]


def first_order_packet(rows_count, *, precision=3, polynomial=7, jet_length=1):
    """rows_count factors (1 - z_i); one target of exponent one, coeff 1."""
    one = unit_jet(jet_length, polynomial.bit_length() - 1)
    data = [list(range(rows_count)), [], [[] for _ in range(rows_count)],
            [[1, [one for _ in range(rows_count)]]], []]
    return reference(data, arity=rows_count, precision=precision,
                     polynomial=polynomial, jet_length=jet_length)


def test_first_order_fifteen_rows_returns_one_within_default_budget():
    """[z](1-z)^15 = -15 = 1 (mod 8) under the stock 5,000,000-unit budget."""
    ref = first_order_packet(15, jet_length=2)
    out = evaluate_source_entry(ref, (0,) * 15, precision=3)
    assert out["status"] == "EXACT_CREATION_PRECISION_ENTRY"
    assert out["result"] == ((1, 0), (1, 0))
    assert out["ledger"]["notes"]["coefficient_algorithm"] == "first_order"
    assert out["ledger"]["work_units"] < 5_000


@pytest.mark.parametrize("rows_count", [0, 1, 2, 3, 4, 5, 8, 12, 15, 16])
def test_first_order_matches_integer_binomial_expansion(rows_count):
    """Independent check: [z] prod_i (1 - z_i) = -rows_count (mod 8)."""
    ref = first_order_packet(rows_count)
    out = evaluate_source_entry(ref, (0,) * rows_count, precision=3)
    assert out["status"] == "EXACT_CREATION_PRECISION_ENTRY"
    assert out["result"] == (((-rows_count) % 8, 0),)


def test_zeroth_exponent_is_the_constant_product():
    # One row, one column.  With no retained target the value is the product
    # of the affine constants: 1 - 3 = -2 = 6 (mod 8) and 3 respectively.
    data = [[0], [1], [[[[3, 0]]]], [], []]
    ref = reference(data, arity=2)
    assert evaluate_source_entry(ref, (0, 1), precision=3)["result"] == ((6, 0),)
    assert evaluate_source_entry(ref, (1, 1), precision=3)["result"] == ((3, 0),)


def test_empty_product_returns_one():
    out = evaluate_source_entry(reference([[], [], [], [], []], arity=0), (),
                                precision=3)
    assert out["result"] == ((1, 0),)


def test_zero_rows_with_positive_target_is_zero():
    out = evaluate_source_entry(
        reference([[], [], [], [[1, []]], []], arity=0), (), precision=3)
    assert out["result"] == ((0, 0),)


@pytest.mark.parametrize("beta,expected", [
    (0, 1), (1, 5), (2, 3), (3, 7)])
def test_repeated_exponent_over_three_rows(beta, expected):
    """(1 - z)^3 = 1 - 3z + 3z^2 - z^3 over Z/8."""
    one = unit_jet(1, 2)
    data = [[0, 1, 2], [], [[], [], []],
            [[beta, [one, one, one]]], []]
    out = evaluate_source_entry(reference(data, arity=3), (0, 0, 0),
                                precision=3)
    assert out["result"] == ((expected, 0),)


def test_mixed_mode_exponents():
    one = unit_jet(1, 2)
    # (1 - z1 - z2)^2 has coefficient 2 at z1 z2.
    data = [[0, 1], [], [[], []],
            [[1, [one, one]], [1, [one, one]]], []]
    out = evaluate_source_entry(reference(data, arity=2), (0, 0), precision=3)
    assert out["result"] == ((2, 0),)


def test_high_precision_keeps_the_exact_representative():
    ref = first_order_packet(15, precision=9, polynomial=7, jet_length=1)
    out = evaluate_source_entry(ref, (0,) * 15, precision=9)
    # -15 mod 512
    assert out["result"] == ((2 ** 9 - 15, 0),)


def test_all_zero_coefficients_give_zero():
    zero = [[0, 0]]
    data = [[0, 1], [], [[], []], [[1, [zero, zero]]], []]
    out = evaluate_source_entry(reference(data, arity=2), (0, 0), precision=3)
    assert out["result"] == ((0, 0),)


def test_cancellation_gives_zero():
    one = unit_jet(1, 2)
    neg_one = [[7, 0]]
    data = [[0, 1], [], [[], []], [[1, [one, neg_one]]], []]
    # (1 - z)(1 + z) = 1 - z^2: the coefficient of z cancels exactly.
    out = evaluate_source_entry(reference(data, arity=2), (0, 0), precision=3)
    assert out["result"] == ((0, 0),)


def _random_packet(rng, *, precision=3, polynomial=7, jet_length=2,
                   max_rows=4, max_cols=3, max_modes=3):
    ring = JetRing(ExtensionRing(precision, polynomial), jet_length)
    e = ring.base.e
    modulus = ring.base.modulus
    rows_count = rng.randrange(max_rows + 1)
    cols_count = rng.randrange(max_cols + 1)
    arity = rows_count + cols_count
    rows = list(range(rows_count))
    cols = list(range(rows_count, arity))
    jet = lambda: [[rng.randrange(modulus) for _ in range(e)]
                   for _ in range(jet_length)]
    local = [[jet() for _ in range(cols_count)] for _ in range(rows_count)]
    targets = [[rng.randrange(3), [jet() for _ in range(rows_count)]]
               for _ in range(rng.randrange(max_modes + 1))]
    sources = [[rng.randrange(3),
                [rng.randrange(modulus) for _ in range(cols_count)]]
               for _ in range(rng.randrange(max_modes + 1))]
    return [rows, cols, local, targets, sources], arity


@pytest.mark.parametrize("seed", range(48))
def test_randomized_packets_agree_with_unpruned_reference_and_oracle(seed):
    rng = random.Random(20261105 + seed)
    data, arity = _random_packet(rng)
    ref = reference(data, arity=arity, jet_length=2)
    for bits in product((0, 1), repeat=arity):
        budget = EntryBudget(EntryLimits(max_work=4_000_000))
        compiled = compile_entry(ref, budget)
        fast = evaluate_compiled(compiled, bits, 7, budget)
        slow_budget = EntryBudget(EntryLimits(max_work=4_000_000))
        slow_compiled = compile_entry(ref, slow_budget)
        slow = _unpruned_value(slow_compiled, bits, 7, slow_budget)
        oracle = evaluate_reference(ref, bits, precision=7, max_work=4_000_000)
        assert fast == slow == oracle


def _unpruned_value(compiled, bits, precision, budget):
    """Re-evaluate one compiled packet with the naive Cartesian reference."""
    ref = compiled.reference
    ring = JetRing(ExtensionRing(ref.creation_precision,
                                 ref.defining_polynomial), ref.jet_length)
    ar = Arithmetic(ring, budget)
    rows, cols, local, targets, sources = compiled.data
    selected = [(beta, coeffs) for beta, coeffs in targets if beta]
    desired = tuple(beta for beta, _ in selected)
    if sum(desired) > len(rows):
        return ring.zero
    factors = row_factors(rows, cols, local, targets, bits, ring, ar, budget,
                          selected=selected)
    result = unpruned_reference(factors, desired, ring, ar, budget)
    for beta, coeffs in sources:
        source = ring.zero
        for pos, c in zip(cols, coeffs):
            if bits[pos]:
                source = ar.add(source, ring.elem([[c]]))
        result = ar.mul(result, ar.power(source, beta))
    return result


def test_sparse_dp_state_cap_refuses_rather_than_truncating():
    ring = JetRing(ExtensionRing(3, 7), 1)
    budget = EntryBudget(EntryLimits(max_work=4_000_000))
    ar = Arithmetic(ring, budget)
    factors = [(ring.one, (ring.one, ring.one)) for _ in range(6)]
    with pytest.raises(SourceAdmissionError):
        sparse_dp(factors, (2, 2), ring, ar, budget, max_states=3)
    # The same request succeeds with the default state cap.
    assert sparse_dp(factors, (2, 2), ring, ar, budget) == ((2, 0),)


def test_first_order_refuses_mismatched_request():
    ring = JetRing(ExtensionRing(3, 7), 1)
    budget = EntryBudget(EntryLimits())
    ar = Arithmetic(ring, budget)
    factors = [(ring.one, (ring.one, ring.one))]
    with pytest.raises(ValueError):
        first_order(factors, ring, ar, budget)
    with pytest.raises(ValueError):
        target_coefficient(factors, (1, 1), ring, ar, budget,
                           algorithm="first_order")


def test_work_growth_is_linear_in_rows_not_exponential():
    """The first-order path charges O(rows); the naive path charges 2**rows."""
    measured = {}
    for rows_count in (8, 12, 16):
        ref = first_order_packet(rows_count)
        out = evaluate_source_entry(ref, (0,) * rows_count, precision=3)
        measured[rows_count] = out["ledger"]["work_units"]
    # Linear growth: doubling the row count less than doubles the charge.
    assert measured[16] < 2 * measured[8]
    # And far below the 2**16 selections the naive enumeration would visit.
    assert measured[16] < 2_000
