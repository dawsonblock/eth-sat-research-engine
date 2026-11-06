"""Complete bounded cycle-transfer grid and exact tapered recovery.

The point calculation is a separate finite local-state execution contract.
Every point creates actual shrinking leaf children, then the final result is
recovered exclusively from the complete independently certified point grid.
No source theorem, generic runtime bound or oracle substitution is claimed.
"""

import base64
from dataclasses import asdict
import zlib

from veritas.research.tapered_v4.provenance import source_binding

from .cycle_transfer import _cycle_order, evaluate_cycle_transfer
from .general_recovery import make_general_plan, general_points, recover_general_grid
from .model import Budget, PacketLayout, ParentCall, Refusal, Semantics, canonical
from .shrinking_engine import DEFAULT_SHRINKING_POLICY
from .shrinking_layout import audit_vertex_shrinking_layout
from .shrinking_oracle import contract_independent
from .transfer_basis import build_transfer_basis
from .transfer_children import TransferChildren
from .transfer_recovery_verify import verify_transfer_recovery_certificate


SCHEMA = "VERITAS_R98_CYCLE_TRANSFER_RECOVERY_V1"


def contract_cycle_transfer(parent, layout, *, policy=None, budget=None, max_points=256):
    """Compute every point and return a replayable complete recovery certificate.

    Shared work/time/call/evidence limits cover production and independent
    replay. All point certificates are compressed only for storage: cumulative
    *uncompressed* evidence is separately capped, and the consumer bounds each
    decompression. A refusal never includes a partial value or certificate.
    """
    if budget is None:
        policy = DEFAULT_SHRINKING_POLICY if policy is None else policy
        budget = Budget(policy)
    elif policy is not None:
        raise TypeError("supply either policy or shared budget")
    else:
        policy = budget.policy
    starting_calls = budget.calls
    raw_bytes = encoded_bytes = compressed_bytes = completed_points = 0
    required_calls = None
    try:
        if type(parent) is not ParentCall or type(layout) is not PacketLayout:
            raise ValueError("typed parent and packet layout required")
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise ValueError("finite scaled parent required for cycle transfer")
        if parent.edge_count <= 4:
            raise Refusal("INCONCLUSIVE_UNSUPPORTED_TOPOLOGY", "transfer recovery requires an active parent with more than four edges")
        implementation = source_binding()["digest"]
        budget.call(parent.depth)
        packing = audit_vertex_shrinking_layout(parent, layout)
        plan = make_general_plan(parent, budget=budget, max_points=max_points)
        order = plan.degree_bound + 1
        point_count = len(plan.nodes) * order
        groups = layout.source["r"]
        degree = parent.defining_polynomial.bit_length() - 1
        if parent.depth + 1 > policy.max_depth:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "transfer leaf depth exceeds policy")

        # The requested grid consists of canonical binary residue lifts. Every
        # nonzero lift is a unit; W_xx(t+4*zeta) has valuation exactly two for
        # t=+/-1, so each real crossing is retained at each nonzero point.
        # Check topology and actual half-edge bounds on that complete basis
        # before making a production child call. Points are checked again by
        # their independent consumers; this is a resource preflight only.
        sample = build_transfer_basis(parent, layout, plan.nodes[0].t,
                                      (1,) + (0,) * (degree - 1), budget=budget)
        adjacency, cycle_nodes, _ = _cycle_order(groups, sample.certificate["modes"],
                                               budget=budget)
        mode_count = len(sample.certificate["modes"])
        if len(cycle_nodes) != mode_count:
            raise ValueError("transfer resource preflight cycle inventory differs")
        TransferChildren(parent, layout, sample, budget=budget)
        zero_point_calls = 1 + groups
        nonzero_point_calls = 1 + sum(1 << len(incident) for incident in adjacency)
        point_calls = len(plan.nodes) * (zero_point_calls + (order - 1) * nonzero_point_calls)
        required_calls = 1 + point_calls
        if budget.calls + point_calls > policy.max_calls:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete transfer grid exceeds remaining call budget")
        # All point payloads contain an ordered record for every group. Even
        # an empty record cannot serialize to less than this fixed JSON shape.
        minimum_group = len(canonical({"group": 0, "mode_indices": [], "values": [], "children": []}))
        if point_count * groups * minimum_group > policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "minimum complete point evidence exceeds byte budget")

        encoded_points, rows = [], []
        max_precision = parent.precision
        for node, zeta, precision in general_points(parent, plan, budget=budget, max_points=max_points):
            budget.tick()
            point = evaluate_cycle_transfer(parent, layout, node, zeta, budget=budget)
            if point.get("status") != "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT":
                status = point.get("status", "INVALID_CYCLE_TRANSFER_POINT")
                reason = point.get("reason", "point calculation did not complete")
                if status.startswith("INCONCLUSIVE_"):
                    raise Refusal(status, reason)
                raise ValueError("transfer point failed: " + reason)
            expected_modes = mode_count if any(zeta) else 0
            if (point["parent_digest"] != parent.content_digest
                    or point["group_count"] != groups
                    or point["point_precision"] != precision
                    or point["retained_modes"] != expected_modes
                    or not point["all_actual_children_are_leaves"]):
                raise ValueError("transfer point metadata or complete mode basis differs")
            value, raw = point["result"], point["certificate"]
            if type(raw) is not bytes:
                raise ValueError("serialized point certificate required")
            raw_bytes += len(raw)
            if raw_bytes > policy.max_certificate_bytes:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "cumulative uncompressed point evidence exceeds byte budget")
            budget.tick(len(raw))
            compressed = zlib.compress(raw, level=9)
            encoded = base64.b64encode(compressed).decode("ascii")
            compressed_bytes += len(compressed)
            encoded_bytes += len(encoded)
            if compressed_bytes > policy.max_certificate_bytes or encoded_bytes > policy.max_certificate_bytes:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "cumulative encoded point evidence exceeds byte budget")
            budget.tick(len(compressed) + len(encoded))
            encoded_points.append(encoded)
            rows.append([node, list(zeta), precision, list(value[0])])
            max_precision = max(max_precision, precision)
            completed_points += 1

        if completed_points != point_count or budget.calls != starting_calls + required_calls:
            raise ValueError("complete transfer grid or planned child calls differ")
        value, recovery = recover_general_grid(parent, layout, rows, budget=budget,
                                                max_points=max_points)
        if contract_independent(parent, budget) != value:
            raise ValueError("recovered transfer value differs from independent original contraction")
        raw_bytes += len(recovery.payload)
        if raw_bytes > policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "cumulative uncompressed recovery evidence exceeds byte budget")
        payload = canonical({"schema": SCHEMA, "parent_digest": parent.content_digest,
            "layout_digest": layout.content_digest, "point_certificates": encoded_points,
            "recovery_certificate": recovery.payload.decode("ascii"),
            "result": [list(row) for row in value]})
        if len(payload) > policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "complete transfer recovery certificate byte cap")
        budget.tick(len(payload))
        checked = verify_transfer_recovery_certificate(parent, layout, payload, budget=budget,
                                                        max_points=max_points)
        if checked.get("status") != "PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY":
            status = checked.get("status", "INVALID_TRANSFER_RECOVERY_CERTIFICATE")
            reason = checked.get("reason", "independent recovery replay failed")
            if status.startswith("INCONCLUSIVE_"):
                raise Refusal(status, reason)
            raise ValueError("independent transfer recovery replay rejected: " + reason)
        if checked.get("result") != value or checked.get("replayed_points") != point_count:
            raise ValueError("independent transfer recovery result or grid differs")
        if source_binding()["digest"] != implementation:
            raise ValueError("implementation source changed during full-grid execution")
        budget.tick(0)
        return {
            "status": "PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY",
            "result": value, "certificate": payload,
            "parent_digest": parent.content_digest, "layout_digest": layout.content_digest,
            "implementation_source_sha256": implementation,
            "source_qualified": False, "theorem_mode_enabled": False,
            "scaled_experiment": True, "packing": packing,
            "group_count": groups, "parent_edges": parent.edge_count,
            "retained_modes_per_nonzero_point": mode_count,
            "zero_point_count": len(plan.nodes), "point_evaluations": completed_points,
            "points_per_node": order, "full_hermite_grid": "COMPLETE",
            "parent_contraction_recovered": True,
            "tuple_completeness": "COMPLETE_SUM_ALGEBRAICALLY_AGGREGATED",
            "global_tuple_stream_enumerated": False,
            "paper_formal_mode_domain_enumerated": False,
            "transition_scope": "REPRESENTATIVE_LOCAL_GROUP_CHILD",
            "required_actual_calls": required_calls, "maximal_precision_used": max_precision,
            "uncompressed_evidence_bytes": raw_bytes, "compressed_point_bytes": compressed_bytes,
            "base64_point_bytes": encoded_bytes, "certificate_bytes": len(payload),
            "per_point_independent_oracle_status": "PASS_HALF_EDGE_ELIMINATION",
            "independent_certificate_status": checked["status"],
            "independent_original_contraction": "PASS_ORACLE_AGREEMENT",
            "oracle_supplied_answer": False, "creation_precision_inheritance": True,
            "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
            "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
            "policy": asdict(policy), "ledger": budget.report(),
        }
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError,
            RuntimeError, MemoryError, zlib.error) as exc:
        return {
            "status": getattr(exc, "status", "INCONCLUSIVE_CYCLE_TRANSFER_RECOVERY"),
            "reason": str(exc), "source_qualified": False, "theorem_mode_enabled": False,
            "scaled_experiment": True, "completed_points": completed_points,
            "required_actual_calls": required_calls, "ledger": budget.report(),
        }
