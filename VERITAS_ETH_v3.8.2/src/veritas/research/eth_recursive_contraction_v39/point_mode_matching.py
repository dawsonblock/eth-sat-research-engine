"""Replayable finite Hall-zero certificates for checked point-mode supports.

The bounded mode validator is run first. Its own internal replay and JSON
hashing are not charged to this module's matching-work budget.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .mode_matching import _BudgetExceeded, _Work, certify_structural_tuple_matching
from .point_modes import check_point_modes


SCHEMA = 'VERITAS_ETH_POINT_MODE_HALL_ZERO_V1'
CLAIM = 'FINITE_CHECKED_POINT_MODE_HALL_ZERO_ONLY'


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode('utf8')).hexdigest()


def _beta_valid(beta, mode_count):
    return (isinstance(beta, (tuple, list)) and len(beta) == mode_count and
            all(type(value) is int and value >= 0 for value in beta))


def _verify_hall_witness(modes, beta, witness, work):
    """Recompute a Hall inequality without invoking the matching algorithm."""
    if type(witness) is not dict or set(witness) != {
            'packet', 'target_group', 'mode_indices', 'row_ids', 'demand', 'available_rows'}:
        raise ValueError('invalid Hall witness fields')
    indices = witness['mode_indices']
    if (type(indices) is not list or not indices or
            any(type(i) is not int or not 0 <= i < len(modes) for i in indices) or
            indices != sorted(set(indices))):
        raise ValueError('invalid Hall witness mode indices')
    if (type(witness['packet']) is not int or type(witness['target_group']) is not int or
            type(witness['demand']) is not int or type(witness['available_rows']) is not int or
            type(witness['row_ids']) is not list or
            any(type(row) is not int for row in witness['row_ids'])):
        raise ValueError('invalid Hall witness values')
    key = (witness['packet'], witness['target_group'])
    neighbors = set()
    demand = 0
    for index in indices:
        work.tick()
        mode = modes[index]
        if (mode['packet'], mode['target_group']) != key or beta[index] < 1:
            raise ValueError('Hall witness crosses groups or contains a zero-demand mode')
        demand += beta[index]
        for row_id, _ in mode['rows']:
            work.tick()
            neighbors.add(row_id)
    if (witness['row_ids'] != sorted(neighbors) or witness['demand'] != demand or
            witness['available_rows'] != len(neighbors) or demand <= len(neighbors)):
        raise ValueError('Hall witness does not prove a deficiency')


def _mode_status(mode_certificate, max_parent_wires, *, _source_validation='canonical',
                 _source_work=1_000_000):
    verdict = check_point_modes(mode_certificate, max_parent_wires=max_parent_wires,
                                _source_validation=_source_validation, _source_work=_source_work)
    if verdict.get('valid') is True:
        return None
    return {'valid': False, 'status': verdict.get('status', 'INVALID_POINT_MODES'),
            'reason': verdict.get('reason'), 'mode_validation_work_metered': False}


def certify_point_mode_matching_zero(mode_certificate, beta, *, max_work=100_000,
                                     max_parent_wires=6, _source_validation='canonical',
                                     _source_work=1_000_000):
    """Validate a finite mode expansion, then seek a replayable Hall zero.

    A feasible matching has no nonzero implication and returns no certificate.
    ``max_work`` covers matching and witness replay, not mode validation,
    hashing, wall time, or complete arithmetic and allocation cost.
    """
    if type(max_work) is not int or not 1 <= max_work <= 2_000_000:
        raise ValueError('max_work must be an integer in 1..2000000')
    failure = _mode_status(mode_certificate, max_parent_wires,
                           _source_validation=_source_validation, _source_work=_source_work)
    if failure is not None:
        return failure
    modes = mode_certificate['modes']
    if not _beta_valid(beta, len(modes)):
        return {'valid': False, 'status': 'INVALID_WEIGHTED_TUPLE',
                'mode_validation_work_metered': False}
    match = certify_structural_tuple_matching(modes, beta, max_work=max_work)
    if match['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT':
        return {'valid': False, 'status': match['status'], 'work_units': match['work_units'],
                'mode_validation_work_metered': False}
    if match['status'] == 'MATCHING_FEASIBLE_ONLY':
        return {'valid': True, 'status': 'MATCHING_FEASIBLE_ONLY',
                'nonzero_proven': False, 'work_units': match['work_units'],
                'mode_validation_work_metered': False}
    work = _Work(max_work)
    work.used = match['work_units']
    try:
        _verify_hall_witness(modes, beta, match['witness'], work)
    except _BudgetExceeded:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT',
                'work_units': work.used, 'mode_validation_work_metered': False}
    certificate = {'schema': SCHEMA, 'claim': CLAIM,
                   'mode_certificate_sha256': _digest(mode_certificate),
                   'beta': list(beta), 'witness': match['witness']}
    return {'valid': True, 'status': 'FINITE_STRUCTURAL_ZERO_CERTIFIED',
            'certificate': certificate, 'work_units': work.used,
            'support_provenance_verified': True,
            'mode_validation_work_metered': False,
            'uniform_complexity_proven': False}


def replay_point_mode_matching_zero(mode_certificate, certificate, *, max_work=100_000,
                                   max_parent_wires=6, _source_validation='canonical',
                                   _source_work=1_000_000):
    """Replay the checked mode source and independently verify the Hall set."""
    if type(max_work) is not int or not 1 <= max_work <= 2_000_000:
        raise ValueError('max_work must be an integer in 1..2000000')
    failure = _mode_status(mode_certificate, max_parent_wires,
                           _source_validation=_source_validation, _source_work=_source_work)
    if failure is not None:
        return failure
    work = _Work(max_work)
    try:
        if (type(certificate) is not dict or set(certificate) != {
                'schema', 'claim', 'mode_certificate_sha256', 'beta', 'witness'} or
                certificate['schema'] != SCHEMA or certificate['claim'] != CLAIM or
                certificate['mode_certificate_sha256'] != _digest(mode_certificate) or
                type(certificate['beta']) is not list or
                not _beta_valid(certificate['beta'], len(mode_certificate['modes']))):
            raise ValueError('invalid certificate or mode-certificate binding')
        _verify_hall_witness(mode_certificate['modes'], certificate['beta'],
                             certificate['witness'], work)
        return {'valid': True, 'status': 'FINITE_STRUCTURAL_ZERO_REPLAYED',
                'work_units': work.used, 'support_provenance_verified': True,
                'mode_validation_work_metered': False,
                'uniform_complexity_proven': False}
    except _BudgetExceeded:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT',
                'work_units': work.used, 'mode_validation_work_metered': False}
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        return {'valid': False, 'status': 'INVALID_ZERO_CERTIFICATE',
                'reason': str(exc), 'mode_validation_work_metered': False}
