"""Actual shrinking finite recursion with certified row-degree optimization.

All successful leaves have at most four edges. The optional event sink lets
the caller stream evidence; the engine retains only each active node's grid.
No contraction oracle is called, and no source semantics are admitted.
"""
from hashlib import sha256

from veritas.research.parent_child_r98.engine import leaf
from veritas.research.parent_child_r98.model import Budget, Refusal, Semantics, canonical
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.tapered_v4.provenance import source_binding
from .basis import build_packet_modes
from .degree_recovery import degree_points, recover_degree_grid
from .row_degree import certify_row_degree
from .supported_engine import evaluate_supported_point


def contract_supported_recursion(parent, *, schedule=((1, 1), (1, 1)), layout_factory=None,
                                 policy=DEFAULT_SHRINKING_POLICY, max_points=256, evidence_sink=None):
    budget = Budget(policy)
    binding = source_binding()['digest']
    chain, evidence_bytes = '0' * 64, 0
    sizes, active_calls, nonconstant_calls, crossing_calls = {}, {}, {}, {}
    max_precision = parent.precision
    try:
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise Refusal('INCONCLUSIVE_SOURCE_REFINEMENT', 'supported recursion is finite only')
        if (type(schedule) is not tuple or not schedule or len(schedule) > policy.max_depth or
            any(type(pair) is not tuple or len(pair) != 2 or
                any(type(x) is not int for x in pair) or not 1 <= pair[1] <= pair[0] <= 3 for pair in schedule)):
            raise ValueError('explicit finite depth schedule required')
        if type(max_points) is not int or not 1 <= max_points <= 4096:
            raise ValueError('degree point cap must be 1..4096')

        def emit(record):
            nonlocal chain, evidence_bytes
            raw = canonical(record)
            evidence_bytes += len(raw)
            if evidence_bytes > policy.max_certificate_bytes:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'streamed recursive evidence cap')
            chain = sha256(bytes.fromhex(chain) + raw).hexdigest()
            if evidence_sink is not None:
                evidence_sink(raw)
            budget.tick()

        def visit(call):
            nonlocal max_precision
            budget.call(call.depth)
            if call.edge_count > policy.max_edges or call.precision > policy.max_precision:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'supported recursive dimension cap')
            depth = call.depth - parent.depth
            sizes[depth] = max(sizes.get(depth, 0), call.edge_count)
            max_precision = max(max_precision, call.precision)
            if call.edge_count <= 4:
                return leaf(call, budget)
            if depth >= len(schedule):
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'schedule exhausted above four-edge leaf threshold')
            a, u = schedule[depth]
            if layout_factory is None:
                if (a, u) != (1, 1):
                    raise ValueError('default finite vertex packer requires a=u=1')
                layout = construct_vertex_shrinking_layout(call, budget=budget)
            else:
                layout = layout_factory(call, a, u, budget)
            packing = audit_layout(call, layout)
            if (layout.a, layout.u, layout.source['r']) != (a, u, 64):
                raise ValueError('supported layout differs from depth schedule')
            if not packing['group_load_bound_met']:
                raise Refusal('INCONCLUSIVE_SOURCE_PACKING', 'actual group loads do not imply shrink')
            degree = certify_row_degree(call, a, budget=budget)
            grid = tuple(degree_points(call, layout, degree, budget=budget, max_points=max_points))
            if budget.calls + 64 * len(grid) > policy.max_calls:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'supported recursive grid call lower bound')
            active_calls[depth] = active_calls.get(depth, 0) + 1
            if degree['nonconstant_row_ports']:
                nonconstant_calls[depth] = nonconstant_calls.get(depth, 0) + 1
            rows, row_bytes = [], 0
            for t, zeta, precision in grid:
                modes = build_packet_modes(call, layout, t, zeta, budget=budget)
                if modes.certificate['modes']:
                    crossing_calls[depth] = crossing_calls.get(depth, 0) + 1
                value, point = evaluate_supported_point(call, layout, modes, budget=budget,
                    contractor=visit, require_shrink=True, row_certificate=degree)
                row = [t, list(zeta), precision, list(value[0])]
                row_bytes += len(canonical(row))
                if row_bytes > policy.max_certificate_bytes:
                    raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'active degree grid byte cap')
                rows.append(row)
                emit({'kind': 'point', 'depth': call.depth, 'certificate': point})
            result, recovery = recover_degree_grid(call, layout, degree, rows, budget=budget, max_points=max_points)
            emit({'kind': 'recovery', 'depth': call.depth, 'parent_digest': call.content_digest,
                  'parent_edges': call.edge_count,
                  'layout': {'a': layout.a, 'u': layout.u, 'strategy': layout.strategy, 'source': layout.source},
                  'rows': rows, 'certificate': recovery, 'result': result})
            return result

        result = visit(parent)
        if source_binding()['digest'] != binding:
            raise ValueError('source changed during supported recursive execution')
        return {'status': 'PASS_FINITE_SUPPORTED_SHRINKING_RECURSION', 'result': result,
                'parent_digest': parent.content_digest, 'implementation_source_sha256': binding,
                'largest_edges_by_depth': {str(k): v for k, v in sizes.items()},
                'active_calls_by_depth': {str(k): v for k, v in active_calls.items()},
                'nonconstant_active_calls_by_depth': {str(k): v for k, v in nonconstant_calls.items()},
                'crossing_points_by_depth': {str(k): v for k, v in crossing_calls.items()},
                'maximum_precision': max_precision, 'evidence_chain': chain, 'evidence_bytes': evidence_bytes,
                'evidence_stream_written': evidence_sink is not None, 'ledger': budget.report(),
                'every_child_shrink': 'CHECKED_64_M_CHILD_LE_6_M', 'leaf_threshold': 4,
                'source_qualified': False, 'theorem_mode_enabled': False,
                'original_weighted_stream_enumerated': False,
                'source_tapered_functional_used': False, 'per_point_independent_oracle_status': 'NOT_RUN_IN_PRODUCTION'}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError, OSError) as exc:
        return {'status': getattr(exc, 'status', 'INCONCLUSIVE_SUPPORTED_RECURSION'), 'reason': str(exc),
                'ledger': budget.report(), 'source_qualified': False, 'theorem_mode_enabled': False}
