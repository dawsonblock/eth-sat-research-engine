"""Depth-configurable finite tapered recursion with explicit failure states.

This is an experimental adapter over bounded v39 components. It does not
implement the manuscript schedule, a complete cost ledger, or a hard memory
limit. Its ordinary execution path does not invoke the 4**M point oracle.
"""
from __future__ import annotations

from dataclasses import asdict
from collections import Counter
from hashlib import sha256

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.extension_lagrange import interpolate_newton
from veritas.research.eth_interpolation.tapered_hermite import make_tapered_plan, reconstruct_tapered
from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_packing_v26.expectation import PackingBudgetExceeded
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_sparse_mode_source,
)
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedDenseTensor, CreatedPacketTensor, contract_described_network,
)
from veritas.research.eth_recursive_contraction_v39.lazy_children import ChildEvaluationBudgetExceeded
from veritas.research.eth_recursive_contraction_v39.mode_matching import (
    _BudgetExceeded as MatchingBudgetExceeded, _Work as MatchingWork,
    certify_structural_tuple_matching,
)
from veritas.research.eth_recursive_contraction_v39.point_mode_matching import _verify_hall_witness
from veritas.research.eth_recursive_contraction_v39.point_children import _ring_for, _build_point_children_checked
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples

from .budget import Inconclusive, WorkBudget
from .certificates import Transcript, canonical, same_json
from .child_partition import verify_constructed_child_partition
from .model import RecursionPolicy, TaperedState

SCHEMA = 'VERITAS_FINITE_TAPERED_V4_TRANSCRIPT_V1'
SOURCE_REVISION = '4eaee87548250b2682affda7d05d947c05554bae'


class _PackingBudget:
    """Charge the constructor's cooperative ticks to the shared run budget."""

    def __init__(self, budget):
        self.budget = budget

    def tick(self, amount=1):
        self.budget.charge('packing_work', amount)


def _hall_zero_witness(modes, beta, budget):
    """Find and independently replay a Hall deficiency for checked modes."""
    available, _ = budget.remaining()
    match = certify_structural_tuple_matching(
        modes, beta, max_work=available,
        _on_step=lambda: budget.charge('hall_matching_steps'))
    if match['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT':
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'Hall matching work budget exhausted')
    if match['status'] == 'MATCHING_FEASIBLE_ONLY':
        return None
    if match['status'] != 'ZERO_IF_SUPPLIED_SUPPORT_COMPLETE':
        raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'unexpected Hall matching status')
    available, _ = budget.remaining()
    check_work = MatchingWork(available, lambda: budget.charge('hall_witness_steps'))
    try:
        _verify_hall_witness(modes, beta, match['witness'], check_work)
    except MatchingBudgetExceeded as exc:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'Hall witness work budget exhausted') from exc
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', f'invalid Hall witness: {exc}') from exc
    budget.charge('hall_zero_tuples')
    return match['witness']


def _network_digest(network, budget):
    """Hash immutable descriptions incrementally, including creation values."""
    digest = sha256()
    total = 0

    def add(value):
        nonlocal total
        budget.charge('description_items')
        data = canonical(value)
        total += len(data) + 8
        if total > budget.policy.max_description_bytes:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'tensor-description byte budget exhausted')
        digest.update(len(data).to_bytes(8, 'big'))
        digest.update(data)

    add({'edges': network.edges, 'vertices': len(network.vertices)})
    for vertex in network.vertices:
        tensor = vertex.tensor
        add({'side': vertex.side, 'label': vertex.label, 'ports': vertex.ports,
             'kind': type(tensor).__name__})
        if isinstance(tensor, CreatedDenseTensor):
            add({'arity': tensor.arity, 'entries': len(tensor.entries)})
            for entry in tensor.entries:
                add({'precision': entry.creation_precision, 'polynomial': entry.defining_polynomial,
                     'coefficients': entry.coefficients})
        elif isinstance(tensor, CreatedPacketTensor):
            add({'precision': tensor.creation_precision, 'polynomial': tensor.defining_polynomial,
                 'jet_length': tensor.jet_length, 'recipe': asdict(tensor.recipe)})
        else:
            raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'unsupported tensor description')
    return digest.hexdigest()


def _validate_creation_rings(state):
    for vertex in state.network.vertices:
        tensor = vertex.tensor
        if isinstance(tensor, CreatedDenseTensor):
            entry = tensor.entries[0]
            created, polynomial, length = (entry.creation_precision, entry.defining_polynomial,
                                            len(entry.coefficients))
        elif isinstance(tensor, CreatedPacketTensor):
            created, polynomial, length = (tensor.creation_precision, tensor.defining_polynomial,
                                           tensor.jet_length)
        else:
            raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'unsupported creation description')
        if (created > state.target_precision or polynomial != state.extension_polynomial or
                length != state.jet_length):
            raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE',
                               'creation precision or inherited coefficient ring is invalid')


def _run_leaf(state, ring, budget, *, oracle=False):
    available, seconds = budget.remaining()
    try:
        result = contract_described_network(state.network, ring, max_work=available,
                                            timeout_s=seconds, max_edges=16)
    except ChildEvaluationBudgetExceeded as exc:
        budget.record_interrupted_work('oracle_failed_leaf_work' if oracle else
                                       'algorithm_failed_leaf_work',
                                       None if exc.work_units is None else
                                       min(available, exc.work_units))
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', str(exc)) from exc
    except TimeoutError as exc:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', str(exc)) from exc
    budget.charge('oracle_leaf_work' if oracle else 'algorithm_leaf_work', result['work_units'])
    return result['result']


def _contract(state, policy, budget, transcript, *, forced_leaf_reason=None):
    if state.depth > policy.max_depth:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'maximum recursion depth exceeded')
    if state.target_precision > policy.max_precision_bits:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'precision budget exceeded')
    if (state.extension_polynomial.bit_length() - 1 > policy.max_extension_degree or
            state.jet_length > policy.max_jet_length):
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'extension-degree or jet-length budget exceeded')
    budget.charge('recursive_calls')
    budget.maximum_depth = max(budget.maximum_depth, state.depth)
    budget.maximum_precision_bits = max(budget.maximum_precision_bits, state.target_precision)
    budget.maximum_parent_edges = max(budget.maximum_parent_edges, state.network.edges)
    parent_degree = max((len(vertex.ports) for vertex in state.network.vertices), default=0)
    budget.maximum_parent_degree = max(budget.maximum_parent_degree, parent_degree)
    if parent_degree > policy.max_vertex_degree:
        raise Inconclusive('INCONCLUSIVE_DEGREE_INVARIANT', 'vertex degree exceeds the declared finite bound')
    _validate_creation_rings(state)
    network_digest = _network_digest(state.network, budget)
    state_data = {'network_sha256': network_digest, 'depth': state.depth,
                  'precision': state.target_precision, 'polynomial': state.extension_polynomial,
                  'jet_length': state.jet_length, 'root_size': state.root_size,
                  'schedule_id': state.schedule_id, 'parent_state_sha256': state.parent_certificate_hash}
    state_hash = sha256(canonical(state_data)).hexdigest()
    transcript.add({'kind': 'enter', 'state_sha256': state_hash, **state_data,
                    'edges': state.network.edges})
    ring = JetRing(ExtensionRing(state.target_precision, state.extension_polynomial), state.jet_length)

    if state.network.edges == 0 or state.network.edges <= policy.leaf_edge_limit or forced_leaf_reason:
        if forced_leaf_reason and state.network.edges > policy.nonshrinking_leaf_limit:
            raise Inconclusive('INCONCLUSIVE_NONSHRINKING_CHILD', 'nonshrinking leaf exceeds its explicit cap')
        budget.charge('algorithm_leaf_calls')
        result = _run_leaf(state, ring, budget)
        transcript.add({'kind': 'leaf', 'state_sha256': state_hash,
                        'reason': forced_leaf_reason or ('ZERO_WIRE' if state.network.edges == 0 else 'EDGE_CUTOFF'),
                        'result': result})
        return result, state_hash

    if state.depth >= policy.max_depth:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'maximum depth reached before a valid leaf')
    if state.network.edges > policy.max_active_wires:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'finite active-wire budget exceeded')
    degree = ring.base.e
    if degree > 8 or state.extension_polynomial != first_irreducible(degree):
        raise Inconclusive('INCONCLUSIVE_UNSUPPORTED_RING',
                           'finite mode builder requires its canonical extension polynomial of degree at most eight')
    a, u, radix = policy.finite_parameters
    try:
        plan = make_tapered_plan(M=state.network.edges, a=a, u=u, p=state.target_precision,
                                 max_work_precision=policy.max_precision_bits,
                                 max_target_precision=policy.max_precision_bits)
    except ValueError as exc:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', f'finite tapered plan unavailable: {exc}') from exc
    point_count = plan.degree_bound + 1
    if point_count > policy.max_points or point_count > 1 << degree:
        raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'insufficient interpolation points or residue classes')
    budget.charge('packing_calls')
    available, _ = budget.remaining()
    source = implicit_sparse_mode_source(construct_implicit_packing(
        state.network.bipartite_edges(), r=radix, a=a, max_work=available,
        _budget=_PackingBudget(budget)),
        max_work=available)
    budget.check()
    transcript.add({'kind': 'packing', 'state_sha256': state_hash,
                    'parameters': [a, u, radix],
                    'source_sha256': sha256(canonical(source)).hexdigest(),
                    'active_packets': len(source['packets']), 'degree_bound': plan.degree_bound})

    node_samples = {}
    for node in plan.nodes:
        if not state.target_precision < node.precision_bits <= policy.max_precision_bits:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'child precision exceeds budget or fails to increase')
        base = ExtensionRing(node.precision_bits, state.extension_polynomial)
        points = distinct_residue_points(base, point_count, max_points=policy.max_points)
        values = []
        for point_index, point in enumerate(points):
            budget.charge('point_evaluations')
            modes = make_point_modes(source, node=node.t, precision=node.precision_bits,
                                     extension_degree=degree, zeta=point,
                                     max_tuples=policy.max_tuples,
                                     max_parent_wires=policy.max_active_wires,
                                     _tuple_work=lambda: budget.charge('mode_precount_steps'))
            budget.check()
            checked_ring, checked_source = _ring_for(state.network, modes,
                                                      max_parent_wires=policy.max_active_wires,
                                                      _tuple_work=lambda: budget.charge('mode_replay_precount_steps'))
            if checked_ring.base != base or checked_ring.length != state.jet_length:
                raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'mode ring differs from inherited ring')
            budget.charge('mode_records', len(modes['modes']))
            mode_counts = Counter(mode['weight'] for mode in modes['modes'])
            budget.mode_counts_by_weight.update(mode_counts)
            node_valuation = (abs(node.t) & -abs(node.t)).bit_length() - 1
            mode_denominator = source['L'] >> node_valuation
            budget.charge('finite_multiplicity_checks')
            multiplicity_ok = all(count * mode_denominator <= 6 * state.network.edges
                                  for count in mode_counts.values())
            # The bounded mode constructor also enumerates tuples once for its
            # certificate; charge those visits separately from execution visits.
            budget.charge('mode_precount_tuples', modes['structural_tuple_count'])
            valuations = []
            for mode in modes['modes']:
                minimum = min(base.valuation(base.elem(encoded[0])) for _, encoded in mode['rows'])
                if minimum < mode['weight']:
                    raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'mode valuation below declared weight')
                valuations.append({'packet': mode['packet'], 'source_group': mode['source_group'],
                                   'target_group': mode['target_group'], 'weight': mode['weight'],
                                   'minimum_valuation': minimum})
            transcript.add({'kind': 'point', 'state_sha256': state_hash, 'node': node.t,
                            'point_index': point_index, 'point': point,
                            'precision': node.precision_bits,
                            'mode_certificate_sha256': sha256(canonical(modes)).hexdigest(),
                            'mode_valuations': valuations,
                            'finite_modes_by_weight': sorted(mode_counts.items()),
                            'finite_multiplicity_bound': {'numerator': 6 * state.network.edges,
                                                          'denominator': mode_denominator,
                                                          'satisfied': multiplicity_ok}})
            point_ring = JetRing(base, state.jet_length)
            total = point_ring.zero
            tuple_count = 0
            for beta in structural_tuples(modes['modes'], node.precision_bits,
                                           max_tuples=policy.max_tuples,
                                           _on_step=lambda: budget.charge('tuple_execution_steps')):
                budget.charge('retained_tuples')
                tuple_count += 1
                declared_weight = sum(exponent * mode['weight']
                                      for exponent, mode in zip(beta, modes['modes']))
                actual_valuation_bound = sum(exponent * item['minimum_valuation']
                                             for exponent, item in zip(beta, valuations))
                if (len(beta) != len(modes['modes']) or
                        declared_weight >= node.precision_bits or
                        actual_valuation_bound < declared_weight):
                    raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE',
                                       'retained tuple violates its weight or valuation bound')
                budget.charge('tuple_valuation_checks')
                if policy.enable_hall_pruning:
                    witness = _hall_zero_witness(modes['modes'], beta, budget)
                    if witness is not None:
                        transcript.add({'kind': 'tuple_hall_zero', 'state_sha256': state_hash,
                                        'node': node.t, 'point_index': point_index, 'beta': beta,
                                        'declared_weight': declared_weight,
                                        'witness': witness})
                        continue
                children = _build_point_children_checked(state.network, modes, beta,
                                                           checked_ring, checked_source)
                budget.charge('child_partition_checks')
                try:
                    verify_constructed_child_partition(state.network, checked_source,
                                                       node_valuation, children)
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE',
                                       f'child half-wire partition is invalid: {exc}') from exc
                term = point_ring.one
                child_rows = []
                for child in children:
                    budget.charge('generated_children')
                    child_edges = child.network.edges
                    child_degree = max((len(v.ports) for v in child.network.vertices), default=0)
                    budget.maximum_child_edges = max(budget.maximum_child_edges, child_edges)
                    budget.maximum_child_degree = max(budget.maximum_child_degree, child_degree)
                    if child_degree > policy.max_vertex_degree:
                        raise Inconclusive('INCONCLUSIVE_DEGREE_INVARIANT',
                                           'child degree exceeds the declared finite bound')
                    if policy.require_one_eighth_shrink and (
                            8 * child_edges >= state.network.edges or
                            radix * child_edges > 6 * state.network.edges):
                        raise Inconclusive('INCONCLUSIVE_CHILD_SIZE_INVARIANT',
                                           'a child violates the requested one-eighth or port bound')
                    forced = None
                    if child_edges >= state.network.edges and child_edges:
                        budget.charge('nonshrinking_children')
                        if not policy.allow_nonshrinking_leaf or child_edges > policy.nonshrinking_leaf_limit:
                            raise Inconclusive('INCONCLUSIVE_NONSHRINKING_CHILD',
                                               'nonshrinking child cannot be recursively expanded')
                        forced = 'NONSHRINKING_FINITE_FALLBACK'
                    child_state = TaperedState(child.network, state.depth + 1, node.precision_bits,
                                               state.extension_polynomial, state.jet_length,
                                               state.root_size, state.schedule_id, state_hash)
                    child_value, child_hash = _contract(child_state, policy, budget, transcript,
                                                        forced_leaf_reason=forced)
                    budget.accumulator_operation('accumulator_ring_multiplications', term, child_value)
                    term = point_ring.mul(term, child_value)
                    child_rows.append({'group': child.group, 'edges': child_edges,
                                       'maximum_degree': child_degree,
                                       'state_sha256': child_hash, 'result': child_value,
                                       'finite_fallback': forced is not None})
                budget.accumulator_operation('accumulator_ring_additions', total, term)
                total = point_ring.add(total, term)
                transcript.add({'kind': 'tuple', 'state_sha256': state_hash, 'node': node.t,
                                'point_index': point_index, 'beta': beta,
                                'declared_weight': declared_weight,
                                'valuation_lower_bound': actual_valuation_bound,
                                'children': child_rows, 'term': term})
            if tuple_count != modes['structural_tuple_count']:
                raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'tuple stream differs from mode certificate')
            values.append(total)
        columns = []
        for v in range(state.jet_length):
            budget.charge('interpolation_calls')
            columns.append(interpolate_newton(base, points, [value[v] for value in values],
                                               max_points=policy.max_points))
        budget.check()
        retained = min(node.multiplicity, point_count)
        budget.charge('retained_jet_coordinates', retained * state.jet_length * degree)
        node_samples[node.t] = tuple(tuple(columns[v][j] for v in range(state.jet_length))
                                     for j in range(retained))

    output = []
    for v in range(state.jet_length):
        coordinates = []
        for u_index in range(degree):
            budget.charge('hermite_recoveries')
            jets = {node.t: tuple(coefficient[v][u_index] for coefficient in node_samples[node.t])
                    for node in plan.nodes}
            precisions = {node.t: (node.precision_bits,) * len(node_samples[node.t])
                          for node in plan.nodes}
            coordinates.append(reconstruct_tapered(plan, jets, coefficient_precisions=precisions))
        output.append(tuple(coordinates))
    result = tuple(output)
    if policy.verify_small_nodes and state.network.edges <= policy.oracle_edge_limit:
        budget.charge('oracle_leaf_calls')
        oracle = _run_leaf(state, ring, budget, oracle=True)
        if result != oracle:
            raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'direct node oracle disagrees with recursion')
    transcript.add({'kind': 'complete', 'state_sha256': state_hash, 'result': result,
                    'direct_node_oracle_used': bool(policy.verify_small_nodes and
                                                    state.network.edges <= policy.oracle_edge_limit)})
    return result, state_hash


def contract_recursive(state, policy):
    """Return a finite modular result or an inconclusive status without a result."""
    if not isinstance(state, TaperedState) or not isinstance(policy, RecursionPolicy):
        raise TypeError('TaperedState and RecursionPolicy required')
    budget = WorkBudget(policy)
    transcript = Transcript(policy.max_certificate_bytes)
    try:
        if state.depth != 0 or state.parent_certificate_hash is not None:
            raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'public entry state must be a root')
        if state.root_size != state.network.edges:
            raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'root size differs from the root network')
        if policy.mode == 'theorem':
            raise Inconclusive('INCONCLUSIVE_THEOREM_PATH_NOT_IMPLEMENTED',
                               'the manuscript schedule and 64-group proof obligations are not implemented')
        if state.schedule_id != 'FINITE_SCALED_V1':
            raise Inconclusive('INCONCLUSIVE_INVARIANT_FAILURE', 'unsupported finite schedule identity')
        if policy.max_memory_bytes is not None:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'a hard process memory limit is not implemented')
        if policy.require_complete_accounting:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'complete bit-work and memory accounting is not implemented')
        result, root_hash = _contract(state, policy, budget, transcript)
        budget.check()
        certificate = {'schema': SCHEMA, 'claim': 'FINITE_BOUNDED_TAPERED_EXECUTION_ONLY',
                       'source_revision': SOURCE_REVISION,
                       'root_state_sha256': root_hash, 'policy': asdict(policy),
                       'events': transcript.events, 'transcript_sha256': transcript.head,
                       'result': result, 'uniform_complexity_proven': False}
        certificate_bytes = len(canonical(certificate))
        if certificate_bytes > policy.max_certificate_bytes:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'serialized certificate budget exhausted')
        ledger = budget.snapshot()
        ledger['serialized_transcript_bytes'] = transcript.serialized_bytes
        ledger['serialized_certificate_bytes'] = certificate_bytes
        return {'status': 'EXACT_MODULAR_CONTRACTION_FINITE', 'result': result,
                'certificate': certificate, 'ledger': ledger,
                'independent_oracle_enabled': policy.verify_small_nodes,
                'subexponential_runtime_proven': False}
    except Inconclusive as exc:
        return {'status': exc.status, 'reason': exc.reason, 'ledger': budget.snapshot(),
                'subexponential_runtime_proven': False}
    except (ChildEvaluationBudgetExceeded, ModeBudgetExceeded, PackingBudgetExceeded, RecursionError, MemoryError) as exc:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc), 'ledger': budget.snapshot(),
                'subexponential_runtime_proven': False}
    except (ValueError, ArithmeticError, AssertionError) as exc:
        return {'status': 'INCONCLUSIVE_INVARIANT_FAILURE', 'reason': str(exc), 'ledger': budget.snapshot(),
                'subexponential_runtime_proven': False}


def replay_certificate(state, policy, certificate):
    """Deterministically replay a finite transcript; this is not independent proof."""
    if type(certificate) is not dict or certificate.get('schema') != SCHEMA:
        return {'valid': False, 'status': 'INVALID_CERTIFICATE'}
    outcome = contract_recursive(state, policy)
    if outcome['status'] != 'EXACT_MODULAR_CONTRACTION_FINITE':
        return {'valid': False, 'status': outcome['status'], 'reason': outcome.get('reason')}
    try:
        valid = same_json(certificate, outcome['certificate'])
    except (TypeError, ValueError):
        valid = False
    return {'valid': valid, 'status': 'FINITE_TRANSCRIPT_REPLAYED' if valid else 'INVALID_CERTIFICATE',
            'independent_proof': False, 'subexponential_runtime_proven': False}
