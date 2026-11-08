"""Topology and necessary cost conditions, without tensor entry evaluation.

Bounds describe the present recomputing executor, not an algorithmic lower
bound for contraction. No successful report supplies a contraction value or
certifies that an upper time/memory budget is sufficient.
"""
from dataclasses import dataclass
from math import comb

from veritas.research.parent_child_r98.group_preflight import Topology, topology_of, _project
from veritas.research.parent_child_r98.model import Budget, Refusal, Semantics, canonical, digest
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.paper_verification.exact_parameters import hermite_parameters
from .execution import ExecutionSpec, RecoveryKind, ScheduleKind


def two_level_call_floor():
    """64 groups, per-side 3M/64, <=4 leaves, full grids, all groups per tuple.

    An active descendant needs floor(3m/64)>=1, so m>=22. Shrink then
    requires M>=ceil(64*22/6)=235. Both signs of a root node with its
    coordinate generate the same topology, at >=3M+1 points each. Each
    such point calls 63 other children and one active child requiring
    >=1+64*2*(3m+1) calls. Other nodes/tuples can only add work.
    """
    child = (64 + 2) // 3
    parent = (64 * child + 5) // 6
    descendant_calls = 1 + 64 * 2 * (3 * child + 1)
    return {'minimum_active_child_edges': child, 'minimum_parent_edges': parent,
            'minimum_calls': 1 + 2 * (3 * parent + 1) * (63 + descendant_calls),
            'scope': 'CURRENT_FULL_GRID_RECOMPUTING_64_GROUP_EXECUTOR',
            'requires_at_least_one_tuple_per_point': True,
            'applies_to_degree_shortcut': False, 'applies_to_memoized_executor': False}


@dataclass(frozen=True)
class ChildTopology:
    group: int
    topology: Topology
    edge_map: tuple
    inherited: tuple
    packet_ids: tuple


def project_packet_children(parent, layout, coordinate, precision, *, budget):
    """Reconstruct every real X/Y wire from the audited occupied slots.

    No mode builder, child constructor, tensor entry evaluator or oracle is
    called. Original vertex port order is preserved, including isolated scalars.
    """
    audit_layout(parent, layout)
    if layout.source['r'] != 64:
        raise ValueError('general topology projection requires 64 groups')
    if type(coordinate) is not int or not 0 <= coordinate < layout.u:
        raise ValueError('inactive packet coordinate')
    if type(precision) is not int or not parent.precision <= precision <= 65536:
        raise ValueError('invalid projected creation precision')
    src = layout.source
    addresses = {e: (pid, slot) for pid, packet in enumerate(src['packets'])
                 for slot, e in packet['occupied_slots']}
    assignments = [[] for _ in range(64)]
    for vertex in parent.vertices:
        labels = src['row_labels' if vertex.side == 'row' else 'column_labels']
        group = labels.get(str(vertex.vertex_id), [0] * layout.a)[coordinate]
        assignments[group].append(vertex)
    children = []
    for group, inherited in enumerate(assignments):
        mapping = []
        for v in inherited:
            half = 'Y' if v.side == 'row' else 'X'
            mapping.extend((half, edge, *addresses[edge], v.vertex_id, pos)
                           for pos, edge in enumerate(v.ports))
        mapping.sort(key=lambda item: (item[0] != 'Y', item[1]))
        index = {(item[0], item[1]): wire for wire, item in enumerate(mapping)}
        vertices = [('row', k, tuple(index['Y' if v.side == 'row' else 'X', e] for e in v.ports))
                    for k, v in enumerate(inherited)]
        packet_ids = []
        for pid, packet in enumerate(src['packets']):
            positions = tuple(index[half, e] for half in ('Y', 'X')
                              for _, e in packet['occupied_slots'] if (half, e) in index)
            if positions:
                vertices.append(('column', len(packet_ids), positions))
                packet_ids.append(pid)
            budget.tick(1 + len(packet['occupied_slots']))
        topology = Topology(len(mapping), parent.depth + 1, precision, tuple(vertices))
        children.append(ChildTopology(group, topology, tuple(mapping),
                        tuple((v.side, v.vertex_id) for v in inherited), tuple(packet_ids)))
    if sum(c.topology.edges for c in children) != 2 * parent.edge_count:
        raise ValueError('projected half-edge coverage failed')
    return tuple(children)


def verify_projected_children(parent, layout, modes, children, *, budget):
    """Independently replay actual incidence before recursive calls."""
    record = modes.certificate
    if modes.layout_digest != layout.content_digest or type(record['node']) is not int or not record['node']:
        raise ValueError('point ancestry or node')
    pars = hermite_parameters(parent.edge_count, layout.a, layout.u, parent.precision,
                             max_wires=budget.policy.max_edges, max_precision=budget.policy.max_precision)
    node = next((n for n in pars['nodes'] if n[0] == record['node']), None)
    if node is None or node[-1] != record['precision']:
        raise ValueError('point precision differs from schedule')
    expected = project_packet_children(parent, layout, node[1], node[-1], budget=budget)
    if len(children) != 64:
        raise ValueError('missing group child')
    for actual, wanted in zip(children, expected):
        if (actual.parent_digest != parent.content_digest or actual.layout_digest != layout.content_digest or
            actual.modes_digest != modes.content_digest or actual.group != wanted.group or
            topology_of(actual) != wanted.topology or actual.edge_map != wanted.edge_map or
            actual.inherited != wanted.inherited or actual.packet_ids != wanted.packet_ids):
            raise ValueError('child differs from independent port projection')
    return expected


def preflight_packet_recursion(parent, layout, spec, *, policy, descendant_strategy='unplanned'):
    """Check the supplied layout; optionally project singleton descendants.

    `singleton_first_fit` is an explicit prospective strategy for remaining
    (1,1) levels. `unplanned` checks necessary descendant conditions only.
    Counts are lower bounds unless all crossing mode sets are empty. Neither
    strategy assumes the unknown descendant tensor values are constant.
    """
    budget = Budget(policy)
    report = {'schema': 'VERITAS_R99_PACKET_PREFLIGHT_V1', 'parent_digest': parent.content_digest,
              'layout_digest': layout.content_digest, 'execution_spec_digest': spec.content_digest,
              'source_qualified': False, 'tensor_entries_evaluated': False, 'production_answer_available': False,
              'two_level_floor': two_level_call_floor(), 'blockers': [], 'nodes': [],
              'upper_runtime_status': 'NOT_ESTABLISHED', 'peak_memory_status': 'NOT_ESTABLISHED',
              'evidence_size_status': 'NOT_ESTABLISHED', 'launch_authorized_by_preflight': False}
    blockers = report['blockers']

    def block(code, **details):
        item = {'code': code, **details}
        if item not in blockers:
            blockers.append(item)

    try:
        if type(spec) is not ExecutionSpec or spec.schedule_kind is not ScheduleKind.FINITE:
            raise Refusal('INCONCLUSIVE_SOURCE_REFINEMENT', 'finite preflight cannot qualify source calls')
        if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT or spec.recovery is not RecoveryKind.TAPERED:
            raise ValueError('packet preflight requires finite full tapered execution')
        if descendant_strategy not in ('unplanned', 'singleton_first_fit'):
            raise ValueError('unknown descendant topology strategy')
        if (layout.a, layout.u) != spec.schedule[0]:
            raise ValueError('root layout differs from execution schedule')
        packing = audit_layout(parent, layout)
        report['packing'] = packing
        if layout.source['r'] != 64:
            raise ValueError('general execution group count differs')
        if parent.edge_count > policy.max_edges or parent.precision > policy.max_precision:
            block('ROOT_DIMENSIONS_EXCEED_POLICY')
        if parent.depth > policy.max_depth or len(spec.schedule) > policy.max_depth:
            block('DEPTH_POLICY')
        if not packing['group_load_bound_met']:
            block('ACTUAL_GROUP_LOADS_EXCEED_BOUND')
        extension = parent.defining_polynomial.bit_length() - 1
        if not 2 <= extension <= 12:
            block('EXTENSION_DEGREE_UNSUPPORTED')
        max_precision, max_depth = parent.precision, parent.depth
        memo = {}
        complete = True

        def visit(topology, level, root_layout=None):
            nonlocal max_precision, max_depth, complete
            budget.tick(1 + topology.edges + len(topology.vertices))
            max_precision = max(max_precision, topology.precision)
            max_depth = max(max_depth, topology.depth)
            if topology.depth > policy.max_depth:
                block('DESCENDANT_DEPTH_POLICY', depth=topology.depth)
            if topology.precision > policy.max_precision:
                block('DESCENDANT_PRECISION_POLICY', precision=topology.precision)
            if topology.edges <= 4:
                return 1
            if level >= len(spec.schedule):
                block('SCHEDULE_EXHAUSTED_ABOVE_LEAF', edges=topology.edges, depth=topology.depth)
                complete = False
                return 1
            key = topology.content_digest
            if key in memo:
                return memo[key]
            a, u = spec.schedule[level]
            M = topology.edges
            if topology.maximum_degree > 3 * M // 64:
                block('VERTEX_EXCEEDS_NEXT_SIDE_CAPACITY', edges=M, degree=topology.maximum_degree,
                      capacity=3 * M // 64, depth=topology.depth)
            pars = hermite_parameters(M, a, u, topology.precision, max_wires=1024, max_precision=65536)
            degree, nodes = pars['degree_bound'], pars['nodes']
            if degree + 1 > spec.max_points:
                block('POINT_GRID_CAP', required=degree + 1)
            if degree + 1 > 1 << extension:
                block('RESIDUE_FIELD_TOO_SMALL', required=degree + 1, available=1 << extension)
            if degree > 3072:
                block('HERMITE_REFERENCE_DEGREE_CAP', required=degree, available=3072)
            if sum(n[2] for n in nodes) > min(8192, 12 * M * (1 << a)):
                block('HERMITE_REFERENCE_MULTIPLICITY_CAP')
            raw_bytes = (degree + 1) * extension * sum((n[-1] + 7) // 8 for n in nodes)
            if raw_bytes > policy.max_certificate_bytes:
                block('DENSE_GRID_POLICY_ESTIMATE', bytes=raw_bytes)
            row = {'topology_digest': key, 'depth': topology.depth, 'edges': M, 'a': a, 'u': u,
                   'degree': degree, 'points_per_node': degree + 1, 'node_count': len(nodes),
                   'dense_coordinate_payload_bytes': raw_bytes, 'coordinates': []}
            report['nodes'].append(row)
            calls = 1
            by_coordinate = {}
            for t, coordinate, multiplicity, _, precision in nodes:
                max_precision = max(max_precision, precision)
                if precision > policy.max_precision:
                    block('POINT_PRECISION_POLICY', required=precision)
                if coordinate not in by_coordinate:
                    if precision > 65536:
                        complete = False
                        by_coordinate[coordinate] = 64
                        continue
                    if root_layout is not None:
                        projected = project_packet_children(parent, root_layout, coordinate, precision, budget=budget)
                        children = tuple(c.topology for c in projected)
                        src = root_layout.source
                        crossing = sum(src['row_labels'][str(src['edges'][e][0])][coordinate] !=
                                       src['column_labels'][str(src['edges'][f][1])][coordinate]
                                       for packet in src['packets'] for _, e in packet['occupied_slots']
                                       for _, f in packet['occupied_slots'])
                    elif descendant_strategy == 'singleton_first_fit' and (a, u) == (1, 1):
                        children, crossing = _project(topology, 64, budget)
                    else:
                        # One tuple, every group, even when further layout is unknown.
                        complete = False
                        by_coordinate[coordinate] = 64
                        continue
                    sizes = [c.edges for c in children]
                    if any(64 * size > 6 * M or size >= M for size in sizes):
                        block('ACTUAL_CHILD_SHRINK_FAILED', depth=topology.depth)
                    detail = {'coordinate': coordinate, 'child_edges': sizes,
                              'child_maximum_degrees': [c.maximum_degree for c in children],
                              'crossing_port_pairs': crossing, 'point_precision': precision,
                              'tuple_count_lower_bound': 1,
                              'tuple_count_status': 'EXACT_ONE_NO_CROSSING' if not crossing else 'BOUNDS_ONLY',
                              # At most crossing*(p-1) modes, all weights >=1;
                              # each beta component <p. No claim this is sharp.
                              'weighted_tuple_count_upper_power_of_two': crossing * (precision - 1) * (precision - 1).bit_length()}
                    row['coordinates'].append(detail)
                    subtree = 0
                    for child in children:
                        max_depth = max(max_depth, child.depth)
                        max_precision = max(max_precision, child.precision)
                        if child.depth + int(child.edges > 4) > policy.max_depth:
                            block('DESCENDANT_DEPTH_POLICY', depth=child.depth + int(child.edges > 4))
                        if child.edges > 4 and child.maximum_degree > 3 * child.edges // 64:
                            block('DESCENDANT_CANNOT_MEET_SIDE_LOAD', depth=child.depth, edges=child.edges,
                                  degree=child.maximum_degree, capacity=3 * child.edges // 64)
                        if child.edges <= 4 or descendant_strategy == 'singleton_first_fit':
                            subtree += visit(child, level + 1)
                        else:
                            complete = False
                            # A successful active child performs at least two grids
                            # of degree >=3m, even when its layout is unspecified.
                            subtree += 1 + 64 * 2 * (3 * child.edges + 1)
                            if level + 1 >= len(spec.schedule):
                                block('SCHEDULE_EXHAUSTED_ABOVE_LEAF', edges=child.edges, depth=child.depth)
                    by_coordinate[coordinate] = subtree
                calls += (degree + 1) * by_coordinate[coordinate]
            row['recursive_calls_lower_bound'] = calls
            memo[key] = calls
            return calls

        calls = visit(topology_of(parent), 0, layout)
        report.update(recursive_calls_lower_bound=calls, maximal_precision=max_precision,
                      maximal_depth=max_depth, descendant_strategy=descendant_strategy,
                      descendant_topologies_complete=complete)
        if calls > policy.max_calls:
            block('RECURSIVE_CALL_LOWER_BOUND', required=calls, available=policy.max_calls)
        report['status'] = ('INCONCLUSIVE_RESOURCE_OR_STRUCTURE' if blockers else
                            'PASS_FINITE_NECESSARY_CONDITIONS')
    except (ValueError, TypeError, KeyError, IndexError, RuntimeError, ArithmeticError, MemoryError) as exc:
        report.update(status=getattr(exc, 'status', 'INVALID_PACKET_PREFLIGHT'), reason=str(exc),
                      descendant_topologies_complete=False)
    report['preflight_work_units'] = budget.work
    if len(canonical(report)) > policy.max_certificate_bytes:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': 'preflight evidence cap',
                'parent_digest': parent.content_digest, 'source_qualified': False}
    report['report_digest'] = digest(canonical(report))
    return report


def compare_group_counts(parent, groups=(64, 128, 256, 512, 1024), *, policy):
    """Actual singleton descendant incidence; full-grid minimum costs only.

    These are finite a=u=1 candidates. General R99 execution still supports
    only 64 groups; the configurable R98 singleton driver is a separate path.
    One tuple per point is a lower bound, never a permission to drop modes.
    """
    if parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT:
        raise ValueError('finite group comparison only')
    if (type(groups) is not tuple or not 1 <= len(groups) <= 32 or len(set(groups)) != len(groups) or
        any(type(g) is not int or not 64 <= g <= 1024 for g in groups)):
        raise ValueError('distinct group candidates in 64..1024 required')
    candidates = []
    for count in groups:
        budget = Budget(policy)
        record = {'groups': count, 'source_qualified': False, 'schedule': 'FINITE_A_U_1',
                  'general_r99_executor_supported': count == 64, 'leaf_threshold': 4,
                  'call_scope': 'FULL_GRID_ONE_TUPLE_PER_POINT_LOWER_BOUND',
                  'mode_tuple_completeness': 'NOT_EVALUATED', 'blockers': []}
        sizes, memo, crossing, max_precision, max_grid = {}, {}, 0, parent.precision, 0
        def visit(node):
            nonlocal crossing, max_precision, max_grid
            budget.tick(1 + node.edges + len(node.vertices))
            sizes[node.depth - parent.depth] = max(sizes.get(node.depth - parent.depth, 0), node.edges)
            max_precision = max(max_precision, node.precision)
            if node.depth > policy.max_depth:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'candidate descendant depth cap')
            if node.edges <= 4:
                return 1
            if node.content_digest in memo:
                return memo[node.content_digest]
            children, cross = _project(node, count, budget)
            crossing += cross
            if node.depth == parent.depth:
                # Singleton a=u=1: y//2=0, so only b=0 survives.
                # At zeta=0 W_xx(+/-1)=0. At every nonzero binary
                # residue zeta, W_xx(+/-1+4*zeta) has valuation two.
                # There is exactly one weight-one mode per crossing.
                precision = node.precision + 64 * node.edges
                tuples = comb(precision + cross - 1, cross)
                record.update(root_crossing_pairs=cross,
                    root_zero_point_tuple_count=1, root_nonzero_point_tuple_count=tuples,
                    root_complete_weighted_child_calls=2 * count * (1 + 3 * node.edges * tuples),
                    mode_tuple_completeness='EXACT_ROOT_SINGLETON_COUNTS_NOT_ENUMERATED')
            grid = 3 * node.edges + 1
            max_grid = max(max_grid, grid)
            calls = 1 + 2 * grid * sum(visit(c) for c in children)
            memo[node.content_digest] = calls
            return calls
        try:
            calls = visit(topology_of(parent))
            record.update(descendant_packing='PASS_TO_FOUR_EDGE_LEAVES', recursive_calls_lower_bound=calls)
            if calls > policy.max_calls:
                record['blockers'].append('CALL_LOWER_BOUND_EXCEEDS_POLICY')
            if max_precision > policy.max_precision:
                record['blockers'].append('PRECISION_EXCEEDS_POLICY')
            if max_grid > 1 << (parent.defining_polynomial.bit_length() - 1):
                record['blockers'].append('RESIDUE_FIELD_TOO_SMALL')
            if max_grid > 3073:
                record['blockers'].append('HERMITE_REFERENCE_DEGREE_CAP')
            if parent.edge_count > policy.max_edges:
                record['blockers'].append('ROOT_EDGE_POLICY')
            record['status'] = 'INCONCLUSIVE_RESOURCE_LIMIT' if record['blockers'] else 'PASS_TOPOLOGY_ONLY'
        except (ValueError, RuntimeError, ArithmeticError, MemoryError) as exc:
            record.update(status=getattr(exc, 'status', 'INVALID_GROUP_CANDIDATE'),
                          reason=str(exc), descendant_packing='INCOMPLETE_OR_REFUSED')
        record.update(largest_edges_by_depth={str(d): m for d, m in sizes.items()},
                      maximal_precision=max_precision, largest_grid=max_grid,
                      crossing_pairs_over_unique_projected_active_nodes=crossing,
                      preflight_work_units=budget.work, launch_authorized_by_preflight=False)
        candidates.append(record)
    report = {'schema': 'VERITAS_R99_GROUP_CANDIDATES_V1', 'parent_digest': parent.content_digest,
            'candidates': candidates, 'tensor_entries_evaluated': False, 'source_qualified': False,
            'upper_runtime_status': 'NOT_ESTABLISHED', 'peak_memory_status': 'NOT_ESTABLISHED'}
    if len(canonical(report)) > policy.max_certificate_bytes:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'group comparison evidence cap')
    return report
