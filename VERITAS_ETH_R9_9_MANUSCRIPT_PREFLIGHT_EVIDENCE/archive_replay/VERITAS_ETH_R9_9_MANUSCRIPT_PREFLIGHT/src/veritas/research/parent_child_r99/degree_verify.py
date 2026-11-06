"""Independent replay of actual shrinking children from a bounded event stream.

Production constructors, entry arithmetic and recursive engines are absent.
The verifier reconstructs child recipes and evaluates only <=4-edge leaves.
Its evidence index is bounded, but is not claimed to have polynomial space.
"""
from hashlib import sha256

from veritas.research.parent_child_r98.independent import reference_children
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, ModeSet, PacketLayout, Refusal, canonical, decode
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_oracle import contract_independent, _arithmetic
from .degree_recovery import degree_points
from .degree_check import verify_degree_recovery
from .support import SupportCertificate
from .support_check import verify_support
from .supported_verify import POINT_FIELDS


def verify_recursive_events(parent, events, claimed_report, *, policy=DEFAULT_SHRINKING_POLICY, max_points=256):
    budget = Budget(policy)
    chain, byte_count = '0' * 64, 0
    points, recoveries = {}, {}
    consumed_points, consumed_calls = set(), set()
    sizes, active, nonconstant, crossing = {}, {}, {}, {}
    max_precision = parent.precision
    try:
        if (claimed_report.get('status') != 'PASS_FINITE_SUPPORTED_SHRINKING_RECURSION' or
            claimed_report.get('source_qualified') is not False or
            claimed_report.get('theorem_mode_enabled') is not False or
            claimed_report.get('source_tapered_functional_used') is not False or
            claimed_report.get('original_weighted_stream_enumerated') is not False or
            type(claimed_report.get('leaf_threshold')) is not int or claimed_report['leaf_threshold'] != 4 or
            claimed_report.get('every_child_shrink') != 'CHECKED_64_M_CHILD_LE_6_M'):
            raise ValueError('unsupported recursive report claims')
        for raw in events:
            if type(raw) is not bytes:
                raise ValueError('canonical event bytes required')
            byte_count += len(raw)
            if byte_count > policy.max_certificate_bytes:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'recursive replay evidence cap')
            event = decode(raw, cap=policy.max_certificate_bytes)
            if type(event.get('depth')) is not int:
                raise ValueError('recursive event depth must be an integer')
            chain = sha256(bytes.fromhex(chain) + raw).hexdigest()
            if event['kind'] == 'point':
                if set(event) != {'kind', 'depth', 'certificate'}:
                    raise ValueError('recursive point event fields')
                point = event['certificate']
                if set(point) != POINT_FIELDS or point['schema'] != 'VERITAS_R99_SUPPORTED_POINT_V1':
                    raise ValueError('recursive point certificate schema')
                modes = point['original_modes']
                key = (point['parent_digest'], modes['node'], tuple(modes['zeta']))
                if key in points:
                    raise ValueError('duplicated recursive point')
                points[key] = event
            elif event['kind'] == 'recovery':
                if set(event) != {'kind', 'depth', 'parent_digest', 'parent_edges', 'layout', 'rows', 'certificate', 'result'}:
                    raise ValueError('recursive recovery event fields')
                if event['parent_digest'] in recoveries:
                    raise ValueError('duplicated recursive recovery')
                recoveries[event['parent_digest']] = event
            else:
                raise ValueError('unknown recursive evidence event')
            budget.tick()
        if (claimed_report.get('evidence_chain') != chain or claimed_report.get('evidence_bytes') != byte_count or
                claimed_report.get('parent_digest') != parent.content_digest):
            raise ValueError('recursive evidence binding changed')

        def visit(call):
            nonlocal max_precision
            budget.call(call.depth)
            depth = call.depth - parent.depth
            sizes[depth] = max(sizes.get(depth, 0), call.edge_count)
            max_precision = max(max_precision, call.precision)
            if call.edge_count > policy.max_edges or call.precision > policy.max_precision:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'recursive replay dimension cap')
            if call.edge_count <= 4:
                return contract_independent(call, budget)
            if call.content_digest in consumed_calls or call.content_digest not in recoveries:
                raise ValueError('missing or reused active child recovery')
            consumed_calls.add(call.content_digest)
            event = recoveries[call.content_digest]
            if event['depth'] != call.depth or type(event['parent_edges']) is not int or event['parent_edges'] != call.edge_count:
                raise ValueError('altered recursive size or depth')
            description = event['layout']
            if set(description) != {'a', 'u', 'strategy', 'source'}:
                raise ValueError('recursive layout fields')
            layout = PacketLayout(call.content_digest, description['a'], description['u'],
                                  canonical(description['source']), description['strategy'])
            packing = audit_layout(call, layout)
            if not packing['group_load_bound_met'] or layout.source['r'] != 64:
                raise ValueError('recursive replay actual packing load failure')
            degree = event['certificate']['degree_certificate']
            expected = tuple(degree_points(call, layout, degree, budget=budget, max_points=max_points))
            node_metadata = []
            for t, _, precision in expected[::degree['degree_bound'] + 1]:
                node_metadata.append({'node': t, 'precision': precision,
                    'coefficient_count': degree['degree_bound'] + 1,
                    'exact_zero_tail_from': degree['degree_bound'] + 1,
                    'denominator_bits': (layout.a + 1) * degree['degree_bound']})
            metadata = {'method': 'DEGREE_CERTIFIED_TAYLOR_AT_EACH_SOURCE_NODE',
                'degree_certificate': degree, 'nodes': node_metadata,
                'source_tapered_functional_used': False, 'source_qualified': False}
            if canonical(event['certificate']) != canonical(metadata):
                raise ValueError('recursive recovery arithmetic metadata changed')
            active[depth] = active.get(depth, 0) + 1
            if degree['nonconstant_row_ports']:
                nonconstant[depth] = nonconstant.get(depth, 0) + 1
            rows = []
            for t, zeta, precision in expected:
                key = (call.content_digest, t, zeta)
                if key not in points or key in consumed_points:
                    raise ValueError('missing or reused recursive point')
                consumed_points.add(key)
                point_event = points[key]
                point = point_event['certificate']
                if (point_event['depth'] != call.depth or point['layout_digest'] != layout.content_digest or
                    point['require_shrink'] is not True or point['child_value_method'] != 'RECURSIVE_CALLS'):
                    raise ValueError('recursive point depth, layout or method changed')
                original = ModeSet(layout.content_digest, canonical(point['original_modes']))
                folded = ModeSet(layout.content_digest, canonical(point['folded_modes']))
                support = SupportCertificate(canonical(point['support']))
                verify_support(call, layout, original, folded, support, budget=budget)
                if (original.certificate['precision'] != precision or
                        canonical(support.record['row_certificate']) != canonical(degree)):
                    raise ValueError('recursive point precision or row premise changed')
                if original.certificate['modes']:
                    crossing[depth] = crossing.get(depth, 0) + 1
                betas, values = support.record['tuples'], point['child_values']
                if type(values) is not list or len(values) != len(betas):
                    raise ValueError('recursive supported tuple coverage')
                ar = _arithmetic(call, precision, budget)
                total = ar.zero
                for exponents, submitted in zip(betas, values):
                    beta = ExponentTuple(folded.content_digest, tuple(exponents))
                    children = reference_children(call, layout, folded, beta)
                    if len(children) != 64 or any(64*c.edge_count > 6*call.edge_count or
                            c.edge_count >= call.edge_count for c in children):
                        raise ValueError('independent recursive child shrink failed')
                    if any(max((len(v.ports) for v in c.vertices), default=0) >
                           max(call.maximum_degree, 2 << layout.a) for c in children):
                        raise ValueError('independent recursive child degree failed')
                    if type(submitted) is not list or len(submitted) != 64:
                        raise ValueError('missing recursive child value')
                    product = ar.one
                    for child, value in zip(children, submitted):
                        checked = visit(child.as_parent(call))
                        if canonical(checked) != canonical(value):
                            raise ValueError('stored recursive child value differs from actual descendants')
                        product = ar.mul(product, checked)
                        budget.transitions += 1
                    total = ar.add(total, product)
                    budget.tuples += 1
                budget.tick(ar.used)
                budget.points += 1
                if canonical(total) != canonical(point['result']):
                    raise ValueError('recursive point sum differs')
                rows.append([t, list(zeta), precision, list(total[0])])
            if canonical(rows) != canonical(event['rows']):
                raise ValueError('recovery grid differs from recomputed child points')
            return verify_degree_recovery(call, layout, degree, rows, event['result'],
                                          budget=budget, max_points=max_points)

        result = visit(parent)
        if (consumed_points != set(points) or consumed_calls != set(recoveries) or
            canonical(result) != canonical(claimed_report.get('result')) or
            canonical({str(k): v for k, v in sizes.items()}) != canonical(claimed_report.get('largest_edges_by_depth')) or
            canonical({str(k): v for k, v in active.items()}) != canonical(claimed_report.get('active_calls_by_depth')) or
            canonical({str(k): v for k, v in nonconstant.items()}) != canonical(claimed_report.get('nonconstant_active_calls_by_depth')) or
            canonical({str(k): v for k, v in crossing.items()}) != canonical(claimed_report.get('crossing_points_by_depth')) or
            max_precision != claimed_report.get('maximum_precision')):
            raise ValueError('recursive coverage, result or accounting changed')
        for key in ('actual_calls', 'maximum_depth', 'point_evaluations', 'tuples', 'transitions'):
            if type(claimed_report['ledger'][key]) is not int or budget.report()[key] != claimed_report['ledger'][key]:
                raise ValueError('recursive ledger differs: ' + key)
        return {'status': 'PASS_INDEPENDENT_SUPPORTED_RECURSION', 'result': result,
                'ledger': budget.report(), 'source_qualified': False, 'evidence_chain': chain}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {'status': getattr(exc, 'status', 'INVALID_SUPPORTED_RECURSION'), 'reason': str(exc),
                'ledger': budget.report(), 'source_qualified': False}
