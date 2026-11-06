"""Single-pass recursive consumer. No production constructors or entry evaluator.

Only the recursion stack, bounded verified cache and current interpolation
polynomials are retained. The supplied iterator is consumed once, in order.
"""
from hashlib import sha256

from veritas.research.parent_child_r98.independent import reference_children
from veritas.research.parent_child_r98.model import ExponentTuple, ModeSet, PacketLayout, Refusal, canonical, decode
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_oracle import contract_independent, _arithmetic
from veritas.research.tapered_v4.provenance import source_binding
from veritas.research.parent_child_r99.execution import ExecutionSpec, TupleStrategy
from veritas.research.parent_child_r99.resources import ExactCache, computation_key
from veritas.research.parent_child_r99.row_degree import verify_row_degree
from .recovery import Recovery
from .accounting import AccountedBudget
from veritas.research.parent_child_r99.support import SupportCertificate
from veritas.research.parent_child_r99.support_check import verify_support


def verify(parent, events, report, *, policy=DEFAULT_SHRINKING_POLICY):
    budget = AccountedBudget(policy)
    chain, byte_count, requests = '0'*64, 0, 0
    active, sizes, degrees, predictions = {}, {}, {}, []
    try:
        if (report.get('schema') != 'VERITAS_R910_NUMERICAL_V1' or
            report.get('status') != 'PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION' or
            report.get('parent_digest') != parent.content_digest or
            report.get('source_qualified') is not False or report.get('theorem_mode_enabled') is not False or
            report.get('source_tapered_functional_used') is not (parent.edge_count > 4) or
            report.get('original_weighted_stream_enumerated') is not False or
            report.get('recovery_optimization') != 'CERTIFIED_ZERO_TAIL_ORIGINAL_FUNCTIONAL' or
            report.get('implementation_source_sha256') != source_binding()['digest']):
            raise ValueError('unsupported streaming report or source binding')
        schedule = tuple(tuple(pair) for pair in report['schedule'])
        spec = ExecutionSpec(schedule=schedule, tuples=TupleStrategy.SUPPORT, max_points=report['max_points'])
        cap = report['cache']['max_payload_bytes']
        if type(cap) is not int or not 0 <= cap <= policy.max_certificate_bytes:
            raise ValueError('unbounded replay cache')
        cache, stream = ExactCache(cap), iter(events)

        def read(kind=None):
            nonlocal chain, byte_count
            raw = next(stream)
            if type(raw) is not bytes:
                raise ValueError('canonical bytes required')
            byte_count += len(raw)
            if byte_count > policy.max_certificate_bytes:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'stream replay byte budget')
            event = decode(raw, cap=policy.max_certificate_bytes)
            if kind is not None and event.get('kind') != kind:
                raise ValueError('missing or reordered stream event')
            chain = sha256(bytes.fromhex(chain) + raw).hexdigest()
            budget.tick()
            return event

        def visit(call):
            nonlocal requests
            requests += 1
            budget.tick()
            if (call.edge_count > policy.max_edges or call.precision > policy.max_precision or
                    call.depth > policy.max_depth):
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'replay dimensions')
            depth = call.depth - parent.depth
            key = computation_key(call, schedule[depth:])
            cached = cache.get(key)
            event = read()
            if event.get('parent') != call.content_digest or event.get('key') != key:
                raise ValueError('recursive ancestry or computation key mismatch')
            if cached is not None:
                if set(event) != {'kind', 'parent', 'key'} or event['kind'] != 'reuse':
                    raise ValueError('invalid cache reuse event')
                return cached
            budget.call(call.depth)
            if call.edge_count <= 4:
                result = contract_independent(call, budget)
                if (set(event) != {'kind', 'parent', 'key', 'result'} or event['kind'] != 'leaf' or
                        canonical(result) != canonical(event['result'])):
                    raise ValueError('independent leaf result mismatch')
                cache.put(key, result)
                return result
            if depth >= len(schedule):
                raise ValueError('nonleaf outside schedule')
            if set(event) != {'kind', 'parent', 'key', 'layout', 'row_certificate', 'recovery'} or event['kind'] != 'start':
                raise ValueError('missing active recursive call')
            description = event['layout']
            if set(description) != {'a', 'u', 'source', 'strategy'}:
                raise ValueError('layout fields')
            layout = PacketLayout(call.content_digest, description['a'], description['u'],
                                  canonical(description['source']), description['strategy'])
            if (layout.a, layout.u, layout.source['r']) != (*schedule[depth], 64):
                raise ValueError('replay depth schedule mismatch')
            if not audit_layout(call, layout)['group_load_bound_met']:
                raise ValueError('independent actual packing failure')
            degree = event['row_certificate']
            verify_row_degree(call, layout.a, degree, budget=budget)
            recovery = Recovery(call, layout, degree, budget=budget, max_points=spec.max_points, independent=True)
            if canonical(recovery.description) != canonical(event['recovery']):
                raise ValueError('recovery functional or zero tail changed')
            active[str(depth)] = active.get(str(depth), 0)+1
            sizes[str(depth)] = max(sizes.get(str(depth), 0), call.edge_count)
            degrees[str(depth)] = max(degrees.get(str(depth), 0), degree['degree_bound'])
            prediction = {'parent': call.content_digest,
                'expected_local_points': recovery.description['actual_point_count'],
                'generic_local_points': recovery.description['generic_point_count'],
                'actual_local_points': 0}
            predictions.append(prediction)
            for t, zeta, precision in recovery.points():
                point = read('point')
                if set(point) != {'kind', 'original', 'folded', 'support'}:
                    raise ValueError('point fields')
                original = ModeSet(layout.content_digest, canonical(point['original']))
                folded = ModeSet(layout.content_digest, canonical(point['folded']))
                support = SupportCertificate(canonical(point['support']))
                meta = original.certificate
                if (canonical((meta['node'], meta['zeta'], meta['precision'])) != canonical((t, zeta, precision)) or
                    canonical(meta.get('row_cancellation')) != canonical(degree) or
                    canonical(support.record.get('row_certificate')) != canonical(degree)):
                    raise ValueError('point node, precision or row premise changed')
                verify_support(call, layout, original, folded, support, budget=budget)
                ar = _arithmetic(call, precision, budget)
                total = ar.zero
                for values in support.record['tuples']:
                    beta = ExponentTuple(folded.content_digest, tuple(values))
                    children = reference_children(call, layout, folded, beta)
                    if len(children) != 64 or any(64*c.edge_count > 6*call.edge_count or
                            c.edge_count >= call.edge_count for c in children):
                        raise ValueError('independent child shrink failed')
                    if any(max((len(v.ports) for v in c.vertices), default=0) >
                           max(call.maximum_degree, 2 << layout.a) for c in children):
                        raise ValueError('independent child degree failed')
                    product = ar.one
                    dependencies = []
                    for child in children:
                        child_call = child.as_parent(call)
                        child_value = visit(child_call)
                        product = ar.mul(product, child_value)
                        dependencies.append({'child': child.content_digest, 'parent': child_call.content_digest,
                            'wires': child.edge_count, 'precision': child.precision, 'value': child_value})
                        budget.transitions += 1
                    term = read('term')
                    if canonical(term) != canonical({'kind': 'term', 'parent': call.content_digest,
                            'beta': values, 'children': dependencies, 'product': product}):
                        raise ValueError('independent numerical contribution differs')
                    total = ar.add(total, product)
                    budget.tuples += 1
                budget.tick(ar.used)
                budget.points += 1
                prediction['actual_local_points'] += 1
                point_value = read('point_value')
                if canonical(point_value) != canonical({'kind': 'point_value', 'parent': call.content_digest, 'value': total}):
                    raise ValueError('point accumulation differs')
                recovery.add(t, zeta, precision, total[0])
            result = recovery.finish()
            end = read('end')
            if (set(end) != {'kind', 'parent', 'key', 'result'} or end['parent'] != call.content_digest or
                    end['key'] != key or canonical(end['result']) != canonical(result)):
                raise ValueError('recursive recovery result mismatch')
            cache.put(key, result)
            return result

        result = visit(parent)
        if next(stream, None) is not None:
            raise ValueError('unconsumed recursive events')
        if (canonical(result) != canonical(report['result']) or chain != report['evidence_chain'] or
                byte_count != report['evidence_bytes'] or requests != report['requests'] or
                canonical(cache.report()) != canonical(report['cache'])):
            raise ValueError('stream result, coverage or cache accounting mismatch')
        for field in ('actual_calls', 'maximum_depth', 'point_evaluations', 'tuples', 'transitions'):
            if budget.report()[field] != report['ledger'][field]:
                raise ValueError('recursive ledger mismatch: '+field)
        for name, value in (('active_calls_by_depth', active), ('largest_active_edges_by_depth', sizes),
                            ('largest_deformation_degree_by_depth', degrees), ('point_accounting', predictions)):
            if canonical(report.get(name)) != canonical(value):
                raise ValueError('altered execution accounting: '+name)
        ledger = report['ledger']
        charges = ledger['stage_work_units']
        if (report.get('point_predictions_reconcile') is not True or
            ledger.get('stage_sum_reconciles') is not True or
            any(type(x) is not int or x < 0 for x in charges.values()) or
            sum(charges.values()) != ledger['work_units'] or
            charges.get('preflight', 0) != report['preflight_work_units'] or
            ledger.get('bit_operations') is not None or
            ledger.get('bit_operation_measurement') != 'NOT_INSTRUMENTED'):
            raise ValueError('work-charge reconciliation differs')
        return {'status': 'PASS_INDEPENDENT_NUMERICAL_REPLAY', 'result': result,
                'evidence_chain': chain, 'source_qualified': False, 'ledger': budget.report()}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError, StopIteration) as exc:
        return {'status': getattr(exc, 'status', 'INVALID_STREAMED_RECURSION'), 'reason': str(exc),
                'source_qualified': False, 'ledger': budget.report()}
