"""Complete bounded L=2 recovery for arbitrary row tensors.

The degree bound is 3M, not a bound inferred from sampled values. Every one
of the 3M+1 residue-distinct points at each of the two Hermite nodes is
required. The caller must obtain and independently verify these values by
the shrinking recurrence; this module never supplies a contraction oracle.
"""

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.extension_lagrange import (
    distinct_residue_points,
    evaluate_polynomial,
    interpolate_newton,
)
from veritas.research.eth_interpolation.source_hermite import (
    SourceHermiteLimits,
    make_source_tapered_plan,
    reconstruct_source_tapered,
)
from veritas.research.paper_verification.hermite_checker import (
    check_functional,
    recover_reference,
)

from .model import HermiteRecoveryCertificate, Refusal, canonical


def _limits(parent, budget, max_points):
    if type(max_points) is not int or not 1 <= max_points <= 4096:
        raise ValueError("general interpolation point cap must be 1..4096")
    M = parent.edge_count
    if type(M) is not int or not 1 <= M <= budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general recovery edge cap")
    degree, extension = 3 * M, parent.defining_polynomial.bit_length() - 1
    if degree + 1 > max_points or degree + 1 > 1 << extension:
        raise Refusal(
            "INCONCLUSIVE_RESOURCE_LIMIT",
            "complete degree-3M grid requires more residue-distinct points",
        )
    precision = parent.precision + 64 * M
    if precision > budget.policy.max_precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general recovery precision cap")
    # Bound a complete point grid before creating rational weights or ring
    # values. This lower bound deliberately excludes JSON and object overhead;
    # serialized evidence receives a separate exact size check below.
    if 2 * (degree + 1) * extension * ((precision + 7) // 8) > budget.policy.max_certificate_bytes:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete point grid byte cap")
    return SourceHermiteLimits(
        max_wires=budget.policy.max_edges,
        max_degree=min(3072, max_points - 1),
        max_target_precision=budget.policy.max_precision,
        max_precision_bits=budget.policy.max_precision,
        max_terms=6 * M,
    )


def make_general_plan(parent, *, budget, max_points=256):
    """Preflight the field and budgets before constructing exact weights."""
    limits = _limits(parent, budget, max_points)
    degree = 3 * parent.edge_count
    # The specialized two-node functional uses quadratic rational operations.
    # Charge a conservative finite operation allowance before the allocation.
    budget.tick(32 * (degree + 1) ** 2)
    plan = make_source_tapered_plan(
        M=parent.edge_count,
        a=1,
        u=1,
        p=parent.precision,
        max_precision_bits=budget.policy.max_precision,
        max_terms=limits.max_terms,
        limits=limits,
    )
    check_functional(
        plan,
        max_wires=limits.max_wires,
        max_precision=limits.max_target_precision,
    )
    budget.tick()
    return plan


def general_points(parent, plan, *, budget, max_points=256):
    """Yield the complete deterministic point grid and prescribed precisions."""
    limits = _limits(parent, budget, max_points)
    if (
        plan.wires != parent.edge_count
        or plan.target_bits != parent.precision
        or (plan.packets_exponent, plan.u, plan.alpha, plan.degree_bound)
        != (1, 1, 4, 3 * parent.edge_count)
    ):
        raise ValueError("general recovery plan differs from parent")
    check_functional(
        plan,
        max_wires=limits.max_wires,
        max_precision=limits.max_target_precision,
    )
    for node in plan.nodes:
        ring = ExtensionRing(
            node.precision_bits,
            parent.defining_polynomial,
            max_precision_bits=budget.policy.max_precision,
        )
        for point in distinct_residue_points(
            ring, plan.degree_bound + 1, max_points=max_points
        ):
            budget.tick()
            yield node.t, point, node.precision_bits


def recover_general_grid(parent, layout, point_rows, *, budget, max_points=256):
    """Interpolate all submitted points, then recover with exact rationals.

    Each coefficient retains its node precision. Agreement with the original
    tensor network belongs to the caller's independent point verification;
    interpolation replay alone is not an oracle for submitted values.
    """
    if layout.parent_digest != parent.content_digest or (layout.a, layout.u) != (1, 1):
        raise ValueError("general recovery layout differs from parent")
    limits = _limits(parent, budget, max_points)
    plan = make_general_plan(parent, budget=budget, max_points=max_points)
    order = plan.degree_bound + 1
    if type(point_rows) not in (tuple, list) or len(point_rows) != 2 * order:
        raise ValueError("incomplete general Hermite point grid")
    if len(canonical(point_rows)) > budget.policy.max_certificate_bytes:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "point evidence byte cap")
    extension = parent.defining_polynomial.bit_length() - 1
    # Newton interpolation, monomial conversion and replay are quadratic in
    # the point count. Account for the extension-coordinate multiplications.
    budget.tick(8 * order**2 * extension**2)
    jets, precisions = {}, {}
    offset = 0
    for node in plan.nodes:
        ring = ExtensionRing(
            node.precision_bits,
            parent.defining_polynomial,
            max_precision_bits=budget.policy.max_precision,
        )
        points = distinct_residue_points(ring, order, max_points=max_points)
        values = []
        for point in points:
            row = point_rows[offset]
            offset += 1
            if (
                type(row) not in (tuple, list)
                or len(row) != 4
                or type(row[0]) is not int
                or row[0] != node.t
                or type(row[1]) not in (tuple, list)
                or any(type(x) is not int for x in row[1])
                or tuple(row[1]) != point
                or type(row[2]) is not int
                or row[2] != node.precision_bits
            ):
                raise ValueError("altered Hermite node, point order or precision")
            value = row[3]
            if (
                type(value) not in (tuple, list)
                or len(value) != extension
                or any(type(x) is not int or not 0 <= x < ring.modulus for x in value)
            ):
                raise ValueError("noncanonical general point value")
            values.append(tuple(value))
        polynomial = interpolate_newton(ring, points, values, max_points=max_points)
        if any(evaluate_polynomial(ring, polynomial, point) != value
               for point, value in zip(points, values)):
            raise ValueError("general interpolation sample mismatch")
        count = min(node.multiplicity, order)
        jets[node.t] = polynomial[:count]
        precisions[node.t] = (node.precision_bits,) * count
        budget.tick()
    result = []
    for coordinate in range(extension):
        data = {t: tuple(value[coordinate] for value in values)
                for t, values in jets.items()}
        value = reconstruct_source_tapered(
            plan, data, coefficient_precisions=precisions, limits=limits
        )
        reference = recover_reference(
            plan, data, precisions,
            max_wires=limits.max_wires,
            max_precision=limits.max_target_precision,
        )
        if value != reference:
            raise ValueError("independent rational Hermite recovery mismatch")
        result.append(value)
        budget.tick(16 * order**2)
    payload = canonical({
        "schema": "VERITAS_R98_GENERAL_RECOVERY_V1",
        "parent_digest": parent.content_digest,
        "layout_digest": layout.content_digest,
        "point_rows": point_rows,
        "coefficient_precisions": {str(t): values for t, values in precisions.items()},
        "result": result,
        "guard_bits": plan.guard_bits,
        "degree_bound": plan.degree_bound,
        "functional_checked_on_all_monomials": True,
        "point_values_require_independent_verification": True,
        "source_qualified": False,
    })
    if len(payload) > budget.policy.max_certificate_bytes:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "recovery evidence byte cap")
    return (tuple(result),), HermiteRecoveryCertificate(payload)
