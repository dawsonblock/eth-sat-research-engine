"""Exact packet coefficient extraction without a Cartesian row enumeration.

The production evaluator used to visit ``product(*row_choices)``, i.e. one leaf
per combination of row factors.  For ``q`` affine rows that is ``2**q``
selections before any pruning, so the valid instance ``[z](1-z)^15 == -15 == 1
(mod 8)`` exhausted the 5,000,000-unit default work budget.

Three algorithms live here, with clearly separated roles:

``first_order``
    One retained target mode of exponent one.  The requested coefficient of
    ``prod_r (c_r + l_r z)`` is ``sum_r l_r prod_{s<r} c_s prod_{s>r} c_s``,
    computed with a left prefix and a right suffix product: ``3q`` ring
    multiplications instead of ``q 2**q``.  Exact, no division.

``sparse_dp``
    General truncated polynomial multiplication.  The state is a map from
    exponent vectors to ring elements, keyed only by vectors that are
    componentwise ``<= target``.  Each row contributes ``c_r`` or one
    ``l_r[j] z_j``, so a state is pruned as soon as some coordinate can no
    longer reach its target with the rows that remain.  This never materializes
    the Cartesian product.

``unpruned_reference``
    Deliberately naive: the full Cartesian row enumeration with an explicit
    exponent vector per selection.  It exists so tests and adversarial checks
    can compare against an implementation that shares no control flow with the
    two above.  It is bounded and refuses rather than truncating.

Soundness of pruning
--------------------

Pruning removes a term only when the *ring element* is exactly zero, or when
its exponent vector can no longer be completed.  Both are exact identities in
the truncated polynomial ring, so no information is lost.  In particular a
coefficient whose representative is zero at creation precision is genuinely
zero in ``(Z/2^pc Z)[U]/(f)``; it is never "kept in case a later lift needs
it", because lifting maps the exact representative and cannot resurrect a
vanished coordinate.  Zeroing by individual modular coordinate (rather than by
whole ring element) would be unsound and is never done.
"""
from __future__ import annotations

from itertools import product

from .source_state import SourceAdmissionError

RESOURCE_STATUS = "INCONCLUSIVE_RESOURCE_LIMIT"
ALGORITHMS = ("first_order", "sparse_dp", "unpruned_reference")
SCHEMA = "VERITAS_PACKET_COEFFICIENT_ALGORITHM_V1"


def _zero_vector(length):
    return (0,) * length


def row_factors(rows, cols, local, targets, bits, ring, ar, budget, *, selected):
    """Materialize the affine factor of each row.

    Returns ``(constant, linear)`` per row, where ``linear[j]`` multiplies the
    ``j``-th retained mode variable.  This is the only place the row convention
    is interpreted, and it is shared by every algorithm so the three agree by
    construction on the factors themselves (they differ only in how they
    combine them).
    """
    factors = []
    for row_index, pos in enumerate(rows):
        budget.tick()
        local_value = ring.zero
        for col_pos, c in zip(cols, local[row_index]):
            if bits[col_pos]:
                local_value = ar.add(local_value, c)
        if bits[pos]:
            constant = local_value
        else:
            constant = ar.add(ring.one, ar.neg(local_value))
        linear = []
        for _, coeffs in selected:
            value = coeffs[row_index]
            linear.append(value if bits[pos] else ar.neg(value))
        factors.append((constant, tuple(linear)))
    return factors


def first_order(factors, ring, ar, budget):
    """Coefficient of ``z**1`` in ``prod_r (c_r + l_r z)``."""
    if any(len(linear) != 1 for _, linear in factors):
        raise ValueError("first-order path needs exactly one retained mode")
    count = len(factors)
    budget.tick(count, "coefficient_allocations")
    prefix = [ring.one] * (count + 1)
    for index, (constant, _) in enumerate(factors):
        prefix[index + 1] = ar.mul(prefix[index], constant)
    total = ring.zero
    suffix = ring.one
    for index in range(count - 1, -1, -1):
        constant, linear = factors[index]
        total = ar.add(total, ar.mul(ar.mul(prefix[index], linear[0]), suffix))
        suffix = ar.mul(suffix, constant)
    return total


def sparse_dp(factors, desired, ring, ar, budget, *, max_states=4096):
    """Truncated polynomial product retaining only completable exponents."""
    width = len(desired)
    if width == 0:
        result = ring.one
        for constant, _ in factors:
            result = ar.mul(result, constant)
        return result
    if sum(desired) > len(factors):
        return ring.zero
    target = tuple(desired)
    polynomial = {_zero_vector(width): ring.one}
    remaining = len(factors)
    for index, (constant, linear) in enumerate(factors):
        remaining -= 1
        budget.tick(len(polynomial), "coefficient_states")
        following = {}
        for powers, value in polynomial.items():
            # Continue with the constant term.
            if constant != ring.zero:
                updated = ar.mul(value, constant)
                following[powers] = ar.add(following.get(powers, ring.zero), updated)
            for mode in range(width):
                if powers[mode] >= target[mode]:
                    continue
                coefficient = linear[mode]
                if coefficient == ring.zero:
                    continue
                next_powers = list(powers)
                next_powers[mode] += 1
                next_powers = tuple(next_powers)
                updated = ar.mul(value, coefficient)
                following[next_powers] = ar.add(
                    following.get(next_powers, ring.zero), updated)
        # Drop exact zeros and states that can no longer be completed.
        polynomial = {}
        for powers in sorted(following):
            value = following[powers]
            if value == ring.zero:
                continue
            deficit = sum(target[i] - powers[i] for i in range(width))
            if deficit > remaining:
                continue
            if any(target[i] - powers[i] > remaining for i in range(width)):
                continue
            polynomial[powers] = value
        if not polynomial:
            return ring.zero
        if len(polynomial) > max_states:
            raise SourceAdmissionError(
                RESOURCE_STATUS,
                f"sparse coefficient state cap exceeded ({len(polynomial)} > {max_states})")
        budget.tick(len(polynomial), "coefficient_allocations")
    return polynomial.get(target, ring.zero)


def unpruned_reference(factors, desired, ring, ar, budget, *, max_selections=1 << 20):
    """Full Cartesian row enumeration; a deliberately independent reference."""
    width = len(desired)
    if sum(desired) > len(factors):
        return ring.zero
    selections = 1
    for constant, linear in factors:
        selections *= 1 + len(linear)
        if selections > max_selections:
            raise SourceAdmissionError(
                RESOURCE_STATUS,
                "unpruned reference selection cap exceeded")
    result = ring.zero
    target = tuple(desired)
    for choice in product(*[range(1 + len(linear)) for _, linear in factors]):
        counts = [0] * width
        term = ring.one
        viable = True
        for index, pick in enumerate(choice):
            constant, linear = factors[index]
            if pick == 0:
                term = ar.mul(term, constant)
            else:
                mode = pick - 1
                counts[mode] += 1
                if counts[mode] > target[mode]:
                    viable = False
                    break
                term = ar.mul(term, linear[mode])
        budget.tick(1, "coefficient_selections")
        if viable and tuple(counts) == target:
            result = ar.add(result, term)
    return result


def target_coefficient(factors, desired, ring, ar, budget, *, algorithm="auto",
                       max_states=4096):
    """Dispatch to the cheapest exact algorithm for this request."""
    if algorithm not in ALGORITHMS + ("auto",):
        raise ValueError("unknown coefficient algorithm")
    width = len(desired)
    if algorithm == "auto":
        if width == 1 and desired[0] == 1:
            algorithm = "first_order"
        elif sum(desired) > len(factors) or width == 0:
            algorithm = "sparse_dp"
        else:
            algorithm = "sparse_dp"
    if algorithm == "first_order":
        if width != 1 or desired[0] != 1:
            raise ValueError("first_order requires one mode of exponent one")
        return first_order(factors, ring, ar, budget)
    if algorithm == "sparse_dp":
        return sparse_dp(factors, desired, ring, ar, budget, max_states=max_states)
    return unpruned_reference(factors, desired, ring, ar, budget)


def algorithm_for(desired):
    """Deterministic algorithm label, recorded in every ledger."""
    if len(desired) == 1 and desired[0] == 1:
        return "first_order"
    return "sparse_dp"
