"""Checked finite transfer summation at one singleton-packet point.

This is a distinct execution contract: it computes one representative child
for each local binary mode state and sums the complete coefficient polynomial
by matrix multiplication. It does not change the ordinary full-tuple driver,
perform Hermite recovery, or qualify source recursion.
"""

from itertools import product

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.tapered_v4.provenance import source_binding

from .engine import leaf
from .model import Budget, PacketLayout, ParentCall, Refusal, Semantics, canonical
from .shrinking_engine import DEFAULT_SHRINKING_POLICY
from .shrinking_layout import audit_vertex_shrinking_layout
from .transfer_basis import build_transfer_basis
from .transfer_children import TransferChildren
from .transfer_verify import verify_transfer_certificate


def _cycle_order(groups, modes, *, budget=None):
    """Find the unique simple cycle, leaving isolated groups explicit."""
    if budget is not None:
        budget.tick(groups)
    adjacency = [[] for _ in range(groups)]
    pairs = set()
    for index, mode in enumerate(modes):
        if budget is not None:
            budget.tick()
        a, b = mode['source_group'], mode['target_group']
        if type(a) is not int or type(b) is not int or not 0 <= a < groups or not 0 <= b < groups or a == b:
            raise ValueError('invalid transfer mode endpoints')
        pair = (min(a, b), max(a, b))
        if pair in pairs:
            raise Refusal('INCONCLUSIVE_TRANSFER_TOPOLOGY', 'parallel crossing modes are not a simple cycle')
        pairs.add(pair)
        adjacency[a].append((b, index))
        adjacency[b].append((a, index))
    active = [g for g, entries in enumerate(adjacency) if entries]
    if not active:
        return adjacency, (), ()
    if len(active) < 3 or any(len(adjacency[g]) != 2 for g in active):
        raise Refusal('INCONCLUSIVE_TRANSFER_TOPOLOGY', 'crossing modes must form one simple cycle')
    nodes, edges, visited = [], [], set()
    start, previous, current = min(active), None, min(active)
    while True:
        if budget is not None:
            budget.tick()
        if current in visited:
            raise Refusal('INCONCLUSIVE_TRANSFER_TOPOLOGY', 'crossing graph has repeated cycle vertex')
        visited.add(current)
        nodes.append(current)
        options = sorted((other, mid) for other, mid in adjacency[current] if other != previous)
        other, mid = options[0]
        edges.append(mid)
        if other == start:
            break
        previous, current = current, other
    if len(visited) != len(active) or len(edges) != len(modes):
        raise Refusal('INCONCLUSIVE_TRANSFER_TOPOLOGY', 'crossing graph is not one connected simple cycle')
    return adjacency, tuple(nodes), tuple(edges)


def _multiply_cycle(ring, adjacency, nodes, edges, group_values, *, budget=None):
    # Work units count extension-coordinate multiplications and additions;
    # integer bit costs remain outside this cooperative accounting.
    pairs = ring.length * (ring.length + 1) // 2
    multiply_cost = (ring.base.e ** 2 + ring.base.e) * pairs
    add_cost = ring.base.e * ring.length
    result = ring.one
    for group, incident in enumerate(adjacency):
        if budget is not None:
            budget.tick()
        if not incident:
            if budget is not None:
                budget.tick(multiply_cost)
            result = ring.mul(result, group_values[group][0])
    if not nodes:
        return result
    matrix = ((ring.one, ring.zero), (ring.zero, ring.one))
    for i, group in enumerate(nodes):
        if budget is not None:
            budget.tick(1 + 8 * multiply_cost + 4 * add_cost)
        previous_edge, next_edge = edges[i - 1], edges[i]
        indices = tuple(sorted(mid for _, mid in adjacency[group]))
        factor = []
        for previous in (0, 1):
            row = []
            for following in (0, 1):
                assignment = {previous_edge: previous, next_edge: following}
                bits = tuple(assignment[mid] for mid in indices)
                row.append(group_values[group][2 * bits[0] + bits[1]])
            factor.append(tuple(row))
        matrix = tuple(tuple(ring.add(ring.mul(matrix[a][0], factor[0][b]),
                                      ring.mul(matrix[a][1], factor[1][b]))
                             for b in (0, 1)) for a in (0, 1))
    if budget is not None:
        budget.tick(multiply_cost + add_cost)
    return ring.mul(result, ring.add(matrix[0][0], matrix[1][1]))


def evaluate_cycle_transfer(parent, layout, node, zeta, *, policy=None, budget=None):
    """Compute and independently certify a complete finite point value.

    All generated children must already be <=4 edges. At each group the local
    states use representative global binary tuples with all nonincident bits
    zero. Their contractions are computed by the ordinary direct leaf routine.
    The independent certificate consumer reconstructs every actual child and
    every group value, and separately eliminates the complete binary mode sum.
    """
    if budget is None:
        policy = DEFAULT_SHRINKING_POLICY if policy is None else policy
        budget = Budget(policy)
    elif policy is not None:
        raise TypeError('supply either policy or shared budget')
    else:
        policy = budget.policy
    try:
        if type(parent) is not ParentCall or type(layout) is not PacketLayout:
            raise ValueError('typed parent and packet layout required')
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
            raise ValueError('cycle transfer requires finite scaled semantics')
        implementation = source_binding()['digest']
        budget.call(parent.depth)
        packing = audit_vertex_shrinking_layout(parent, layout)
        modes = build_transfer_basis(parent, layout, node, zeta, budget=budget)
        m = modes.certificate
        groups = layout.source['r']
        adjacency, cycle_nodes, cycle_edges = _cycle_order(groups, m['modes'], budget=budget)
        if len(m['modes']) >= m['precision']:
            raise Refusal('INCONCLUSIVE_TRANSFER_WEIGHT', 'all binary tuples must be within the precision weight budget')
        required = 1 + sum(1 << len(incident) for incident in adjacency)
        # The point call was already charged above; existing shared-budget
        # calls must also be reserved before constructing any local child.
        if budget.calls + required - 1 > policy.max_calls:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'complete local-state calls exceed policy')
        children = TransferChildren(parent, layout, modes, budget=budget)
        ring = JetRing(ExtensionRing(m['precision'], parent.defining_polynomial,
                                     max_precision_bits=policy.max_precision), 1)
        group_records, group_values, evidence_bytes = [], [], 0
        for group, incident in enumerate(adjacency):
            indices = tuple(sorted(mid for _, mid in incident))
            values, serialized = [], []
            for state in product((0, 1), repeat=len(indices)):
                beta = [0] * len(m['modes'])
                for index, value in zip(indices, state):
                    beta[index] = value
                child = children.child(group, tuple(beta))
                budget.call(child.depth)
                value = leaf(child.as_parent(parent), budget)
                budget.transitions += 1
                child_bytes = child.serialize()
                evidence_bytes += len(child_bytes) + len(canonical(value))
                if evidence_bytes > policy.max_certificate_bytes:
                    raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'transfer child evidence byte cap')
                serialized.append(child_bytes.decode('ascii'))
                values.append(value)
            group_values.append(values)
            group_records.append({'group': group, 'mode_indices': list(indices),
                                  'values': [[list(row) for row in value] for value in values],
                                  'children': serialized})
        result = _multiply_cycle(ring, adjacency, cycle_nodes, cycle_edges, group_values,
                                 budget=budget)
        inventory = [[mode['packet'], mode['rows'][0][0], mode['source_group'], mode['target_group']]
                     for mode in m['modes']]
        payload = canonical({'schema': 'VERITAS_R98_CYCLE_TRANSFER_POINT_V1',
            'parent_digest': parent.content_digest, 'layout_digest': layout.content_digest,
            'node': node, 'zeta': list(zeta), 'precision': m['precision'], 'modes': inventory,
            'groups': group_records, 'result': [list(row) for row in result]})
        if len(payload) > policy.max_certificate_bytes:
            raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'transfer point certificate byte cap')
        checked = verify_transfer_certificate(parent, layout, payload, budget=budget,
                                              expected_point=(node, tuple(zeta), m['precision']))
        if not checked['status'].startswith('PASS_'):
            reason = checked.get('reason', 'certificate rejected')
            if checked['status'].startswith('INCONCLUSIVE_'):
                raise Refusal(checked['status'], reason)
            raise ValueError('independent transfer certificate rejected: ' + reason)
        if checked['result'] != result:
            raise ValueError('independent transfer certificate returned a different value')
        # The independent verifier also checks the original half-edge point;
        # it never supplies a production value or a fallback.
        if source_binding()['digest'] != implementation:
            raise ValueError('implementation source changed during transfer execution')
        budget.tick(0)
        budget.points += 1
        return {'status': 'PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT', 'result': result,
            'certificate': payload, 'source_qualified': False, 'theorem_mode_enabled': False,
            'scaled_experiment': True, 'parent_digest': parent.content_digest,
            'implementation_source_sha256': implementation, 'group_count': groups,
            'parent_edges': parent.edge_count, 'point_precision': m['precision'],
            'crossing_pairs': len(m['cross_pairs']), 'retained_modes': len(m['modes']),
            'complete_weighted_tuple_count': m['mode_tuple_count'],
            'potentially_nonzero_binary_tuple_count': 1 << len(m['modes']),
            'zero_exponent_proof': 'SINGLETON_TARGET_AFFINE_ROW_DEGREE_AT_MOST_ONE',
            'locality': 'CHECKED_AGAINST_INDEPENDENT_CHILD_RECIPES',
            'tuple_completeness': 'COMPLETE_SUM_ALGEBRAICALLY_AGGREGATED',
            'global_tuple_stream_enumerated': False,
            'transition_scope': 'REPRESENTATIVE_LOCAL_GROUP_CHILD',
            'all_actual_children_are_leaves': True, 'packing': packing,
            'cycle_groups': len(cycle_nodes), 'independent_certificate': checked['status'],
            'independent_point_oracle': 'PASS_HALF_EDGE_ELIMINATION',
            'full_hermite_grid': 'NOT_RUN', 'parent_contraction_recovered': False,
            'bit_time_bound_status': 'COMPLEXITY_NOT_ESTABLISHED',
            'peak_space_bound_status': 'COMPLEXITY_NOT_ESTABLISHED', 'ledger': budget.report()}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, RuntimeError, MemoryError) as exc:
        return {'status': getattr(exc, 'status', 'INCONCLUSIVE_CYCLE_TRANSFER_POINT'),
            'reason': str(exc), 'source_qualified': False, 'theorem_mode_enabled': False,
            'scaled_experiment': True, 'ledger': budget.report()}
