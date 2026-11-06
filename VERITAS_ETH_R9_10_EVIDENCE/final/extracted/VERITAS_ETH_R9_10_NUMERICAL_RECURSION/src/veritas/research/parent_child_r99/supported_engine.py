"""Separate exact finite support executor, with real group children throughout."""
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.model import Budget, DEFAULT_POLICY, ExponentTuple, Refusal, canonical
from veritas.research.tapered_v4.provenance import source_binding
from .basis import build_packet_modes
from .engine import _topology
from .recovery import make_packet_plan, packet_points, recover_packet_grid
from .support import build_support, fold_source_forms
from .support_check import verify_support


def evaluate_supported_point(parent, layout, original, *, budget, contractor=None, require_shrink=False,
                             row_certificate=None):
    """Contract all 64 children for each certified supported folded exponent.

    The input is the complete original mode basis. This explicitly aggregates
    its weighted sum; it does not claim to enumerate the original tuple stream.
    """
    folded = fold_source_forms(parent, layout, original, budget=budget)
    support = build_support(original, folded, budget=budget, row_certificate=row_certificate)
    verification = verify_support(parent, layout, original, folded, support, budget=budget)
    tuples = support.record['tuples']
    if budget.calls + 64 * len(tuples) > budget.policy.max_calls:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'complete supported point call lower bound')
    ring = JetRing(ExtensionRing(original.certificate['precision'], parent.defining_polynomial,
                                max_precision_bits=budget.policy.max_precision), 1)
    total, values = ring.zero, []
    evidence_bytes = len(support.payload) + len(original.certificate_bytes) + len(folded.certificate_bytes)
    for exponents in tuples:
        beta = ExponentTuple(folded.content_digest, tuple(exponents))
        children = construct_children(parent, layout, folded, beta, budget=budget,
                                      _admitted=True, require_shrink=require_shrink)
        _topology(parent, layout, folded, beta, children, budget, require_shrink)
        if contractor is None and any(child.edge_count > 4 for child in children):
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'supported point requires recursive nonleaf contractor')
        term, row = ring.one, []
        for child in children:
            call = child.as_parent(parent)
            if contractor is None:
                budget.call(call.depth)
                value = leaf(call, budget)
            else:
                value = contractor(call)
            term = ring.mul(term, value)
            row.append(value)
            budget.tick(ring.base.e**2)
            budget.transitions += 1
        evidence_bytes += len(canonical(row))
        if evidence_bytes > budget.policy.max_certificate_bytes:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'supported point evidence cap')
        values.append(row)
        total = ring.add(total, term)
        budget.tuples += 1
    budget.points += 1
    certificate = {
        'schema': 'VERITAS_R99_SUPPORTED_POINT_V1',
        'parent_digest': parent.content_digest, 'layout_digest': layout.content_digest,
        'original_modes': original.certificate, 'folded_modes': folded.certificate,
        'support': support.record, 'child_values': values, 'result': total,
        'require_shrink': require_shrink,
        'child_value_method': 'RECURSIVE_CALLS' if contractor else 'EXACT_FOUR_EDGE_LEAVES',
    }
    if len(canonical(certificate)) > budget.policy.max_certificate_bytes:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'supported point serialized cap')
    return total, certificate


def recover_supported_parent(parent, layout, *, policy=DEFAULT_POLICY, max_points=256):
    """Full general grid for a bounded parent whose group children are leaves.

    This identity/recovery entry point deliberately transforms even tiny
    parents. It reports actual shrink separately from equality, and never
    falls back to an original-network contraction.
    """
    budget = Budget(policy)
    binding = source_binding()['digest']
    try:
        plan = make_packet_plan(parent, layout, budget=budget, max_points=max_points)
        if 64 * len(plan.nodes) * (plan.degree_bound + 1) > policy.max_calls:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'complete recovery call lower bound')
        rows, certificates, evidence_bytes = [], [], 0
        for node, zeta, precision in packet_points(parent, layout, plan, budget=budget, max_points=max_points):
            modes = build_packet_modes(parent, layout, node, zeta, budget=budget)
            value, certificate = evaluate_supported_point(parent, layout, modes, budget=budget)
            evidence_bytes += len(canonical(certificate))
            if evidence_bytes > policy.max_certificate_bytes:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'supported recovery evidence cap')
            rows.append([node, list(zeta), precision, list(value[0])])
            certificates.append(certificate)
        result, recovery = recover_packet_grid(parent, layout, rows, budget=budget, max_points=max_points)
        payload = {
            'schema': 'VERITAS_R99_SUPPORTED_RECOVERY_V1',
            'parent_digest': parent.content_digest, 'layout_digest': layout.content_digest,
            'points': certificates, 'recovery': recovery.payload.decode('ascii'), 'result': result,
        }
        if len(canonical(payload)) > policy.max_certificate_bytes:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'supported recovery serialized cap')
        if source_binding()['digest'] != binding:
            raise ValueError('source changed during supported recovery')
        return {'status': 'PASS_FINITE_SUPPORTED_PACKET_RECOVERY', 'result': result,
                'certificate': payload, 'ledger': budget.report(), 'source_qualified': False,
                'original_weighted_stream_enumerated': False,
                'implementation_source_sha256': binding}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {'status': getattr(exc, 'status', 'INCONCLUSIVE_SUPPORTED_RECOVERY'),
                'reason': str(exc), 'ledger': budget.report(), 'source_qualified': False}
