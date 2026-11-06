"""Independent bounded replay of a complete finite cycle-transfer grid.

The consumer replays every point certificate and constructs its recovery
input exclusively from the verified point values.  It does not import the
production transfer builder or use an oracle result as an answer.  This is a
finite certificate boundary, not a proof of source-recursion complexity.
"""

import base64
import binascii
import zlib

from .general_recovery import make_general_plan, general_points, recover_general_grid
from .model import Budget, PacketLayout, ParentCall, Refusal, Semantics, canonical, decode
from .shrinking_oracle import contract_independent
from .transfer_verify import verify_transfer_certificate


SCHEMA = "VERITAS_R98_CYCLE_TRANSFER_RECOVERY_V1"
FIELDS = {"schema", "parent_digest", "layout_digest", "point_certificates",
          "recovery_certificate", "result"}


def _bounded_point_decode(encoded, *, remaining_bytes, budget):
    """Decode one canonical base64/zlib stream without unbounded allocation."""
    if type(encoded) is not str:
        raise ValueError("point certificate encoding must be an ASCII string")
    if type(remaining_bytes) is not int or remaining_bytes < 0:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "decompressed evidence byte cap")
    budget.tick(len(encoded))
    try:
        wire = encoded.encode("ascii")
        compressed = base64.b64decode(wire, validate=True)
    except (UnicodeError, ValueError, binascii.Error) as exc:
        raise ValueError("invalid point certificate base64") from exc
    if base64.b64encode(compressed) != wire:
        raise ValueError("noncanonical point certificate base64")
    if len(compressed) > budget.policy.max_certificate_bytes:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "compressed point byte cap")
    budget.tick(len(compressed))
    decoder = zlib.decompressobj()
    try:
        # One extra byte distinguishes an exactly full valid stream from a
        # zip bomb, while bounding the temporary output allocation.
        raw = decoder.decompress(compressed, remaining_bytes + 1)
    except zlib.error as exc:
        raise ValueError("invalid compressed point certificate") from exc
    if len(raw) > remaining_bytes or decoder.unconsumed_tail:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "decompressed evidence byte cap")
    if not decoder.eof or decoder.unused_data:
        raise ValueError("truncated or trailing compressed point certificate")
    budget.tick(len(raw))
    return raw, len(compressed)


def verify_transfer_recovery_certificate(parent, layout, certificate, *, policy=None,
                                         budget=None, max_points=256):
    """Replay a full point grid, rational recovery and original network oracle.

    Only values returned by independent point replay enter recovery.  The
    independent original-network contraction is used solely to reject a
    disagreement, never to supply the returned result.
    """
    from .shrinking_engine import DEFAULT_SHRINKING_POLICY

    if budget is None:
        budget = Budget(DEFAULT_SHRINKING_POLICY if policy is None else policy)
    elif policy is not None:
        raise TypeError("supply either policy or shared budget")
    try:
        if type(parent) is not ParentCall or type(layout) is not PacketLayout:
            raise ValueError("typed parent and packet layout required")
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise ValueError("finite scaled parent required")
        data = decode(certificate, cap=budget.policy.max_certificate_bytes)
        budget.tick(len(certificate))
        if type(data) is not dict or set(data) != FIELDS or data["schema"] != SCHEMA:
            raise ValueError("transfer recovery certificate fields or schema")
        if data["parent_digest"] != parent.content_digest or data["layout_digest"] != layout.content_digest:
            raise ValueError("transfer recovery parent or layout digest differs")
        if layout.parent_digest != parent.content_digest:
            raise ValueError("transfer recovery layout ancestry differs")
        if type(data["point_certificates"]) is not list:
            raise ValueError("transfer recovery requires an ordered point inventory")
        if type(data["recovery_certificate"]) is not str:
            raise ValueError("recovery certificate must be an ASCII string")
        plan = make_general_plan(parent, budget=budget, max_points=max_points)
        expected_count = len(plan.nodes) * (plan.degree_bound + 1)
        if len(data["point_certificates"]) != expected_count:
            raise ValueError("incomplete transfer recovery point grid")
        rows, row_bytes = [], 0
        compressed_bytes = decompressed_bytes = 0
        point_count = 0
        for (node, zeta, precision), encoded in zip(
                general_points(parent, plan, budget=budget, max_points=max_points),
                data["point_certificates"]):
            remaining = budget.policy.max_certificate_bytes - decompressed_bytes
            raw, size = _bounded_point_decode(encoded, remaining_bytes=remaining, budget=budget)
            compressed_bytes += size
            decompressed_bytes += len(raw)
            if compressed_bytes > budget.policy.max_certificate_bytes:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "cumulative compressed evidence byte cap")
            checked = verify_transfer_certificate(
                parent, layout, raw, budget=budget,
                expected_point=(node, tuple(zeta), precision),
            )
            if checked.get("status") != "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT":
                status = checked.get("status", "INVALID_CYCLE_TRANSFER_CERTIFICATE")
                reason = checked.get("reason", "independent point replay failed")
                if status.startswith("INCONCLUSIVE_"):
                    raise Refusal(status, reason)
                raise ValueError("independent point replay rejected: " + reason)
            value = checked["result"]
            row = [node, list(zeta), precision, list(value[0])]
            row_bytes += len(canonical(row))
            if row_bytes > budget.policy.max_certificate_bytes:
                raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "replayed point grid byte cap")
            rows.append(row)
            point_count += 1
        if point_count != expected_count:
            raise ValueError("incomplete replayed transfer grid")
        value, expected = recover_general_grid(parent, layout, rows, budget=budget,
                                                max_points=max_points)
        encoded_recovery = data["recovery_certificate"].encode("ascii")
        if decompressed_bytes + len(encoded_recovery) > budget.policy.max_certificate_bytes:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "cumulative uncompressed recovery evidence byte cap")
        if encoded_recovery != expected.payload:
            raise ValueError("transfer recovery certificate or precision metadata differs")
        claimed = data["result"]
        degree = parent.defining_polynomial.bit_length() - 1
        if (type(claimed) is not list or len(claimed) != 1
                or type(claimed[0]) is not list or len(claimed[0]) != degree
                or any(type(x) is not int or not 0 <= x < 1 << parent.precision
                       for x in claimed[0])
                or claimed != [list(row) for row in value]):
            raise ValueError("transfer recovery result differs from independently replayed points")
        if contract_independent(parent, budget) != value:
            raise ValueError("transfer recovery differs from independent original contraction")
        budget.tick(0)
        return {
            "status": "PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY",
            "result": value, "parent_digest": parent.content_digest,
            "layout_digest": layout.content_digest, "replayed_points": point_count,
            "compressed_point_bytes": compressed_bytes,
            "decompressed_point_bytes": decompressed_bytes,
            "point_status": "ALL_INDEPENDENT_CHILD_AND_HALF_EDGE_REPLAYS_PASS",
            "recovery_status": "COEFFICIENTWISE_RATIONAL_AND_REFERENCE_CHECKED",
            "original_contraction_status": "INDEPENDENT_ORACLE_AGREEMENT",
            "oracle_supplied_answer": False, "source_qualified": False,
            "theorem_mode_enabled": False, "ledger": budget.report(),
        }
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError,
            RuntimeError, MemoryError, zlib.error, binascii.Error) as exc:
        return {
            "status": getattr(exc, "status", "INVALID_TRANSFER_RECOVERY_CERTIFICATE"),
            "reason": str(exc), "source_qualified": False,
            "theorem_mode_enabled": False, "ledger": budget.report(),
        }
