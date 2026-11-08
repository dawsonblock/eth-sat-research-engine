"""Standalone bounded arithmetic replay, with no production child constructor."""
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.independent import reference_children, verify_children
from veritas.research.parent_child_r98.model import Budget, DEFAULT_POLICY, ExponentTuple, ModeSet, canonical
from veritas.research.parent_child_r98.shrinking_oracle import parent_point
from .recovery import make_packet_plan, packet_points, recover_packet_grid
from .support import SupportCertificate
from .support_check import verify_support


POINT_FIELDS = {'schema', 'parent_digest', 'layout_digest', 'original_modes', 'folded_modes',
                'support', 'child_values', 'result', 'require_shrink', 'child_value_method'}


def verify_supported_point(parent, layout, certificate, *, budget):
    if (type(certificate) is not dict or set(certificate) != POINT_FIELDS or
            certificate['schema'] != 'VERITAS_R99_SUPPORTED_POINT_V1' or
            certificate['parent_digest'] != parent.content_digest or
            certificate['layout_digest'] != layout.content_digest or
            type(certificate['require_shrink']) is not bool or
            certificate['child_value_method'] != 'EXACT_FOUR_EDGE_LEAVES'):
        raise ValueError('supported leaf point fields, ancestry or method mismatch')
    if len(canonical(certificate)) > budget.policy.max_certificate_bytes:
        raise ValueError('supported point replay byte cap')
    original = ModeSet(layout.content_digest, canonical(certificate['original_modes']))
    folded = ModeSet(layout.content_digest, canonical(certificate['folded_modes']))
    support = SupportCertificate(canonical(certificate['support']))
    verify_support(parent, layout, original, folded, support, budget=budget)
    tuples, submitted = support.record['tuples'], certificate['child_values']
    if type(submitted) is not list or len(submitted) != len(tuples):
        raise ValueError('supported point tuple value coverage')
    ring = JetRing(ExtensionRing(original.certificate['precision'], parent.defining_polynomial,
                                max_precision_bits=budget.policy.max_precision), 1)
    total, all_shrink = ring.zero, True
    for beta_values, values in zip(tuples, submitted):
        beta = ExponentTuple(folded.content_digest, tuple(beta_values))
        children = reference_children(parent, layout, folded, beta)
        if any(child.edge_count > 4 for child in children):
            raise ValueError('independent leaf point cannot certify recursive nonleaf results')
        report = verify_children(parent, layout, folded, beta, children, budget=budget, _admitted=True)
        if canonical(values) != canonical(report['values']):
            raise ValueError('independent child contraction differs from stored value')
        all_shrink = all_shrink and report['all_source_shrink']
        if certificate['require_shrink'] and not report['all_source_shrink']:
            raise ValueError('supported point claimed shrink fails actual child counts')
        product = ring.one
        for value in report['values']:
            product = ring.mul(product, value)
            budget.tick(ring.base.e**2)
        total = ring.add(total, product)
    if canonical(total) != canonical(certificate['result']):
        raise ValueError('supported point total changed')
    if total != parent_point(parent, layout, original, budget=budget):
        raise ValueError('independent half-edge Cauchy point mismatch')
    return total, {'status': 'PASS_INDEPENDENT_SUPPORTED_POINT',
                   'actual_source_shrink': all_shrink, 'source_qualified': False}


def verify_supported_recovery(parent, layout, certificate, *, policy=DEFAULT_POLICY, max_points=256):
    budget = Budget(policy)
    try:
        if (type(certificate) is not dict or set(certificate) !=
                {'schema', 'parent_digest', 'layout_digest', 'points', 'recovery', 'result'} or
                certificate['schema'] != 'VERITAS_R99_SUPPORTED_RECOVERY_V1' or
                certificate['parent_digest'] != parent.content_digest or
                certificate['layout_digest'] != layout.content_digest):
            raise ValueError('supported recovery fields or ancestry mismatch')
        if len(canonical(certificate)) > policy.max_certificate_bytes:
            raise ValueError('supported recovery replay byte cap')
        plan = make_packet_plan(parent, layout, budget=budget, max_points=max_points)
        if type(certificate['points']) is not list or len(certificate['points']) != len(plan.nodes) * (plan.degree_bound + 1):
            raise ValueError('incomplete supported recovery grid')
        rows, all_shrink = [], True
        for (t, zeta, precision), point in zip(
                packet_points(parent, layout, plan, budget=budget, max_points=max_points), certificate['points']):
            value, report = verify_supported_point(parent, layout, point, budget=budget)
            modes = point['original_modes']
            if canonical((modes['node'], modes['zeta'], modes['precision'])) != canonical((t, zeta, precision)):
                raise ValueError('altered supported grid node, order or precision')
            all_shrink = all_shrink and report['actual_source_shrink']
            rows.append([t, list(zeta), precision, list(value[0])])
        result, recovery = recover_packet_grid(parent, layout, rows, budget=budget, max_points=max_points)
        if (canonical(result) != canonical(certificate['result']) or
                recovery.payload.decode('ascii') != certificate['recovery']):
            raise ValueError('independent supported recovery mismatch')
        return {'status': 'PASS_INDEPENDENT_SUPPORTED_RECOVERY', 'result': result,
                'point_count': len(rows), 'actual_source_shrink': all_shrink,
                'source_qualified': False, 'ledger': budget.report()}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {'status': getattr(exc, 'status', 'INVALID_SUPPORTED_RECOVERY'),
                'reason': str(exc), 'source_qualified': False, 'ledger': budget.report()}
