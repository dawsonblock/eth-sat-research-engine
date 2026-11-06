"""Actual shrinking packet recursion on a certified constant-deformation family.

This is an explicitly scaled a=u=1 implementation. Every active call proves
that its row tensors are constant on Boolean inputs. Summing its Y variables
then proves degree zero for its deformation, so the complete jets at -1 and
+1 consist of the recursively computed constant and an exact zero tail.
It does not certify arbitrary source-regime inputs or asymptotic complexity.
"""

from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
from math import prod

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_interpolation.cauchy_product import cauchy_point_value
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.tapered_v4.provenance import source_binding

from .constructor import construct_children
from .engine import leaf
from .independent import verify_children
from .model import Budget, ModeSet, Policy, Refusal, Semantics, canonical
from .modes import TupleChecker, weighted_tuples
from .shrinking_layout import (
    audit_vertex_shrinking_layout as audit_shrinking_layout,
    construct_vertex_shrinking_layout as construct_shrinking_layout,
)
from .shrinking_oracle import (
    certify_constant_deformation,
    parent_point,
    tuple_coefficient,
)


LEAF_EDGES = 4
DEFAULT_SHRINKING_POLICY = Policy(
    max_edges=1024,
    max_precision=65536,
    max_work=300_000_000,
    max_depth=16,
    max_seconds=600,
)


def _zero_node_certificate(parent, layout, node, budget):
    audit_shrinking_layout(parent, layout)
    if type(node) is not int or node not in (-1, 1):
        raise ValueError("shrinking recurrence requires both odd L=2 nodes")
    if (layout.a, layout.u) != (1, 1):
        raise ValueError("constant-family recurrence uses a=u=1")
    precision = parent.precision + 64 * parent.edge_count
    if precision > budget.policy.max_precision:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "shrinking point precision cap")
    src = layout.source
    # A singleton's row/column slot agrees even when endpoint groups differ.
    # At L=B=2, y0=y, so its geometric denominator is the odd node itself.
    # Every target coefficient therefore contains the exact factor W_xx(t)=0.
    cross_pairs = []
    for packet in src["packets"]:
        budget.tick()
        if len(packet["occupied_slots"]) != 1:
            raise ValueError("degree-zero point basis requires singleton packets")
        slot, edge = packet["occupied_slots"][0]
        row, col = src["edges"][edge]
        if type(slot) is not int or slot not in (0, 1):
            raise ValueError("point basis requires a real L=2 singleton slot")
        if src["row_labels"][str(row)] != src["column_labels"][str(col)]:
            cross_pairs.append([edge, edge])
    # C(T)/T divided by C'(0), with C(T)=T(T+2)(T+1)(T-1).
    # Exact rational evaluation is separate from production ring arithmetic.
    exact = Fraction(prod(node - q for q in (-2, -1, 1)), prod(-q for q in (-2, -1, 1)))
    if exact != 0:
        raise ValueError("integer-node diagonal Cauchy coefficient is nonzero")
    degree = parent.defining_polynomial.bit_length() - 1
    return {
        "d3_certificate": src,
        "node": node,
        "precision": precision,
        "jet_length": 1,
        "extension_degree": degree,
        "irreducible_polynomial": parent.defining_polynomial,
        "zeta": [0] * degree,
        "local": [],
        "cross_pairs": sorted(cross_pairs),
        "modes": [],
        "mode_tuple_count": 1,
    }


def verify_zero_node_modes(parent, layout, modes, *, budget):
    """Check complete real interactions and the empty retained mode basis."""
    if modes.layout_digest != layout.content_digest:
        raise ValueError("shrinking point layout binding mismatch")
    record = modes.certificate
    expected = _zero_node_certificate(parent, layout, record["node"], budget)
    if canonical(record) != canonical(expected):
        raise ValueError("altered or incomplete constant-family point modes")
    return {
        "mode_completeness": "EXACT_SINGLETON_CAUCHY_AND_GROUP_CHECK",
        "weighted_tuple_count": 1,
        "mode_basis_scope": "ZERO_REDUCED_GEOMETRIC_POINT_MODES",
        "tuple_domain": "ALL_WEIGHTED_TUPLES_OVER_RETAINED_MODES",
        "paper_formal_mode_domain_enumerated": False,
    }


def build_zero_node_modes(parent, layout, node, *, budget):
    record = _zero_node_certificate(parent, layout, node, budget)
    ring = ExtensionRing(
        record["precision"],
        parent.defining_polynomial,
        max_precision_bits=budget.policy.max_precision,
    )
    for slot in (0, 1):
        coefficient = cauchy_point_value(
            2, node, ring, slot, slot, tuple(record["zeta"])
        )
        if coefficient != ring.zero:
            raise ValueError("production Cauchy evaluation disagrees with exact zero")
    modes = ModeSet(layout.content_digest, canonical(record))
    verify_zero_node_modes(parent, layout, modes, budget=budget)
    return modes


def _value_digest(value):
    # Hex avoids imposing decimal-string serialization limits on high-precision
    # intermediate residues; the value itself is still computed exactly.
    return sha256(canonical([[hex(x) for x in row] for row in value])).hexdigest()


def recover_constant_points(parent, certificate, points, *, budget):
    """Recover degree-zero jets, after independently rechecking their premise.

    The point values must come from recursion. The certificate supplies only a
    degree bound; it contains no contraction value that could replace a failure.
    """
    expected = certify_constant_deformation(parent, budget=budget)
    if (
        canonical(certificate) != canonical(expected)
        or certificate["degree_bound"] != 0
    ):
        raise ValueError("constant-deformation certificate differs from parent")
    if (
        type(points) is not dict
        or any(type(node) is not int for node in points)
        or set(points) != {-1, 1}
    ):
        raise ValueError("both complete degree-zero Hermite nodes are required")
    precision = parent.precision + 64 * parent.edge_count
    degree = parent.defining_polynomial.bit_length() - 1
    for value in points.values():
        if (
            type(value) is not tuple
            or len(value) != 1
            or type(value[0]) is not tuple
            or len(value[0]) != degree
            or any(type(x) is not int or not 0 <= x < 1 << precision for x in value[0])
        ):
            raise ValueError("noncanonical recursively computed point value")
    if points[-1] != points[1]:
        raise ValueError("recursively computed constant-deformation points disagree")
    # For the independently proved degree-zero polynomial all j>=1 coefficients
    # vanish exactly. Therefore evaluation at zero is its constant coefficient;
    # this specialized Hermite recovery loses no bits or rational denominators.
    modulus = 1 << parent.precision
    value = (tuple(x % modulus for x in points[-1][0]),)
    return value, {
        "parent_digest": parent.content_digest,
        "degree_certificate": certificate,
        "nodes": [-1, 1],
        "point_precision": precision,
        "coefficients_per_node": 3 * parent.edge_count,
        "constant_coefficients_checked_equal": True,
        "zero_tail": "EXACT_FROM_INDEPENDENT_DEGREE_ZERO_CERTIFICATE",
        "coefficient_precision": "POINT_PRECISION_FOR_CONSTANT_EXACT_FOR_ZERO_TAIL",
        "point_value_sha256": _value_digest(points[-1]),
        "result_sha256": _value_digest(value),
        "source_qualified": False,
    }


def contract_shrinking(parent, *, policy=DEFAULT_SHRINKING_POLICY):
    """Recurse on generated children only after enforcing the actual shrink.

    Depth is a refusal budget, never a successful leaf condition. Every one of
    the 64 children is evaluated on each complete point, including empty units.
    """
    budget = Budget(policy)
    trace, recoveries, edge_layers = [], [], {}
    active_calls = 0
    evidence_bytes = 0
    maximal_precision = parent.precision
    try:
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise ValueError("explicit finite scaled shrinking semantics required")
        degree_limit = max(parent.maximum_degree, 4)
        implementation_digest = source_binding()["digest"]

        def retain(collection, record):
            nonlocal evidence_bytes
            size = len(canonical(record))
            if evidence_bytes + size > budget.policy.max_certificate_bytes:
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT", "shrinking evidence byte cap"
                )
            evidence_bytes += size
            collection.append(record)

        def visit(call):
            nonlocal active_calls, maximal_precision
            budget.call(call.depth)
            maximal_precision = max(maximal_precision, call.precision)
            edge_layers.setdefault(call.depth, set()).add(call.edge_count)
            if call.edge_count > budget.policy.max_edges:
                raise Refusal(
                    "INCONCLUSIVE_RESOURCE_LIMIT", "shrinking parent edge cap"
                )
            if call.maximum_degree > degree_limit:
                raise ValueError("recursive degree invariant failed")
            if call.edge_count <= LEAF_EDGES:
                return leaf(call, budget)
            active_calls += 1
            certificate = certify_constant_deformation(call, budget=budget)
            layout = construct_shrinking_layout(call, budget=budget)
            layout_report = audit_shrinking_layout(call, layout)
            points = {}
            for node in (-1, 1):
                modes = build_zero_node_modes(call, layout, node, budget=budget)
                maximal_precision = max(
                    maximal_precision, modes.certificate["precision"]
                )
                verify_zero_node_modes(call, layout, modes, budget=budget)
                checker = TupleChecker(modes, budget)
                ring = JetRing(
                    ExtensionRing(
                        modes.certificate["precision"],
                        call.defining_polynomial,
                        max_precision_bits=budget.policy.max_precision,
                    ),
                    1,
                )
                total = ring.zero
                for beta in weighted_tuples(modes, budget=budget):
                    checker.accept(beta)
                    children = construct_children(
                        call,
                        layout,
                        modes,
                        beta,
                        budget=budget,
                        _admitted=True,
                        require_shrink=True,
                    )
                    # Inspect actual graph measures before recursing into ANY
                    # child. Predicted loads and a copied digest are insufficient.
                    if len(children) != 64 or tuple(c.group for c in children) != tuple(
                        range(64)
                    ):
                        raise ValueError(
                            "exactly 64 ordered shrinking children required"
                        )
                    for child in children:
                        budget.tick()
                        if (
                            64 * child.edge_count > 6 * call.edge_count
                            or child.edge_count >= call.edge_count
                        ):
                            raise Refusal(
                                "INCONCLUSIVE_CHILD_SHRINK",
                                "actual child violates 64*M_child<=6*M",
                            )
                        if (
                            max((len(v.ports) for v in child.vertices), default=0)
                            > degree_limit
                        ):
                            raise ValueError(
                                "actual child exceeds fixed degree invariant"
                            )
                    verified = verify_children(
                        call,
                        layout,
                        modes,
                        beta,
                        children,
                        budget=budget,
                        _admitted=True,
                    )
                    if (
                        len(verified["values"]) != 64
                        or not verified["all_source_shrink"]
                    ):
                        raise ValueError("independent actual child shrink disagrees")
                    value = ring.one
                    for child, expected in zip(children, verified["values"]):
                        actual = visit(child.as_parent(call))
                        if actual != expected:
                            raise ValueError(
                                "recursive child differs from independent child contraction"
                            )
                        value = ring.mul(value, actual)
                        budget.transitions += 1
                    oracle = tuple_coefficient(call, layout, modes, beta, budget=budget)
                    if value != oracle:
                        raise ValueError(
                            "shrinking child product differs from independent coefficient"
                        )
                    total = ring.add(total, value)
                    budget.tuples += 1
                    retain(
                        trace,
                        {
                            "parent_digest": call.content_digest,
                            "depth": call.depth,
                            "parent_edges": call.edge_count,
                            "node": node,
                            "child_edges": [c.edge_count for c in children],
                            "child_count": 64,
                            "actual_child_shrink": "PASS_64_M_CHILD_LE_6_M",
                            "actual_child_degree": "PASS_FIXED_DEGREE_INVARIANT",
                            "group_load_bound_met": layout_report[
                                "group_load_bound_met"
                            ],
                            "point_sha256": _value_digest(value),
                        },
                    )
                checker.finish()
                if total != parent_point(call, layout, modes, budget=budget):
                    raise ValueError(
                        "complete shrinking point differs from independent half-edge elimination"
                    )
                budget.points += 1
                points[node] = total
            value, recovery = recover_constant_points(
                call, certificate, points, budget=budget
            )
            retain(recoveries, recovery)
            return value

        value = visit(parent)
        report = {
            "status": "PASS_FINITE_SCALED_SHRINKING_RECURSION"
            if active_calls
            else "PASS_FINITE_SCALED_LEAF",
            "result": value,
            "semantics": parent.semantics.value,
            "family": "ROW_CONSTANT_AT_EVERY_ACTIVE_CALL",
            "packing_family": "VERTEX_DEGREES_FIT_PER_SIDE_GROUP_LOAD_CAPACITY",
            "scaled_experiment": True,
            "source_eligible": False,
            "source_qualified": False,
            "theorem_mode_enabled": False,
            "parent_digest": parent.content_digest,
            "implementation_source_sha256": implementation_digest,
            "paper": source_registry(),
            "policy": asdict(policy),
            "leaf_threshold": LEAF_EDGES,
            "termination": "STRICT_EDGE_DECREASE_TO_LEAF_THRESHOLD",
            "active_calls": active_calls,
            "maximal_precision_used": maximal_precision,
            "child_count_per_tuple": 64 if active_calls else None,
            "mode_completeness": "EXACT_SINGLETON_CAUCHY_AND_GROUP_CHECK"
            if active_calls
            else "NOT_RUN_LEAF",
            "tuple_completeness": "COMPLETE_WEIGHTED_STREAM"
            if active_calls
            else "NOT_RUN_LEAF",
            "per_point_independent_oracle_status": "PASS_INDEPENDENT_HALF_EDGE_ELIMINATION"
            if active_calls
            else "NOT_RUN_LEAF",
            "one_tuple_independent_oracle_status": "PASS_INDEPENDENT_POLYNOMIAL_FACTOR_ELIMINATION"
            if active_calls
            else "NOT_RUN_LEAF",
            "creation_precision_inheritance": True,
            "hermite_coefficient_precision": "CONSTANT_AT_POINT_PRECISION_ZERO_TAIL_EXACT"
            if active_calls
            else "NOT_RUN_LEAF",
            "fixed_degree_limit": degree_limit,
            "actual_child_shrink": "PASS_64_M_CHILD_LE_6_M"
            if active_calls
            else "NOT_RUN_LEAF",
            "edge_layers": {
                str(d): sorted(ms) for d, ms in sorted(edge_layers.items())
            },
            "transitions": trace,
            "hermite_recoveries": recoveries,
            "interpolation": "CERTIFIED_DEGREE_ZERO_TWO_NODE_RECOVERY",
            "source_refinement_proven": False,
            "ledger": budget.report(),
        }
        if len(canonical(report)) > policy.max_certificate_bytes:
            raise Refusal(
                "INCONCLUSIVE_RESOURCE_LIMIT", "complete shrinking report byte cap"
            )
        return report
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
            "status": getattr(exc, "status", "INCONCLUSIVE_SHRINKING_RECURSION"),
            "reason": str(exc),
            "source_qualified": False,
            "theorem_mode_enabled": False,
            "active_calls": active_calls,
            "ledger": budget.report(),
        }
