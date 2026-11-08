"""General bounded packet execution. Production values come only from children.

Source qualification is deliberately unavailable. Independent exponential
oracles are confined to verify_packet_term and external bounded validation.
"""
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.independent import reference_children, verify_children
from veritas.research.parent_child_r98.model import Budget, DEFAULT_POLICY, Refusal, Semantics, canonical
from veritas.research.parent_child_r98.modes import TupleChecker, weighted_tuples
from veritas.research.parent_child_r98.packing import audit_layout, construct_layout
from veritas.research.parent_child_r98.shrinking_oracle import tuple_coefficient
from veritas.research.paper_verification.exact_parameters import hermite_parameters
from veritas.research.tapered_v4.provenance import source_binding
from .basis import build_packet_modes, verify_packet_modes
from .recovery import make_packet_plan, packet_points, recover_packet_grid
from .preflight import preflight_packet_recursion, verify_projected_children
from .execution import ExecutionSpec, TupleStrategy


def _topology(parent, layout, modes, beta, children, budget, require_shrink):
    verify_projected_children(parent, layout, modes, children, budget=budget)
    # Independent construction semantics, without evaluating any tensor value.
    expected = reference_children(parent, layout, modes, beta)
    budget.tick(64 + 2 * parent.edge_count)
    if len(children) != 64 or children != expected:
        raise ValueError("independent child topology or immutable recipe mismatch")
    for child in children:
        if require_shrink and (64 * child.edge_count > 6 * parent.edge_count or
                               child.edge_count >= parent.edge_count):
            raise Refusal("INCONCLUSIVE_CHILD_SHRINK", "actual group child does not shrink")
        if max((len(v.ports) for v in child.vertices), default=0) > max(parent.maximum_degree, 2 << layout.a):
            raise ValueError("packet degree bound failed")


def evaluate_packet_point(parent, layout, modes, *, budget, contractor=None, require_shrink=False):
    """Full weighted sum; no structural or binary tuple pruning.

    The optional contractor is the recursive engine, never an oracle. Direct
    point calls only contract children with at most four actual edges.
    """
    verify_packet_modes(parent, layout, modes, budget=budget)
    checker = TupleChecker(modes, budget)  # refuses the entire point before calls
    if budget.calls + 64 * checker.expected > budget.policy.max_calls:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete point call lower bound")
    m = modes.certificate
    ring = JetRing(ExtensionRing(m["precision"], parent.defining_polynomial, max_precision_bits=budget.policy.max_precision), 1)
    total = ring.zero
    for beta in weighted_tuples(modes, budget=budget):
        checker.accept(beta)
        children = construct_children(parent, layout, modes, beta, budget=budget,
                                      _admitted=True, require_shrink=require_shrink)
        _topology(parent, layout, modes, beta, children, budget, require_shrink)
        if contractor is None and any(c.edge_count > 4 for c in children):
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "point requires recursive non-leaf contractor")
        term = ring.one
        for child in children:
            call = child.as_parent(parent)
            if contractor is None:
                budget.call(call.depth)
                value = leaf(call, budget)
            else:
                value = contractor(call)
            term = ring.mul(term, value)
            budget.tick(ring.base.e**2)
            budget.transitions += 1
        total = ring.add(total, term)
        budget.tuples += 1
    checker.finish()
    budget.points += 1
    return total


def verify_packet_term(parent, layout, modes, beta, children, claimed, *, budget):
    """Standalone fixed-beta finite boundary, not a complete-point certificate."""
    try:
        verify_packet_modes(parent, layout, modes, budget=budget)
        e = parent.defining_polynomial.bit_length() - 1
        if (type(claimed) is not tuple or len(claimed) != 1 or
            type(claimed[0]) is not tuple or len(claimed[0]) != e or
            any(type(x) is not int or not 0 <= x < 1 << modes.certificate["precision"] for x in claimed[0])):
            raise ValueError("noncanonical claimed coefficient")
        verdict = verify_children(parent, layout, modes, beta, children, budget=budget, _admitted=True)
        ring = JetRing(ExtensionRing(modes.certificate["precision"], parent.defining_polynomial, max_precision_bits=budget.policy.max_precision), 1)
        value = ring.one
        for child_value in verdict["values"]:
            value = ring.mul(value, child_value)
        if claimed != value or value != tuple_coefficient(parent, layout, modes, beta, budget=budget):
            raise ValueError("child product or independent parent coefficient mismatch")
        return {"status": "PASS_FINITE_GENERAL_PACKET_COEFFICIENT", "result": value,
                "child_count": 64, "all_source_shrink": verdict["all_source_shrink"],
                "complete_point_verified": False, "source_qualified": False}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {"status": getattr(exc, "status", "INVALID_GENERAL_PACKET_TERM"), "reason": str(exc),
                "source_qualified": False}


def contract_packet_recursion(parent, *, schedule=((2, 1),), layout_factory=None, policy=DEFAULT_POLICY,
                              max_points=256, point_strategy='complete_weighted'):
    """Depth-first finite general packets with edge-only successful leaves.

    schedule is an explicit finite sequence of (a,u), not a source schedule.
    A layout factory may supply audited packet data, never contraction values.
    Exhausted schedule, depth, arithmetic, tuples or evidence returns no result.
    The present independent arithmetic/grid limits restrict this prototype.
    """
    budget = Budget(policy)
    recoveries, transitions = [], []
    evidence_bytes = 0
    binding = source_binding()["digest"]
    try:
        if point_strategy not in ('complete_weighted', 'certified_support'):
            raise ValueError('unknown finite packet point strategy')
        if type(max_points) is not int or not 1 <= max_points <= 4096:
            raise ValueError('packet interpolation point cap must be 1..4096')
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise Refusal("INCONCLUSIVE_SOURCE_REFINEMENT", "source execution remains separately gated")
        if (type(schedule) is not tuple or not schedule or len(schedule) > policy.max_depth or
            any(type(pair) is not tuple or len(pair) != 2 or
                any(type(x) is not int for x in pair) or not 1 <= pair[1] <= pair[0] <= 3
                for pair in schedule)):
            raise ValueError("explicit bounded finite schedule required")

        def retain(destination, record):
            nonlocal evidence_bytes
            evidence_bytes += len(canonical(record))
            if evidence_bytes > policy.max_certificate_bytes:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "recursive evidence cap")
            destination.append(record)

        def visit(call):
            budget.call(call.depth)
            if call.edge_count > policy.max_edges or call.precision > policy.max_precision:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "recursive dimensions exceed policy")
            if call.edge_count <= 4:
                return leaf(call, budget)
            depth = call.depth - parent.depth
            if depth >= len(schedule):
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "finite schedule exhausted above leaf threshold")
            a, u = schedule[depth]
            layout = (construct_layout(call, a=a, u=u, budget=budget) if layout_factory is None
                      else layout_factory(call, a, u, budget))
            packing = audit_layout(call, layout)
            if (layout.a, layout.u, layout.source["r"]) != (a, u, 64):
                raise ValueError("layout differs from finite depth schedule")
            if not packing["group_load_bound_met"]:
                raise Refusal("INCONCLUSIVE_SOURCE_PACKING", "actual finite group loads exceed shrink budget")
            preflight = preflight_packet_recursion(call, layout,
                ExecutionSpec(schedule=schedule[depth:], tuples=TupleStrategy(point_strategy), max_points=max_points),
                policy=policy)
            budget.tick(preflight.get('preflight_work_units', 1))
            if preflight['status'] != 'PASS_FINITE_NECESSARY_CONDITIONS':
                refusal = Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'packet topology/resource preflight refused')
                refusal.report = preflight
                raise refusal
            if budget.calls - 1 + preflight['recursive_calls_lower_bound'] > policy.max_calls:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'remaining recursive call lower bound')
            plan = make_packet_plan(call, layout, budget=budget, max_points=max_points)
            if budget.calls + 64 * len(plan.nodes) * (plan.degree_bound + 1) > policy.max_calls:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'complete recursive grid call lower bound')
            row_certificate = None
            if point_strategy == 'certified_support':
                from .row_degree import certify_row_degree
                # This certificate simplifies the exact point sum only. The
                # complete degree-bound grid and tapered functional stay intact.
                row_certificate = certify_row_degree(call, a, budget=budget)
            rows = []
            for t, zeta, precision in packet_points(call, layout, plan, budget=budget, max_points=max_points):
                modes = build_packet_modes(call, layout, t, zeta, budget=budget)
                support_summary = None
                if point_strategy == 'certified_support':
                    from .supported_engine import evaluate_supported_point
                    value, point_certificate = evaluate_supported_point(
                        call, layout, modes, budget=budget, contractor=visit, require_shrink=True,
                        row_certificate=row_certificate)
                    support_summary = point_certificate['support']
                else:
                    value = evaluate_packet_point(call, layout, modes, budget=budget,
                                                  contractor=visit, require_shrink=True)
                retain(rows, [t, list(zeta), precision, list(value[0])])
                retain(transitions, {"parent": call.content_digest, "depth": call.depth,
                                     "node": t, "modes": modes.content_digest,
                                     "tuples": modes.certificate["mode_tuple_count"], "child_count": 64,
                                     "point_strategy": point_strategy, "support": support_summary,
                                     "actual_child_shrink": "CHECKED_64_M_CHILD_LE_6_M",
                                     "packet_load_audit": packing})
            result, certificate = recover_packet_grid(call, layout, rows, budget=budget, max_points=max_points)
            retain(recoveries, {"parent": call.content_digest, "certificate": certificate.payload.decode("ascii")})
            return result

        result = visit(parent)
        if source_binding()["digest"] != binding:
            raise ValueError("source changed during calculation")
        return {"status": "PASS_FINITE_GENERAL_PACKET_RECURSION" if recoveries else "PASS_FINITE_SCALED_LEAF",
                "result": result, "source_qualified": False, "theorem_mode_enabled": False,
                "implementation_source_sha256": binding, "parent_digest": parent.content_digest,
                "per_point_independent_oracle_status": "NOT_RUN_IN_PRODUCTION",
                "point_strategy": point_strategy, "max_points": max_points,
                "source_tapered_functional_used": bool(recoveries),
                "original_weighted_stream_enumerated": point_strategy == 'complete_weighted',
                "transitions": transitions, "recoveries": recoveries, "ledger": budget.report()}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {"status": getattr(exc, "status", "INCONCLUSIVE_GENERAL_PACKET_RECURSION"),
                "reason": str(exc), "source_qualified": False, "theorem_mode_enabled": False,
                "preflight": getattr(exc, 'report', None), "ledger": budget.report()}
