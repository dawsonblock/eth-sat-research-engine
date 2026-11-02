"""Opt-in finite point modes and children for independently audited packets.

Unlike the default point API, these functions accept noncanonical labels.
They verify the complete sparse packet geometry and the point-mode identity;
they do not certify the deterministic D.3 labeling, a general shrink theorem,
or subexponential complexity. No theorem-mode recursor calls these functions.
"""
from __future__ import annotations

from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_packing_v26.geometry_audit import audit_sparse_packet_geometry

from .point_modes import SCHEMA, make_point_modes, check_point_modes
from .point_children import _ring_for, _build_point_children_checked, contract_point_child_expansion
from .independent_tuple_oracle import direct_tuple_contribution
from .point_mode_matching import certify_point_mode_matching_zero, replay_point_mode_matching_zero


def _geometry_limit(value):
    if type(value) is not int or not 1 <= value <= 2_000_000:
        raise ValueError('finite geometry work limit must be in 1..2000000')


def _source_snapshot(source, *, max_geometry_work, max_parent_wires):
    """Freeze only bounded, checked fields and audit again in the mode API."""
    _geometry_limit(max_geometry_work)
    if (type(max_parent_wires) is not int or not 1 <= max_parent_wires <= 8 or
            not isinstance(source, dict) or type(source.get('M')) is not int or
            not 1 <= source['M'] <= max_parent_wires):
        raise ValueError('finite geometry source exceeds the parent-wire limit')
    audited = audit_sparse_packet_geometry(source, max_work=max_geometry_work)
    if audited.get('status') == 'INCONCLUSIVE_RESOURCE_LIMIT':
        raise ModeBudgetExceeded('geometry audit work limit exhausted')
    if audited.get('valid') is not True:
        raise ValueError('sparse packet geometry did not verify')
    # Retain only fields required by point-mode construction. This avoids
    # copying caller-added irrelevant data. Every retained field is audited
    # again by make_point_modes on the newly created snapshot.
    return {
        'schema': source['schema'], 'claim': source['claim'],
        'r': source['r'], 'a': source['a'], 'L': source['L'],
        'D': source['D'], 'M': source['M'], 'H_pad': source['H_pad'],
        'edges': [list(edge) for edge in source['edges']],
        'row_labels': {key: list(value) for key, value in source['row_labels'].items()},
        'column_labels': {key: list(value) for key, value in source['column_labels'].items()},
        'packets': [{'symbol_pairs': [list(pair) for pair in packet['symbol_pairs']],
                     'index': packet['index'],
                     'occupied_slots': [list(item) for item in packet['occupied_slots']]}
                    for packet in source['packets']],
    }


def make_geometry_point_modes(source, *, node=1, precision=5, extension_degree=3,
                              zeta=None, max_modes=240, max_tuples=6000,
                              max_parent_wires=6, max_geometry_work=1_000_000):
    """Generate finite point modes after independent sparse-geometry checks."""
    snapshot = _source_snapshot(source, max_geometry_work=max_geometry_work,
                                max_parent_wires=max_parent_wires)
    return make_point_modes(snapshot, node=node, precision=precision,
                            extension_degree=extension_degree, zeta=zeta,
                            max_modes=max_modes, max_tuples=max_tuples,
                            max_parent_wires=max_parent_wires,
                            _source_validation='geometry', _source_work=max_geometry_work)


def check_geometry_point_modes(certificate, *, max_parent_wires=6,
                               max_geometry_work=1_000_000):
    """Independently replay source geometry and every finite point mode."""
    _geometry_limit(max_geometry_work)
    verdict = check_point_modes(certificate, max_parent_wires=max_parent_wires,
                                _source_validation='geometry', _source_work=max_geometry_work)
    verdict.update({'source_validation': 'INDEPENDENT_FINITE_GEOMETRY',
                    'deterministic_trace_verified': False})
    return verdict


def build_geometry_point_children(parent, certificate, beta, *, max_parent_wires=6,
                                  max_geometry_work=1_000_000):
    """Construct one bounded tuple's children after geometry and mode replay."""
    _geometry_limit(max_geometry_work)
    if not isinstance(certificate, dict) or certificate.get('schema') != SCHEMA:
        raise ValueError('a point-mode certificate is required')
    ring, source = _ring_for(parent, certificate, max_parent_wires=max_parent_wires,
                             _source_validation='geometry', _source_work=max_geometry_work)
    return _build_point_children_checked(parent, certificate, beta, ring, source)


def contract_geometry_point_expansion(parent, certificate, *, max_parent_wires=6,
                                      max_geometry_work=1_000_000, max_tuples=3000,
                                      max_work=250_000, timeout_s=10.0,
                                      enable_hall_pruning=False):
    """Run the bounded child sum and independent direct half-edge oracle."""
    _geometry_limit(max_geometry_work)
    if not isinstance(certificate, dict) or certificate.get('schema') != SCHEMA:
        raise ValueError('a point-mode certificate is required')
    result = contract_point_child_expansion(
        parent, certificate, max_parent_wires=max_parent_wires, max_tuples=max_tuples,
        max_work=max_work, timeout_s=timeout_s, enable_hall_pruning=enable_hall_pruning,
        _source_validation='geometry', _source_work=max_geometry_work)
    result.update({'source_validation': 'INDEPENDENT_FINITE_GEOMETRY',
                   'deterministic_trace_verified': False,
                   'uniform_complexity_proven': False})
    return result


def direct_geometry_tuple_contribution(parent, certificate, beta, *, max_geometry_work=1_000_000,
                                       max_work=250_000, timeout_s=10.0):
    """Check one tuple by direct half-wire/row-selection enumeration.

    This independent small reference has a stricter three-parent-wire cap.
    """
    _geometry_limit(max_geometry_work)
    if not isinstance(certificate, dict) or certificate.get('schema') != SCHEMA:
        raise ValueError('a point-mode certificate is required')
    return direct_tuple_contribution(parent, certificate, beta, max_work=max_work,
                                     timeout_s=timeout_s, _source_validation='geometry',
                                     _source_work=max_geometry_work)


def certify_geometry_point_matching_zero(certificate, beta, *, max_parent_wires=6,
                                         max_geometry_work=1_000_000, max_work=100_000):
    """Certify one exact zero from a replayed finite geometry-mode support."""
    _geometry_limit(max_geometry_work)
    result = certify_point_mode_matching_zero(
        certificate, beta, max_work=max_work, max_parent_wires=max_parent_wires,
        _source_validation='geometry', _source_work=max_geometry_work)
    result['deterministic_trace_verified'] = False
    return result


def replay_geometry_point_matching_zero(mode_certificate, zero_certificate, *, max_parent_wires=6,
                                        max_geometry_work=1_000_000, max_work=100_000):
    """Independently replay a Hall-zero witness on a geometry-validated source."""
    _geometry_limit(max_geometry_work)
    result = replay_point_mode_matching_zero(
        mode_certificate, zero_certificate, max_work=max_work, max_parent_wires=max_parent_wires,
        _source_validation='geometry', _source_work=max_geometry_work)
    result['deterministic_trace_verified'] = False
    return result
