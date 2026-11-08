"""Complete finite singleton-packet recursion with general tensor entries.

Every active call uses the full degree bound and complete weighted tuple set.
Limits refuse the computation; they never introduce an oracle answer or a leaf.
This implements a bounded scaled recurrence, not source-regime qualification.
"""

from dataclasses import asdict

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.paper_verification.source_registry import source_registry
from veritas.research.tapered_v4.provenance import source_binding

from .constructor import construct_children
from .engine import leaf
from .general_modes import build_general_modes
from .general_recovery import make_general_plan, general_points, recover_general_grid
from .group_preflight import preflight_group_recursion
from .independent import verify_children
from .model import Budget, Refusal, Semantics, canonical, decode
from .modes import TupleChecker, weighted_tuples
from .shrinking_engine import DEFAULT_SHRINKING_POLICY, LEAF_EDGES, _value_digest
from .shrinking_layout import construct_vertex_shrinking_layout, audit_vertex_shrinking_layout
from .shrinking_oracle import contract_independent, parent_point, tuple_coefficient


def contract_general_shrinking(parent, *, policy=DEFAULT_SHRINKING_POLICY, max_points=256, groups=64):
    """Recurse on all configured children at every point and retained tuple.

    General entries are admitted, subject to actual packing and complete-work
    budgets at every depth. The immutable defining polynomial is never changed.
    """
    budget = Budget(policy)
    transitions, recoveries, edge_layers = [], [], {}
    active_calls = evidence_bytes = 0
    maximal_precision = parent.precision
    try:
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise ValueError("explicit finite scaled general semantics required")
        if type(max_points) is not int or not 1 <= max_points <= 4096:
            raise ValueError("general interpolation point cap must be 1..4096")
        if parent.defining_polynomial.bit_length() - 1 > 12:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general extension degree cap")
        implementation = source_binding()["digest"]
        degree_limit = max(parent.maximum_degree, 4)
        topology_plan = preflight_group_recursion(parent, groups=groups, budget=budget, general=True)
        preflight_report = topology_plan.report()
        evidence_bytes = len(canonical(preflight_report))

        def retain(collection, record):
            nonlocal evidence_bytes
            size = len(canonical(record))
            if evidence_bytes + size > policy.max_certificate_bytes:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general evidence byte cap")
            evidence_bytes += size
            collection.append(record)

        def visit(call):
            nonlocal active_calls, maximal_precision
            budget.call(call.depth)
            edge_layers.setdefault(call.depth, set()).add(call.edge_count)
            maximal_precision = max(maximal_precision, call.precision)
            if call.edge_count > policy.max_edges or call.precision > policy.max_precision:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "general node dimensions exceed policy")
            if call.maximum_degree > degree_limit:
                raise ValueError("general recursive degree invariant failed")
            if call.edge_count <= LEAF_EDGES:
                return leaf(call, budget)
            active_calls += 1
            layout = construct_vertex_shrinking_layout(call, budget=budget, groups=groups)
            packing = audit_vertex_shrinking_layout(call, layout)
            plan = make_general_plan(call, budget=budget, max_points=max_points)
            # Even a mode-free point invokes every configured child.
            lower_calls = len(plan.nodes) * (plan.degree_bound + 1) * groups
            if budget.calls + lower_calls > policy.max_calls:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete grid exceeds remaining call budget")
            rows, row_bytes = [], 0
            for node, zeta, precision in general_points(call, plan, budget=budget, max_points=max_points):
                budget.tick()
                maximal_precision = max(maximal_precision, precision)
                modes = build_general_modes(call, layout, node, zeta, budget=budget)
                checker = TupleChecker(modes, budget)
                if budget.calls + groups * checker.expected > policy.max_calls:
                    raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete point exceeds remaining call budget")
                ring = JetRing(ExtensionRing(precision, call.defining_polynomial,
                                              max_precision_bits=policy.max_precision), 1)
                total = ring.zero
                for beta in weighted_tuples(modes, budget=budget):
                    checker.accept(beta)
                    children = construct_children(call, layout, modes, beta, budget=budget,
                                                  _admitted=True, require_shrink=True)
                    if len(children) != groups or tuple(c.group for c in children) != tuple(range(groups)):
                        raise ValueError(f"exactly {groups} ordered children required")
                    # All children must pass before any one of them is invoked.
                    for child in children:
                        budget.tick()
                        if groups * child.edge_count > 6 * call.edge_count or child.edge_count >= call.edge_count:
                            raise Refusal("INCONCLUSIVE_CHILD_SHRINK", "actual child violates strict shrinking bound")
                        if max((len(v.ports) for v in child.vertices), default=0) > degree_limit:
                            raise ValueError("actual child exceeds fixed degree invariant")
                    topology_plan.verify_children(call, children, budget=budget)
                    verified = verify_children(call, layout, modes, beta, children,
                                               budget=budget, _admitted=True)
                    if len(verified["values"]) != groups or not verified["all_group_shrink"]:
                        raise ValueError("independent child inventory or shrink mismatch")
                    term = ring.one
                    for child, expected in zip(children, verified["values"]):
                        actual = visit(child.as_parent(call))
                        if actual != expected:
                            raise ValueError("recursive child differs from independent contraction")
                        term = ring.mul(term, actual)
                        budget.transitions += 1
                    if term != tuple_coefficient(call, layout, modes, beta, budget=budget):
                        raise ValueError("child product differs from independent parent coefficient")
                    total = ring.add(total, term)
                    budget.tuples += 1
                    retain(transitions, {
                        "parent_digest": call.content_digest, "depth": call.depth,
                        "parent_edges": call.edge_count, "node": node, "zeta": list(zeta),
                        "point_precision": precision, "beta": list(beta.values),
                        "modes_digest": modes.content_digest, "child_count": groups,
                        "group_count": groups,
                        "child_edges": [c.edge_count for c in children],
                        "actual_child_shrink": f"PASS_{groups}_M_CHILD_LE_6_M",
                        "cross_group_pairs": len(modes.certificate["cross_pairs"]),
                        "retained_modes": len(modes.certificate["modes"]),
                        "complete_tuple_count": modes.certificate["mode_tuple_count"],
                        "group_load_bound_met": packing["group_load_bound_met"],
                        "source_padded_packet_bound_met": packing["packet_bound_met"],
                        "term_sha256": _value_digest(term),
                    })
                checker.finish()
                if total != parent_point(call, layout, modes, budget=budget, max_extension_degree=12):
                    raise ValueError("complete point differs from independent half-edge elimination")
                budget.points += 1
                row = [node, list(zeta), precision, list(total[0])]
                row_bytes += len(canonical(row))
                if row_bytes + evidence_bytes > policy.max_certificate_bytes:
                    raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete grid evidence byte cap")
                rows.append(row)
            value, certificate = recover_general_grid(call, layout, rows, budget=budget,
                                                      max_points=max_points)
            if value != contract_independent(call, budget):
                raise ValueError("recovered parent differs from independent original contraction")
            retain(recoveries, decode(certificate.payload, cap=policy.max_certificate_bytes))
            return value

        value = visit(parent)
        if source_binding()["digest"] != implementation:
            raise ValueError("implementation source changed during execution")
        report = {
            "status": "PASS_FINITE_SCALED_GENERAL_SHRINKING_RECURSION" if active_calls else "PASS_FINITE_SCALED_LEAF",
            "result": value, "semantics": parent.semantics.value,
            "family": "GENERAL_TENSORS_WITH_COMPLETE_GRID_AND_TUPLE_BUDGETS",
            "scaled_experiment": True, "source_eligible": False,
            "source_qualified": False, "theorem_mode_enabled": False,
            "parent_digest": parent.content_digest, "implementation_source_sha256": implementation,
            "paper": source_registry(), "policy": asdict(policy), "max_interpolation_points": max_points,
            "finite_group_count": groups, "source_group_count": 64,
            "group_preflight": preflight_report,
            "leaf_threshold": LEAF_EDGES, "termination": "STRICT_EDGE_DECREASE_TO_LEAF_THRESHOLD",
            "active_calls": active_calls, "maximal_precision_used": maximal_precision,
            "child_count_per_tuple": groups if active_calls else None,
            "mode_completeness": "INDEPENDENT_SINGLETON_CAUCHY_BASIS" if active_calls else "NOT_RUN_LEAF",
            "tuple_completeness": "COMPLETE_WEIGHTED_STREAM" if active_calls else "NOT_RUN_LEAF",
            "per_point_independent_oracle_status": "PASS_INDEPENDENT_HALF_EDGE_ELIMINATION" if active_calls else "NOT_RUN_LEAF",
            "one_tuple_independent_oracle_status": "PASS_INDEPENDENT_POLYNOMIAL_FACTOR_ELIMINATION" if active_calls else "NOT_RUN_LEAF",
            "creation_precision_inheritance": True,
            "hermite_coefficient_precision": "FULL_GRID_COEFFICIENTWISE_CHECKED" if active_calls else "NOT_RUN_LEAF",
            "actual_child_shrink": f"PASS_{groups}_M_CHILD_LE_6_M" if active_calls else "NOT_RUN_LEAF",
            "fixed_degree_limit": degree_limit,
            "edge_layers": {str(d): sorted(ms) for d, ms in sorted(edge_layers.items())},
            "transitions": transitions, "hermite_recoveries": recoveries,
            "interpolation": "COMPLETE_DEGREE_BOUND_GRID_RATIONAL_HERMITE",
            "source_refinement_proven": False, "ledger": budget.report(),
        }
        if len(canonical(report)) > policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete general report byte cap")
        return report
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {
            "status": getattr(exc, "status", "INCONCLUSIVE_GENERAL_SHRINKING_RECURSION"),
            "reason": str(exc), "source_qualified": False, "theorem_mode_enabled": False,
            "active_calls": active_calls, "ledger": budget.report(),
            "group_preflight": getattr(exc, "report", None),
        }
