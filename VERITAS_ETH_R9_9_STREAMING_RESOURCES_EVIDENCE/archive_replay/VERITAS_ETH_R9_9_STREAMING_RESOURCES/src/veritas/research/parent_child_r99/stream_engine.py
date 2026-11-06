"""Finite full-grid packet recursion with bounded reuse and pre-order evidence.

No source qualification and no oracle result substitution. Call caps count
cache misses; work caps also charge every request, including cache hits.
"""
from hashlib import sha256

from veritas.research.parent_child_r98.constructor import construct_children
from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.model import Budget, ExponentTuple, Refusal, Semantics, canonical
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.tapered_v4.provenance import source_binding
from .basis import build_packet_modes
from .engine import _topology
from .execution import ExecutionSpec, TupleStrategy
from .recovery import packet_points
from .resources import ExactCache, computation_key
from .row_degree import certify_row_degree
from .stream_recovery import StreamRecovery
from .support import fold_source_forms, build_support
from .support_check import verify_support


def contract_streaming(parent, *, schedule=((1, 1),), policy=DEFAULT_SHRINKING_POLICY,
                       max_points=256, cache_bytes=1_000_000, evidence_sink=None, layout_factory=None):
    budget = Budget(policy)
    binding = source_binding()['digest']
    chain, evidence_bytes, requests = '0'*64, 0, 0
    try:
        spec = ExecutionSpec(schedule=schedule, tuples=TupleStrategy.SUPPORT, max_points=max_points)
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise Refusal('INCONCLUSIVE_SOURCE_REFINEMENT', 'streaming executor is finite only')
        if type(cache_bytes) is not int or not 0 <= cache_bytes <= policy.max_certificate_bytes:
            raise ValueError('cache exceeds explicit payload budget')
        cache = ExactCache(cache_bytes)

        def emit(record):
            nonlocal chain, evidence_bytes
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
            budget.tick()
            if (call.edge_count > policy.max_edges or call.precision > policy.max_precision or
                    call.depth > policy.max_depth):
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'streaming recursive dimensions')
            depth = call.depth - parent.depth
            remaining = schedule[depth:]
            key = computation_key(call, remaining)
            cached = cache.get(key)
            if cached is not None:
                emit({'kind': 'reuse', 'parent': call.content_digest, 'key': key})
                return cached
            budget.call(call.depth)
            if call.edge_count <= 4:
                result = leaf(call, budget)
                emit({'kind': 'leaf', 'parent': call.content_digest, 'key': key, 'result': result})
                cache.put(key, result)
                return result
            if depth >= len(schedule):
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'schedule exhausted above four-edge leaves')
            a, u = schedule[depth]
            if layout_factory is None:
                if (a, u) != (1, 1):
                    raise ValueError('default packer requires a=u=1')
                layout = construct_vertex_shrinking_layout(call, budget=budget)
            else:
                layout = layout_factory(call, a, u, budget)
            if (layout.a, layout.u, layout.source['r']) != (a, u, 64):
                raise ValueError('streaming layout schedule mismatch')
            if not audit_layout(call, layout)['group_load_bound_met']:
                raise Refusal('INCONCLUSIVE_SOURCE_PACKING', 'actual group load failure')
            recovery = StreamRecovery(call, layout, budget=budget, max_points=max_points)
            row_certificate = certify_row_degree(call, a, budget=budget)
            emit({'kind': 'start', 'parent': call.content_digest, 'key': key,
                  'layout': {'a': a, 'u': u, 'source': layout.source, 'strategy': layout.strategy},
                  'row_certificate': row_certificate})
            for t, zeta, precision in packet_points(call, layout, recovery.plan, budget=budget, max_points=max_points, streaming=True):
                original = build_packet_modes(call, layout, t, zeta, budget=budget, row_certificate=row_certificate)
                folded = fold_source_forms(call, layout, original, budget=budget)
                support = build_support(original, folded, budget=budget, row_certificate=row_certificate)
                verify_support(call, layout, original, folded, support, budget=budget)
                emit({'kind': 'point', 'original': original.certificate, 'folded': folded.certificate,
                      'support': support.record})
                ring = JetRing(ExtensionRing(precision, call.defining_polynomial,
                               max_precision_bits=policy.max_precision), 1)
                total = ring.zero
                for values in support.record['tuples']:
                    beta = ExponentTuple(folded.content_digest, tuple(values))
                    children = construct_children(call, layout, folded, beta, budget=budget,
                                                  _admitted=True, require_shrink=True)
                    _topology(call, layout, folded, beta, children, budget, True)
                    product = ring.one
                    for child in children:
                        product = ring.mul(product, visit(child.as_parent(call)))
                        budget.tick(ring.base.e**2)
                        budget.transitions += 1
                    total = ring.add(total, product)
                    budget.tuples += 1
                budget.points += 1
                recovery.add(t, zeta, precision, total[0])
            result = recovery.finish()
            emit({'kind': 'end', 'parent': call.content_digest, 'key': key, 'result': result})
            cache.put(key, result)
            return result

        result = visit(parent)
        if source_binding()['digest'] != binding:
            raise ValueError('source changed during streaming run')
        return {'status': 'PASS_FINITE_STREAMED_TAPERED_RECURSION', 'result': result,
                'parent_digest': parent.content_digest, 'implementation_source_sha256': binding,
                'schedule': schedule, 'max_points': max_points, 'cache': cache.report(),
                'requests': requests, 'ledger': budget.report(), 'evidence_chain': chain,
                'evidence_bytes': evidence_bytes, 'evidence_stream_written': evidence_sink is not None,
                'source_tapered_functional_used': bool(budget.points), 'original_weighted_stream_enumerated': False,
                'source_qualified': False, 'theorem_mode_enabled': False}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError, OSError) as exc:
        return {'status': getattr(exc, 'status', 'INCONCLUSIVE_STREAMED_RECURSION'),
                'reason': str(exc), 'ledger': budget.report(), 'requests': requests,
                'source_qualified': False, 'theorem_mode_enabled': False}
