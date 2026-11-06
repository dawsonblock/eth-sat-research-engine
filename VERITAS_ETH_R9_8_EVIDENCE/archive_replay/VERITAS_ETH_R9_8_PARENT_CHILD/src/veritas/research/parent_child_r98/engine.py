"""Bounded, depth-first packet recursion. Oracle values only accept or reject.

Scaled depth limits are an experimental termination policy. They do not supply
the source's decreasing-edge argument, and cannot enable SOURCE_QUALIFIED.
"""

from dataclasses import asdict
from itertools import product

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.extension_lagrange import (
    evaluate_polynomial,
    interpolate_newton,
)
from veritas.research.eth_interpolation.source_hermite import (
    make_source_tapered_plan,
    reconstruct_source_tapered,
)
from veritas.research.paper_verification.exact_parameters import hermite_parameters
from veritas.research.paper_verification.hermite_checker import (
    check_functional,
    recover_reference,
)
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.tapered_v4.provenance import source_binding
from veritas.research.tapered_v4.source_recipes import (
    EntryBudget,
    EntryLimits,
    compile_entry,
    evaluate_compiled,
)
from veritas.research.tapered_v4.source_state import SourceNode

from .constructor import construct_children
from .independent import (
    contract_independent,
    parent_point,
    reference_children,
    tuple_coefficient,
    verify_children,
)
from .model import (
    DEFAULT_POLICY,
    Budget,
    ExponentTuple,
    HermiteRecoveryCertificate,
    PointEvaluationCertificate,
    Refusal,
    Semantics,
    canonical,
    decode,
)
from .modes import TupleChecker, build_modes, verify_modes, weighted_tuples
from .packing import audit_layout, construct_layout, preconditions


def leaf(parent, budget):
    if parent.edge_count > budget.policy.max_edges:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "leaf edge cap")
    ring = JetRing(ExtensionRing(parent.precision, parent.defining_polynomial), 1)
    entries = EntryBudget(EntryLimits(max_work=100_000_000, max_seconds=60))
    compiled = [(v.ports, compile_entry(v.tensor, entries)) for v in parent.vertices]
    total = ring.zero
    for bits in product((0, 1), repeat=parent.edge_count):
        budget.tick()
        term = ring.one
        for ports, entry in compiled:
            term = ring.mul(
                term,
                evaluate_compiled(
                    entry, tuple(bits[p] for p in ports), parent.precision, entries
                ),
            )
            budget.tick(ring.base.e**2)
        total = ring.add(total, term)
    budget.tick(entries.used)
    return total


def _point_header(parent, layout, modes):
    return {
        "schema": "VERITAS_R98_POINT_V1",
        "parent_digest": parent.content_digest,
        "layout_digest": layout.content_digest,
        "modes_digest": modes.content_digest,
        "precision": modes.certificate["precision"],
        "semantics": parent.semantics.value,
        "paper": source_registry(),
        "source_qualified": False,
        "implementation_source_sha256": source_binding()["digest"],
    }


def evaluate_point(parent, layout, modes, *, budget, contractor=None, capture=False):
    verify_modes(parent, layout, modes, budget=budget)
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise Refusal(
            "INCONCLUSIVE_SOURCE_REFINEMENT",
            "active source refinement is not established",
        )
    m = modes.certificate
    ring = JetRing(ExtensionRing(m["precision"], parent.defining_polynomial), 1)
    checker = TupleChecker(modes, budget)
    total = ring.zero
    terms = []
    count = 0
    all_shrink = True
    for beta in weighted_tuples(modes, budget=budget):
        checker.accept(beta)
        children = construct_children(
            parent, layout, modes, beta, budget=budget, _admitted=True
        )
        verified = verify_children(
            parent, layout, modes, beta, children, budget=budget, _admitted=True
        )
        all_shrink &= verified["all_source_shrink"]
        term = ring.one
        groups = []
        for child, expected in zip(children, verified["values"]):
            budget.tick()
            call = child.as_parent(parent)
            if contractor is None:
                budget.call(call.depth)
                actual = leaf(call, budget)
            else:
                actual = contractor(call)
            if actual != expected:
                raise ValueError(
                    "generated child contraction disagrees with independent value"
                )
            term = ring.mul(term, actual)
            if capture:
                groups.append(
                    [child.group, child.edge_count, child.content_digest, actual]
                )
            budget.transitions += 1
            budget.nonshrinking += int(child.edge_count >= parent.edge_count)
        oracle = tuple_coefficient(parent, layout, modes, beta, budget=budget)
        if term != oracle:
            raise ValueError("one-tuple child product differs from parent coefficient")
        total = ring.add(total, term)
        count += 1
        budget.tuples += 1
        if capture:
            terms.append({"beta": list(beta.values), "groups": groups, "product": term})
            # Bound retained transcript incrementally, before adding another term.
            if (
                len(canonical(terms[-1])) * len(terms)
                > budget.policy.max_certificate_bytes
            ):
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT", "point transcript byte cap"
                )
    checker.finish()
    direct = parent_point(parent, layout, modes, budget=budget)
    if total != direct:
        raise ValueError(
            "complete child sum differs from independent half-edge elimination"
        )
    budget.points += 1
    cert = None
    if capture:
        payload = canonical(
            dict(_point_header(parent, layout, modes), terms=terms, result=total)
        )
        if len(payload) > budget.policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "point transcript byte cap")
        cert = PointEvaluationCertificate(payload)
    return (
        total,
        cert,
        {
            "status": "PASS_FINITE_SCALED_PARENT_CHILD_IDENTITY",
            "tuples": count,
            "child_count_per_tuple": 64,
            "all_source_shrink": all_shrink,
            "per_point_independent_oracle_status": "PASS_HALF_EDGE_FACTOR_ELIMINATION",
            "one_tuple_independent_oracle_status": "PASS_GLOBAL_FORMAL_COEFFICIENT",
            "creation_precision_inheritance": True,
            "source_qualified": False,
        },
    )


def verify_point_certificate(
    parent, layout, modes, certificate, *, policy=DEFAULT_POLICY
):
    """Consume submitted values using independent child generation and arithmetic."""
    budget = Budget(policy)
    try:
        verify_modes(parent, layout, modes, budget=budget)
        data = decode(certificate.payload, cap=policy.max_certificate_bytes)
        header = _point_header(parent, layout, modes)
        if set(data) != set(header) | {"terms", "result"} or any(
            canonical(data[k]) != canonical(v) for k, v in header.items()
        ):
            raise ValueError("point certificate header mismatch")
        m = modes.certificate
        from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic

        ar = ReferenceArithmetic(
            m["precision"], parent.defining_polynomial, 1, policy.max_work
        )
        checker = TupleChecker(modes, budget)
        total = ar.zero
        if type(data["terms"]) is not list or len(data["terms"]) != checker.expected:
            raise ValueError("incomplete point term inventory")
        for term in data["terms"]:
            if set(term) != {"beta", "groups", "product"}:
                raise ValueError("point term fields")
            beta = ExponentTuple(modes.content_digest, tuple(term["beta"]))
            checker.accept(beta)
            children = reference_children(parent, layout, modes, beta)
            checked = verify_children(
                parent, layout, modes, beta, children, budget=budget, _admitted=True
            )
            expected = [
                [c.group, c.edge_count, c.content_digest, v]
                for c, v in zip(children, checked["values"])
            ]
            if canonical(term["groups"]) != canonical(expected):
                raise ValueError("submitted child digest, order or value mismatch")
            value = ar.one
            for v in checked["values"]:
                value = ar.mul(value, v)
            if canonical(value) != canonical(
                term["product"]
            ) or value != tuple_coefficient(parent, layout, modes, beta, budget=budget):
                raise ValueError("submitted one-tuple product mismatch")
            total = ar.add(total, value)
        checker.finish()
        if total != parent_point(parent, layout, modes, budget=budget) or canonical(
            total
        ) != canonical(data["result"]):
            raise ValueError("submitted full point identity mismatch")
        budget.tick(ar.used)
        return {
            "status": "PASS_FINITE_SCALED_PARENT_CHILD_IDENTITY",
            "result": total,
            "tuples": checker.seen,
            "child_count_per_tuple": 64,
            "source_qualified": False,
        }
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ArithmeticError,
        RuntimeError,
        MemoryError,
    ) as exc:
        return {
            "status": getattr(exc, "status", "INVALID_POINT_CERTIFICATE"),
            "reason": str(exc),
        }


def recover_grid(parent, layout, point_rows, budget):
    """Recover from complete submitted point values with coefficientwise guards."""
    plan = make_source_tapered_plan(
        M=parent.edge_count,
        a=layout.a,
        u=layout.u,
        p=parent.precision,
        max_precision_bits=budget.policy.max_precision,
    )
    check_functional(plan)
    order = plan.degree_bound + 1
    if len(point_rows) != len(plan.nodes) * order:
        raise ValueError("incomplete Hermite point grid")
    jets, precisions = {}, {}
    offset = 0
    for node in plan.nodes:
        ring = ExtensionRing(node.precision_bits, parent.defining_polynomial)
        points = distinct_residue_points(ring, order, max_points=64)
        values = []
        for z in points:
            row = point_rows[offset]
            offset += 1
            if (row[0], tuple(row[1]), row[2]) != (node.t, z, node.precision_bits):
                raise ValueError("altered Hermite node, point order or precision")
            value = tuple(row[3])
            if len(value) != ring.e or any(
                type(v) is not int or not 0 <= v < ring.modulus for v in value
            ):
                raise ValueError("noncanonical point value")
            values.append(value)
        polynomial = interpolate_newton(ring, points, values, max_points=64)
        if any(
            evaluate_polynomial(ring, polynomial, z) != v
            for z, v in zip(points, values)
        ):
            raise ValueError("interpolation sample mismatch")
        count = min(node.multiplicity, order)
        jets[node.t] = polynomial[:count]
        precisions[node.t] = (node.precision_bits,) * count
        budget.tick(order**2 * ring.e**2)
    result = []
    for coordinate in range(parent.defining_polynomial.bit_length() - 1):
        data = {t: tuple(x[coordinate] for x in values) for t, values in jets.items()}
        value = reconstruct_source_tapered(
            plan, data, coefficient_precisions=precisions
        )
        if value != recover_reference(plan, data, precisions):
            raise ValueError("independent rational Hermite recovery mismatch")
        result.append(value)
    cert = HermiteRecoveryCertificate(
        canonical(
            {
                "schema": "VERITAS_R98_RECOVERY_V1",
                "parent_digest": parent.content_digest,
                "layout_digest": layout.content_digest,
                "point_rows": point_rows,
                "coefficient_precisions": {str(t): ps for t, ps in precisions.items()},
                "result": result,
                "guard_bits": plan.guard_bits,
                "degree_bound": plan.degree_bound,
                "functional_checked_on_all_monomials": True,
                "source_qualified": False,
            }
        )
    )
    return (tuple(result),), cert


def verify_recovery_certificate(parent, layout, certificate, *, policy=DEFAULT_POLICY):
    """Verify recovery bytes and every submitted point with a separate parent oracle.

    This checks finite values and coefficientwise recovery; it does not prove
    that a claimed recursive execution trace produced the submitted points.
    """
    budget = Budget(policy)
    try:
        data = decode(certificate.payload, cap=policy.max_certificate_bytes)
        rows = data["point_rows"]
        value, expected = recover_grid(parent, layout, rows, budget)
        if expected.payload != certificate.payload:
            raise ValueError("recovery metadata, coefficients or result changed")
        for node, zeta, _, claimed in rows:
            modes = build_modes(parent, layout, node, tuple(zeta), budget=budget)
            if parent_point(parent, layout, modes, budget=budget) != (tuple(claimed),):
                raise ValueError(
                    "recovery point differs from independent parent oracle"
                )
        return {
            "status": "PASS_FINITE_SCALED_HERMITE_RECOVERY",
            "result": value,
            "points_checked": len(rows),
            "source_qualified": False,
            "recursive_trace_verified": False,
        }
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ArithmeticError,
        RuntimeError,
        MemoryError,
    ) as exc:
        return {
            "status": getattr(exc, "status", "INVALID_RECOVERY_CERTIFICATE"),
            "reason": str(exc),
        }


def contract_scaled(
    parent, *, levels=1, a=2, u=1, strategy="canonical", policy=DEFAULT_POLICY
):
    budget = Budget(policy)
    try:
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise ValueError("explicit finite scaled parent required")
        implementation = source_binding()["digest"]
        if (
            type(levels) is not int
            or not 0 <= levels <= policy.max_depth - parent.depth
        ):
            raise ValueError("invalid finite recursion depth")
        leaf_depth = parent.depth + levels
        root_recovery = None
        packing_reports = []

        def visit(call):
            nonlocal root_recovery
            budget.call(call.depth)
            if call.depth == leaf_depth or call.edge_count == 0:
                return leaf(call, budget)
            if call.edge_count > policy.max_edges:
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT", "recursive parent edge cap"
                )
            layout = construct_layout(call, a=a, u=u, strategy=strategy, budget=budget)
            if call.depth == parent.depth:
                packing_reports.append(audit_layout(call, layout))
            parameters = hermite_parameters(call.edge_count, a, u, call.precision)
            if any(n[-1] > policy.max_precision for n in parameters["nodes"]):
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT", "recursive point precision cap"
                )
            if parameters["degree_bound"] + 1 > min(
                64, 1 << (call.defining_polynomial.bit_length() - 1)
            ):
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT",
                    "insufficient residue-distinct interpolation points",
                )
            plan = make_source_tapered_plan(
                M=call.edge_count,
                a=a,
                u=u,
                p=call.precision,
                max_precision_bits=policy.max_precision,
            )
            check_functional(plan)
            rows = []
            for node in plan.nodes:
                ring = ExtensionRing(node.precision_bits, call.defining_polynomial)
                for z in distinct_residue_points(
                    ring, plan.degree_bound + 1, max_points=64
                ):
                    budget.tick()
                    modes = build_modes(call, layout, node.t, z, budget=budget)
                    value, _, _ = evaluate_point(
                        call, layout, modes, budget=budget, contractor=visit
                    )
                    rows.append([node.t, list(z), node.precision_bits, list(value[0])])
            value, recovery = recover_grid(call, layout, rows, budget)
            if value != contract_independent(call, budget):
                raise ValueError(
                    "recovered parent differs from independent original contraction"
                )
            if call.depth == parent.depth:
                root_recovery = recovery
            return value

        value = visit(parent)
        return {
            "status": "PASS_FINITE_SCALED_PARENT_CHILD_IDENTITY",
            "result": value,
            "semantics": parent.semantics.value,
            "source_eligible": False,
            "scaled_experiment": True,
            "theorem_mode_enabled": False,
            "source_qualified": False,
            "parent_digest": parent.content_digest,
            "implementation_source_sha256": implementation,
            "paper": source_registry(),
            "policy": asdict(policy),
            "packing": packing_reports,
            "hermite_recovery": None
            if root_recovery is None
            else decode(root_recovery.payload),
            "per_point_independent_oracle_status": "PASS_HALF_EDGE_FACTOR_ELIMINATION"
            if budget.points
            else "NOT_RUN_LEAF",
            "creation_precision_inheritance": True,
            "mode_completeness": "INDEPENDENT_BASIS_EQUALITY"
            if budget.points
            else "NOT_RUN_LEAF",
            "tuple_completeness": "COMPLETE_WEIGHTED_STREAM"
            if budget.points
            else "NOT_RUN_LEAF",
            "child_count_per_tuple": 64 if budget.points else None,
            "hermite_coefficient_precision": "COEFFICIENTWISE_CHECKED"
            if root_recovery
            else "NOT_RUN_LEAF",
            "source_refinement_proven": False,
            "ledger": budget.report(),
        }
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ArithmeticError,
        RuntimeError,
        MemoryError,
    ) as exc:
        return {
            "status": getattr(exc, "status", "INCONCLUSIVE_SCALED_RECURSION"),
            "reason": str(exc),
            "source_qualified": False,
            "theorem_mode_enabled": False,
            "ledger": budget.report(),
        }


def contract_source(node, parent_context=None, policy=DEFAULT_POLICY):
    """Source leaf execution stays distinct from bounded scaled recursion."""
    from veritas.research.tapered_v4.source_leaf import contract_source_leaf

    from .model import from_source

    try:
        if type(node) is not SourceNode or (
            parent_context is not None and node.context != parent_context
        ):
            raise ValueError("source node/root context mismatch")
        if node.edge_count <= node.context.leaf_threshold:
            return contract_source_leaf(node)
        parent = from_source(node)
        numeric = preconditions(parent)
        if numeric["status"] != "NUMERIC_PRECONDITIONS_MET":
            raise Refusal(
                numeric["status"],
                "source active schedule/packing preconditions unavailable",
            )
        raise Refusal(
            "INCONCLUSIVE_SOURCE_REFINEMENT",
            "universal recursive refinement and proof requirements remain open",
        )
    except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
        return {
            "status": getattr(exc, "status", "INVALID_SOURCE_CALL"),
            "reason": str(exc),
            "theorem_mode_enabled": False,
            "source_qualified": False,
        }
