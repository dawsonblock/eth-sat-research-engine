"""Bounded tapered reconstruction using described point-child contractions.

The packet parameters are experimentally scaled and the child contractions
are direct finite sums.  This module checks one full parent recovery, not the
uniform recursive complexity theorem.
"""
from __future__ import annotations

from time import monotonic

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.extension_lagrange import interpolate_newton
from veritas.research.eth_interpolation.tapered_hermite import make_tapered_plan, reconstruct_tapered
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from .described_network import CreatedDenseTensor, CreatedPacketTensor, DescribedNetwork, contract_described_network
from .lazy_children import ChildEvaluationBudgetExceeded
from .point_modes import make_point_modes
from .point_children import contract_point_child_expansion


def _shape(network):
    if not isinstance(network, DescribedNetwork) or not network.vertices:
        raise ValueError('a nonempty described network is required')
    shape = None
    for vertex in network.vertices:
        tensor = vertex.tensor
        if isinstance(tensor, CreatedDenseTensor):
            entry = tensor.entries[0]
            item = (entry.defining_polynomial, len(entry.coefficients), entry.creation_precision)
        elif isinstance(tensor, CreatedPacketTensor):
            item = (tensor.defining_polynomial, tensor.jet_length, tensor.creation_precision)
        else:
            raise ValueError('unsupported tensor description')
        if shape is not None and item[:2] != shape[:2]:
            raise ValueError('incompatible tensor entry rings')
        shape = item if shape is None else (shape[0], shape[1], max(shape[2], item[2]))
    return shape


def contract_tapered_finite(network, *, target_precision, packet_exponent=1, u=1,
                            radix=2, max_work=1_000_000, timeout_s=30.0,
                            max_points=32, max_tuples=3000,
                            max_recursive_levels=1,
                            experimental_level_parameters=None):
    """Recover a small described contraction through finite point children.

    A direct contraction at target precision is an independent final oracle.
    Any exhausted budget raises without returning a partial result.
    """
    if type(max_work) is not int or not 1 <= max_work <= 2_000_000:
        raise ValueError('max_work must be in 1..2000000')
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
        raise ValueError('timeout must be in (0,30]')
    if type(max_recursive_levels) is not int or not 1 <= max_recursive_levels <= 2:
        raise ValueError('finite reference supports one or two recursive levels')
    if experimental_level_parameters is None:
        levels = ((packet_exponent, u, radix),) * max_recursive_levels
    else:
        levels = experimental_level_parameters
        if (type(levels) is not tuple or len(levels) != max_recursive_levels or
                any(type(level) is not tuple or len(level) != 3 or
                    any(type(value) is not int for value in level) for level in levels)):
            raise ValueError('experimental level parameters must be immutable (a,u,r) tuples')
        packet_exponent, u, radix = levels[0]
    if not isinstance(network, DescribedNetwork):
        raise TypeError('DescribedNetwork required')
    if not 1 <= network.edges <= 6:
        raise ValueError('finite tapered reference supports 1..6 wires')
    f, jet_length, latest_creation = _shape(network)
    if type(target_precision) is not int or target_precision < latest_creation:
        raise ValueError('target precision precedes a tensor creation')
    degree = f.bit_length() - 1
    try:
        plan = make_tapered_plan(M=network.edges, a=packet_exponent, u=u,
                                 p=target_precision, max_work_precision=1024)
    except ValueError as exc:
        if 'guard precision exceeds reference budget' in str(exc):
            raise ChildEvaluationBudgetExceeded('guard precision exceeds finite ring limit') from exc
        raise
    if plan.degree_bound + 1 > max_points:
        raise ChildEvaluationBudgetExceeded('interpolation point budget exceeded')
    source = implicit_mode_source(construct_implicit_packing(
        network.bipartite_edges(), r=radix, a=packet_exponent))
    deadline = monotonic() + timeout_s
    work = 0
    oracle_work = 0
    nested_calls = 0
    levels_exercised = 1
    maximum_precision_bits = max(node.precision_bits for node in plan.nodes)
    modes_generated = 0
    tuples_visited = 0
    structurally_zero_tuples = 0

    def contract_child(child, ring, remaining_work, remaining_time):
        nonlocal nested_calls, levels_exercised, maximum_precision_bits
        if (max_recursive_levels > 1 and 1 <= child.edges <= 6 and
                ring.base.p <= 128):
            nested = contract_tapered_finite(
                child, target_precision=ring.base.p, packet_exponent=packet_exponent,
                u=u, radix=radix, max_work=remaining_work, timeout_s=remaining_time,
                max_points=max_points, max_tuples=max_tuples,
                max_recursive_levels=max_recursive_levels - 1,
                experimental_level_parameters=levels[1:])
            charged = nested['algorithm_work_units'] + nested['independent_oracle_work_units']
            if charged > remaining_work:
                raise ChildEvaluationBudgetExceeded('nested evaluation work budget exhausted')
            nested_calls += 1 + nested['nested_calls']
            levels_exercised = max(levels_exercised, 1 + nested['recursive_levels_exercised'])
            maximum_precision_bits = max(maximum_precision_bits, nested['maximum_precision_bits'])
            return {'result': nested['result'],
                    'work_units': nested['algorithm_work_units'],
                    'oracle_work_units': nested['independent_oracle_work_units']}
        return contract_described_network(child, ring, max_work=remaining_work,
                                          timeout_s=remaining_time, max_edges=12)

    node_samples = {}
    node_summaries = []
    for node in plan.nodes:
        base = ExtensionRing(node.precision_bits, f)
        points = distinct_residue_points(base, plan.degree_bound + 1, max_points=max_points)
        values = []
        for point in points:
            remaining_time, remaining_work = deadline - monotonic(), max_work - work - oracle_work
            if remaining_time <= 0 or remaining_work < 1:
                raise ChildEvaluationBudgetExceeded('tapered evaluation budget exhausted')
            modes = make_point_modes(source, node=node.t, precision=node.precision_bits,
                                     extension_degree=degree, zeta=point, max_tuples=max_tuples)
            out = contract_point_child_expansion(network, modes, max_tuples=max_tuples,
                                                 max_work=remaining_work,
                                                 timeout_s=remaining_time,
                                                 _child_contractor=(contract_child
                                                                    if max_recursive_levels > 1 else None))
            work += out['algorithm_work_units']
            oracle_work += out['independent_oracle_work_units']
            modes_generated += len(modes['modes'])
            tuples_visited += len(out['tuples'])
            structurally_zero_tuples += out['structurally_zero_tuples']
            values.append(out['result'])
        # Interpolation is R-linear; recover each V coordinate independently.
        coefficient_columns = [interpolate_newton(base, points,
                                                   [value[v] for value in values],
                                                   max_points=max_points)
                               for v in range(jet_length)]
        coefficients = tuple(tuple(coefficient_columns[v][j] for v in range(jet_length))
                             for j in range(plan.degree_bound + 1))
        node_samples[node.t] = coefficients
        node_summaries.append({'node': node.t, 'precision': node.precision_bits,
                               'multiplicity': node.multiplicity, 'points': len(points)})
    recovered = []
    for v in range(jet_length):
        component = []
        for u_index in range(degree):
            scalar_jets = {node.t: tuple(coefficient[v][u_index]
                                         for coefficient in node_samples[node.t])
                           for node in plan.nodes}
            component.append(reconstruct_tapered(plan, scalar_jets))
        recovered.append(tuple(component))
    result = tuple(recovered)
    remaining_time, remaining_work = deadline - monotonic(), max_work - work - oracle_work
    if remaining_time <= 0 or remaining_work < 1:
        raise ChildEvaluationBudgetExceeded('tapered final-oracle budget exhausted')
    direct_ring = JetRing(ExtensionRing(target_precision, f), jet_length)
    direct = contract_described_network(network, direct_ring, max_work=remaining_work,
                                        timeout_s=remaining_time, max_edges=12)
    oracle_work += direct['work_units']
    if result != direct['result']:
        raise ArithmeticError('tapered recovery differs from direct contraction')
    return {'status': 'FINITE_TAPERED_CHILD_RECOVERY_VERIFIED', 'result': result,
            'nodes': tuple(node_summaries), 'algorithm_work_units': work,
            'independent_oracle_work_units': oracle_work,
            'nested_calls': nested_calls, 'recursive_levels_exercised': levels_exercised,
            'maximum_precision_bits': maximum_precision_bits,
            'experimental_level_parameters': levels,
            'point_modes_generated': modes_generated, 'tuples_visited': tuples_visited,
            'structurally_zero_tuples': structurally_zero_tuples,
            'ledger_complete': False, 'experimental_scaled_parameters': True,
            'full_recursive_contraction': False,
            'subexponential_runtime_proven': False}


def run_tapered_finite(network, **kwargs):
    """Return an inconclusive status, with no result, on finite budget exhaustion."""
    try:
        return contract_tapered_finite(network, **kwargs)
    except (ChildEvaluationBudgetExceeded, ModeBudgetExceeded) as exc:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc),
                'full_recursive_contraction': False,
                'subexponential_runtime_proven': False}
