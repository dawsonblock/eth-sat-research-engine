"""Bounded evidence for one actual packet-mode child tuple.

This is a finite audit, not a theorem-scale packing, recursion, or runtime
certificate.  An optional independent half-wire oracle is exponential and
limited to three parent wires.
"""
from __future__ import annotations

from hashlib import sha256
from time import monotonic

from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedPacketTensor, DescribedNetwork, contract_described_network,
)
from veritas.research.eth_recursive_contraction_v39.independent_tuple_oracle import direct_tuple_contribution
from veritas.research.eth_recursive_contraction_v39.lazy_children import ChildEvaluationBudgetExceeded
from veritas.research.eth_recursive_contraction_v39.point_children import (
    DescribedGroupChild, _build_point_children_checked, _ring_for,
)

from .budget import Inconclusive, WorkBudget
from .certificates import canonical
from .child_partition import verify_constructed_child_partition
from .model import RecursionPolicy


SCHEMA = 'VERITAS_ACTUAL_POINT_CHILD_CERTIFICATE_V1'


def certify_actual_point_children(parent, mode_certificate, beta, children, *,
                                  source_validation='canonical', declared_degree_bound=None,
                                  verify_tuple_identity=False, max_work=250_000,
                                  timeout_s=10.0, max_source_work=1_000_000,
                                  max_description_bytes=4_000_000):
    """Audit supplied immutable children for one point and retained tuple.

    Mode replay and source validation are required.  Child descriptions are
    compared with a fresh construction and an independent topology replay.
    The optional tuple oracle checks one term only and is limited to M<=3.
    Limits are cooperative finite guards, not complete bit/memory metering.
    Exhaustion and failures return no certificate or partial contraction.
    """
    if source_validation not in ('canonical', 'geometry'):
        raise ValueError('source validation must be canonical or geometry')
    if (type(max_work) is not int or not 1 <= max_work <= 2_000_000 or
            type(max_source_work) is not int or not 1 <= max_source_work <= 2_000_000 or
            type(max_description_bytes) is not int or not 1 <= max_description_bytes <= 50_000_000 or
            type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30 or
            type(verify_tuple_identity) is not bool or
            (declared_degree_bound is not None and
             (type(declared_degree_bound) is not int or not 0 <= declared_degree_bound <= 64))):
        raise ValueError('invalid finite audit limits or options')
    if not isinstance(parent, DescribedNetwork):
        raise TypeError('described parent network required')
    if not isinstance(children, (tuple, list)):
        raise TypeError('finite sequence of actual children required')
    started = monotonic()
    policy = RecursionPolicy(max_work=max_work, max_seconds=timeout_s,
                             max_description_bytes=max_description_bytes)
    budget = WorkBudget(policy)

    def remaining():
        available, seconds = budget.remaining()
        seconds = min(seconds, timeout_s - (monotonic() - started))
        if seconds <= 0:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'cooperative audit deadline exhausted')
        return available, seconds

    try:
        if parent.edges > 8 or len(parent.vertices) > 64 or len(children) > 64:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'finite network-description cap exceeded')
        if verify_tuple_identity and parent.edges > 3:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'independent tuple oracle supports at most three wires')
        if any(type(child) is not DescribedGroupChild for child in children):
            raise ValueError('actual described group children required')
        remaining()
        ring, source = _ring_for(parent, mode_certificate, max_parent_wires=8,
                                 _source_validation=source_validation, _source_work=max_source_work)
        remaining()
        expected = _build_point_children_checked(parent, mode_certificate, beta, ring, source)
        if tuple(c.group for c in children) != tuple(c.group for c in expected):
            raise ValueError('actual child groups differ from checked mode construction')
        coordinate = (abs(mode_certificate['node']) & -abs(mode_certificate['node'])).bit_length() - 1
        verify_constructed_child_partition(parent, source, coordinate, children)

        # The digest routine binds the complete immutable creation recipes,
        # not just port topology. It also enforces a finite description cap.
        from .recursor import _network_digest
        parent_digest = _network_digest(parent, budget)
        actual_digests = []
        for actual, reference in zip(children, expected):
            actual_digest = _network_digest(actual.network, budget)
            if actual_digest != _network_digest(reference.network, budget):
                raise ValueError('actual child description differs from checked construction')
            actual_digests.append(actual_digest)

        M, L, r = parent.edges, source['L'], source['r']
        parent_degree = max((len(v.ports) for v in parent.vertices), default=0)
        rows = []
        for child, digest in zip(children, actual_digests):
            new_packets = [v for v in child.network.vertices if v.side == 'column']
            if any(not isinstance(v.tensor, CreatedPacketTensor) for v in new_packets):
                raise ValueError('new packet vertices require immutable packet tensors')
            packet_degree = max((len(v.ports) for v in new_packets), default=0)
            child_degree = max((len(v.ports) for v in child.network.vertices), default=0)
            if packet_degree > 2 * L or child_degree > max(parent_degree, 2 * L):
                raise ValueError('constructed child violates the packet or inherited degree bound')
            rows.append({'group': child.group, 'edges': child.network.edges,
                         'maximum_degree': child_degree, 'maximum_packet_degree': packet_degree,
                         'network_sha256': digest,
                         'meets_six_M_over_r': r * child.network.edges <= 6 * M,
                         'meets_three_M_over_32': r == 64 and 32 * child.network.edges <= 3 * M,
                         'meets_strict_one_eighth': 8 * child.network.edges < M,
                         'meets_declared_degree_bound': (None if declared_degree_bound is None else
                                                          child_degree <= declared_degree_bound)})
        oracle_evidence = None
        if verify_tuple_identity:
            term = ring.one
            for child in children:
                left_work, left_time = remaining()
                out = contract_described_network(child.network, ring, max_work=left_work,
                                                 timeout_s=left_time, max_edges=12)
                budget.charge('algorithm_child_work', out['work_units'])
                term = ring.mul(term, out['result'])
            left_work, left_time = remaining()
            oracle = direct_tuple_contribution(parent, mode_certificate, beta,
                                               max_work=left_work, timeout_s=left_time,
                                               _source_validation=source_validation,
                                               _source_work=max_source_work)
            budget.charge('independent_tuple_oracle_work', oracle['work_units'])
            if term != oracle['result']:
                raise ArithmeticError('child product differs from independent tuple oracle')
            oracle_evidence = {'result': term, 'algorithm_child_work':
                               budget.counters.get('algorithm_child_work', 0),
                               'independent_tuple_oracle_work': oracle['work_units']}
        remaining()
        certificate = {
            'schema': SCHEMA, 'claim': 'FINITE_ACTUAL_POINT_CHILDREN_ONLY',
            'source_validation': source_validation,
            'parent_sha256': parent_digest,
            'mode_certificate_sha256': sha256(canonical(mode_certificate)).hexdigest(),
            'beta': list(beta), 'coordinate': coordinate, 'parent_edges': M,
            'radix': r, 'packet_size': L, 'parent_maximum_degree': parent_degree,
            'declared_degree_bound': declared_degree_bound,
            'parent_meets_declared_degree_bound': (None if declared_degree_bound is None else
                                                   parent_degree <= declared_degree_bound),
            'two_L_meets_declared_degree_bound': (None if declared_degree_bound is None else
                                                  2 * L <= declared_degree_bound),
            'children': rows, 'sum_child_edges': sum(row['edges'] for row in rows),
            'all_children_meet_six_M_over_r': all(row['meets_six_M_over_r'] for row in rows),
            'all_children_meet_strict_one_eighth': all(row['meets_strict_one_eighth'] for row in rows),
            'tuple_identity_checked': verify_tuple_identity, 'tuple_identity_evidence': oracle_evidence,
            'all_tuples_checked': False, 'theorem_schedule_verified': False,
            'uniform_complexity_proven': False,
        }
        if len(canonical(certificate)) > max_description_bytes:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'certificate byte budget exhausted')
        return {'status': 'FINITE_ACTUAL_POINT_CHILDREN_CHECKED', 'certificate': certificate,
                'observed_work_units': budget.used, 'complete_resource_accounting': False,
                'source_validation_and_mode_replay_fully_metered': False}
    except (Inconclusive, ChildEvaluationBudgetExceeded, ModeBudgetExceeded, MemoryError) as exc:
        return {'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'reason': str(exc),
                'complete_resource_accounting': False}
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, OverflowError) as exc:
        return {'status': 'INVALID_ACTUAL_POINT_CHILDREN', 'reason': str(exc),
                'complete_resource_accounting': False}


def replay_actual_point_children(parent, mode_certificate, beta, children, certificate, **kwargs):
    """Recompute one finite certificate, propagating an inconclusive audit."""
    result = certify_actual_point_children(parent, mode_certificate, beta, children, **kwargs)
    if result['status'] != 'FINITE_ACTUAL_POINT_CHILDREN_CHECKED':
        return {'valid': False, 'status': result['status'], 'reason': result.get('reason')}
    try:
        valid = canonical(certificate) == canonical(result['certificate'])
    except (TypeError, ValueError):
        valid = False
    return {'valid': valid,
            'status': 'FINITE_ACTUAL_CHILD_CERTIFICATE_REPLAYED' if valid else 'INVALID_CHILD_CERTIFICATE',
            'uniform_complexity_proven': False}
