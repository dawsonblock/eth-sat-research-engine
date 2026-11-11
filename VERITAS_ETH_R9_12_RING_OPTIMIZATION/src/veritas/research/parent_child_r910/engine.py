"""Finite degree-certified tapered recursion with explicit numerical dependencies.

No source qualification and no oracle result substitution. Call caps count
cache misses; work caps also charge every request, including cache hits.
"""
from hashlib import sha256

from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.model import ExponentTuple, Refusal, Semantics, canonical
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.tapered_v4.provenance import source_binding
from veritas.research.parent_child_r99.basis import build_packet_modes
from veritas.research.parent_child_r99.engine import _topology
from veritas.research.parent_child_r99.execution import ExecutionSpec, TupleStrategy
from veritas.research.parent_child_r99.resources import ExactCache, computation_key
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r912.jet_recovery import JetRecovery as Recovery
from .accounting import AccountedBudget
from veritas.research.cost_ledger_bridge import RecursiveVisitTracker
from veritas.research.parent_child_r99.support import fold_source_forms, build_support
from veritas.research.parent_child_r99.support_check import verify_support


def contract(parent, *, schedule=((1, 1),), policy=DEFAULT_SHRINKING_POLICY,
                       max_points=256, cache_bytes=1_000_000, evidence_sink=None, layout_factory=None,
                       preflight_work=0, oracle_limits=None, coefficient_encoding=False, compressed_records=False,
                       conformance=None):
    budget = AccountedBudget(policy, oracle_limits)
    tracker = RecursiveVisitTracker(policy)
    if conformance not in (None, 'report', 'strict'):
        raise ValueError("conformance must be None, 'report' or 'strict'")
    audit = None
    if conformance is not None:
        from veritas.research.parent_child_r912.conformance import NodeAudit
        audit = NodeAudit(strict=conformance == 'strict')
    binding = source_binding()['digest']
    chain, evidence_bytes, requests = '0'*64, 0, 0
    active, sizes, degrees = {}, {}, {}
    work_predictions = []
    try:
        if type(preflight_work) is not int or preflight_work < 0:
            raise ValueError('nonnegative preflight work required')
        with budget.at('preflight'):
            budget.tick(preflight_work)
        spec = ExecutionSpec(schedule=schedule, tuples=TupleStrategy.SUPPORT, max_points=max_points)
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise Refusal('INCONCLUSIVE_SOURCE_REFINEMENT', 'streaming executor is finite only')
        if type(cache_bytes) is not int or not 0 <= cache_bytes <= policy.max_certificate_bytes:
            raise ValueError('cache exceeds explicit payload budget')
        cache = ExactCache(cache_bytes)

        def emit(record):
            nonlocal chain, evidence_bytes
            if coefficient_encoding:
                from veritas.research.parent_child_r912.coefficient_writer import encode_point
                record = encode_point(record)
            if compressed_records:
                from veritas.research.parent_child_r912.record_writer import pack_record
                record = pack_record(record)
            raw = canonical(record)
            evidence_bytes += len(raw)
            if evidence_bytes > policy.max_certificate_bytes:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'streamed evidence budget')
            chain = sha256(bytes.fromhex(chain) + raw).hexdigest()
            if evidence_sink is not None:
                evidence_sink(raw)
            budget.tick()

        def visit(call):
            nonlocal requests
            requests += 1
            tracker.request()
            budget.tick()
            if (call.edge_count > policy.max_edges or call.precision > policy.max_precision or
                    call.depth > policy.max_depth):
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'streaming recursive dimensions')
            depth = call.depth - parent.depth
            remaining = schedule[depth:]
            key = computation_key(call, remaining)
            cached = cache.get(key)
            tracker.cache_lookup(key, hit=cached is not None)
            if cached is not None:
                emit({'kind': 'reuse', 'parent': call.content_digest, 'key': key})
                return cached
            budget.call(call.depth)
            if call.edge_count <= 4:
                tracker.note_leaf()
                with budget.at('leaf_arithmetic'):
                    result = leaf(call, budget)
                emit({'kind': 'leaf', 'parent': call.content_digest, 'key': key, 'result': result})
                cache.put(key, result)
                return result
            if depth >= len(schedule):
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'schedule exhausted above four-edge leaves')
            a, u = schedule[depth]
            if layout_factory is None:
                from veritas.research.parent_child_r912.layout import finite_layout
                layout = finite_layout(call, a, u, budget)
            else:
                layout = layout_factory(call, a, u, budget)
            if (layout.a, layout.u, layout.source['r']) != (a, u, 64):
                raise ValueError('streaming layout schedule mismatch')
            if not audit_layout(call, layout)['group_load_bound_met']:
                raise Refusal('INCONCLUSIVE_SOURCE_PACKING', 'actual group load failure')
            if audit is not None:
                from veritas.research.parent_child_r912 import conformance as theorem
                from veritas.research.paper_verification.exact_parameters import hermite_parameters
                packing = theorem.layout_packing_check(call, layout)
                audit.add(call, 'packet_count', packing, depth=depth, a=a, u=u)
                hermite = hermite_parameters(call.edge_count, a, u, call.precision,
                                             max_wires=policy.max_edges, max_precision=policy.max_precision)
                node_info = {n[0]: n for n in hermite['nodes']}
                checked_nodes = set()
            with budget.at('row_degree'):
                row_certificate = certify_row_degree(call, a, budget=budget)
            with budget.at('hermite_plan'):
                recovery = Recovery(call, layout, row_certificate, budget=budget, max_points=max_points)
            active[str(depth)] = active.get(str(depth), 0)+1
            sizes[str(depth)] = max(sizes.get(str(depth), 0), call.edge_count)
            degrees[str(depth)] = max(degrees.get(str(depth), 0), row_certificate['degree_bound'])
            work_predictions.append({'parent': call.content_digest,
                'expected_local_points': recovery.description['actual_point_count'],
                'generic_local_points': recovery.description['generic_point_count'],
                'actual_local_points': 0})
            prediction = work_predictions[-1]
            emit({'kind': 'start', 'parent': call.content_digest, 'key': key,
                  'layout': {'a': a, 'u': u, 'source': layout.source, 'strategy': layout.strategy},
                  'row_certificate': row_certificate, 'recovery': recovery.description})
            for t, zeta, precision in recovery.points():
                with budget.at('modes_and_support'):
                    original = build_packet_modes(call, layout, t, zeta, budget=budget, row_certificate=row_certificate)
                    folded = fold_source_forms(call, layout, original, budget=budget)
                    support = build_support(original, folded, budget=budget, row_certificate=row_certificate)
                    verify_support(call, layout, original, folded, support, budget=budget)
                emit({'kind': 'point', 'original': original.certificate, 'folded': folded.certificate,
                      'support': support.record})
                if audit is not None and t not in checked_nodes:
                    checked_nodes.add(t)
                    _, i, _, Dt, p_t = node_info[t]
                    L, M = 1 << a, call.edge_count
                    modes_v = theorem.mode_check(original.certificate['modes'], P=packing['padded_packets'],
                                                 i=i, L=L, M=M, Dt=Dt, packed=packing['hypotheses_met'])
                    audit.add(call, 'mode_multiplicity', modes_v, depth=depth, node=t)
                    prec_v = theorem.precision_check(M=M, a=a, u=u, i=i, p=call.precision,
                                                     h=hermite['h'], Dt=Dt, precision=precision)
                    audit.add(call, 'precision_bound', prec_v, depth=depth, node=t)
                    audit.add(call, 'tuple_count', theorem.tuple_check(
                        weighted_count=original.certificate['mode_tuple_count'],
                        support_tuples=support.record['tuples'],
                        support_weights=[m['weight'] for m in folded.certificate['modes']],
                        precision=precision, M=M, u=u,
                        upstream=packing['hypotheses_met'] and modes_v['hypotheses_met'] and
                        prec_v['hypotheses_met']), depth=depth, node=t)
                ring = JetRing(ExtensionRing(precision, call.defining_polynomial,
                               max_precision_bits=policy.max_precision), call.jet_length)
                total = ring.zero
                for values in support.record['tuples']:
                    beta = ExponentTuple(folded.content_digest, tuple(values))
                    with budget.at('child_construction'):
                        children = construct_children(call, layout, folded, beta, budget=budget,
                                                  _admitted=True, require_shrink=True)
                        _topology(call, layout, folded, beta, children, budget, True)
                    product = ring.one
                    dependencies = []
                    for child in children:
                        child_call = child.as_parent(call)
                        with tracker.child_frame():
                            with budget.at('control'):
                                child_value = visit(child_call)
                        product = ring.mul(product, child_value)
                        tracker.charge('jet_mul', ring.base.e**2 * call.jet_length**2)
                        dependencies.append({'child': child.content_digest, 'parent': child_call.content_digest,
                            'wires': child.edge_count, 'precision': child.precision, 'value': child_value})
                        budget.tick(ring.base.e**2 * call.jet_length**2)
                        budget.transitions += 1
                    emit({'kind': 'term', 'parent': call.content_digest, 'beta': values,
                          'children': dependencies, 'product': product})
                    total = ring.add(total, product)
                    budget.tuples += 1
                budget.points += 1
                prediction['actual_local_points'] += 1
                emit({'kind': 'point_value', 'parent': call.content_digest, 'value': total})
                with budget.at('interpolation'):
                    recovery.add(t, zeta, precision, total)
            result = recovery.finish()
            emit({'kind': 'end', 'parent': call.content_digest, 'key': key, 'result': result})
            cache.put(key, result)
            return result

        result = visit(parent)
        if source_binding()['digest'] != binding:
            raise ValueError('source changed during streaming run')
        budget.tick(0)
        extra = {} if audit is None else {'theorem_conformance': audit.report()}
        return {**extra, 'schema': 'VERITAS_R912_NUMERICAL_V1' if coefficient_encoding or compressed_records else 'VERITAS_R910_NUMERICAL_V1',
                'status': 'PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION', 'result': result,
                'parent_digest': parent.content_digest, 'implementation_source_sha256': binding,
                'active_calls_by_depth': active, 'largest_active_edges_by_depth': sizes,
                'largest_deformation_degree_by_depth': degrees,
                'point_accounting': work_predictions,
                'preflight_work_units': preflight_work,
                'point_predictions_reconcile': all(r['expected_local_points'] == r['actual_local_points'] for r in work_predictions),
                'recovery_optimization': 'CERTIFIED_ZERO_TAIL_ORIGINAL_FUNCTIONAL',
                'schedule': schedule, 'max_points': max_points, 'cache': cache.report(),
                'requests': requests, 'ledger': budget.report(), 'tree_ledger': tracker.finalize(budget),
                'evidence_chain': chain,
                'evidence_bytes': evidence_bytes, 'evidence_stream_written': evidence_sink is not None,
                'source_tapered_functional_used': bool(budget.points), 'original_weighted_stream_enumerated': False,
                'source_qualified': False, 'theorem_mode_enabled': False}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError, OSError) as exc:
        extra = {} if audit is None else {'theorem_conformance': audit.report()}
        return {**extra, 'status': getattr(exc, 'status', 'INCONCLUSIVE_STREAMED_RECURSION'),
                'reason': str(exc), 'resource_failure': getattr(exc, 'resource_failure', None),
                'ledger': budget.report(), 'tree_ledger': tracker.finalize(budget),
                'requests': requests,
                'source_qualified': False, 'theorem_mode_enabled': False}
