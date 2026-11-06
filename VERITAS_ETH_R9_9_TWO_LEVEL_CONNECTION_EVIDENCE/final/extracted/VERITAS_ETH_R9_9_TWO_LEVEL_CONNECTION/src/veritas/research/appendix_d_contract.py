"""Fail-closed finite call contract for the source-pinned Appendix D schedule.

This checks observable input facts for one call. It is not a verifier for the
manuscript's packing or recursive contraction theorems.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from veritas.research.tensor import TensorNetwork
from veritas.research.appendix_d_schedule import schedule_preflight


SOURCE_REVISION = '4eaee87548250b2682affda7d05d947c05554bae'
RING_DESCRIPTION = '(Z/2^P Z)[V]/(V^ell)'


def _description(network: TensorNetwork) -> bytes:
    payload = {
        'edges': network.edges,
        'factors': [{'ports': f.ports, 'table': f.table, 'label': f.label}
                    for f in network.factors],
    }
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


@dataclass(frozen=True)
class TensorCallContract:
    """Immutable per-call limits and the creation-time network digest."""
    size_parameter: int
    description_length: int
    depth: int
    size_constant: int
    root_precision: int
    precision: int
    truncation_order: int
    entry_bit_limit: int
    max_factors: int
    max_table_entries: int
    precision_path: tuple[int, ...]
    creation_digest: str
    manuscript_revision: str = SOURCE_REVISION
    entry_creation_precisions: tuple[int, ...] = ()
    max_precision_bits: int = 4096

    def __post_init__(self):
        ints = (self.size_parameter, self.description_length, self.depth,
                self.size_constant, self.root_precision, self.precision,
                self.truncation_order, self.entry_bit_limit, self.max_factors,
                self.max_table_entries, self.max_precision_bits)
        if any(type(x) is not int for x in ints):
            raise ValueError('contract limits must be exact integers')
        if (self.size_parameter < 2 or self.description_length < 0 or self.depth < 0 or
                self.size_constant < 1 or self.root_precision < 1 or
                self.precision < 1 or self.max_precision_bits < 1 or
                self.truncation_order < 1 or self.entry_bit_limit < 1 or
                self.max_factors < 0 or self.max_table_entries < 1):
            raise ValueError('contract limits outside supported range')
        if type(self.precision_path) is not tuple or len(self.precision_path) != self.depth + 1:
            raise ValueError('precision path must be an immutable root-to-call tuple')
        if (any(type(p) is not int or p < 1 for p in self.precision_path) or
                self.precision_path[0] != self.root_precision or
                self.precision_path[-1] != self.precision or
                any(left >= right for left, right in zip(self.precision_path, self.precision_path[1:]))):
            raise ValueError('precision path does not match the declared call precision')
        if (type(self.entry_creation_precisions) is not tuple or
                any(type(p) is not int or p not in self.precision_path
                    for p in self.entry_creation_precisions)):
            raise ValueError('entry creation precisions must be immutable path precisions')
        if self.manuscript_revision != SOURCE_REVISION:
            raise ValueError('unsupported or unpinned manuscript revision')
        if (type(self.creation_digest) is not str or len(self.creation_digest) != 64 or
                any(c not in '0123456789abcdef' for c in self.creation_digest)):
            raise ValueError('invalid creation-time description digest')


def bind_tensor_call(network: TensorNetwork, *, size_parameter: int,
                     description_length: int, depth: int, size_constant: int,
                     root_precision: int, precision: int, truncation_order: int,
                     entry_bit_limit: int = 4096, max_factors: int = 100_000,
                     max_table_entries: int = 1_000_000,
                     precision_path: tuple[int, ...] | None = None,
                     entry_creation_precisions: tuple[int, ...] | None = None,
                     max_precision_bits: int = 4096) -> TensorCallContract:
    """Capture an immutable input description and caller-declared limits."""
    if not isinstance(network, TensorNetwork):
        raise TypeError('TensorNetwork required')
    if precision_path is None:
        precision_path = (precision,) if depth == 0 else ()
    if entry_creation_precisions is None:
        entry_creation_precisions = (root_precision,) * len(network.factors)
    return TensorCallContract(size_parameter, description_length, depth,
                              size_constant, root_precision, precision,
                              truncation_order, entry_bit_limit, max_factors,
                              max_table_entries, precision_path,
                              sha256(_description(network)).hexdigest(),
                              entry_creation_precisions=entry_creation_precisions,
                              max_precision_bits=max_precision_bits)


def validate_tensor_call(network: TensorNetwork, contract: TensorCallContract) -> dict:
    """Check one call's input bounds and creation-time identity.

    Resource ceilings are caller-declared finite caps. A cap or hypothesis
    miss returns an inconclusive result and never a partial contraction.
    """
    if not isinstance(network, TensorNetwork) or not isinstance(contract, TensorCallContract):
        raise TypeError('TensorNetwork and TensorCallContract required')
    if sha256(_description(network)).hexdigest() != contract.creation_digest:
        return {'valid': False, 'status': 'INVALID_CREATION_DESCRIPTION'}
    if len(contract.entry_creation_precisions) != len(network.factors):
        return {'valid': False, 'status': 'INVALID_CREATION_PRECISIONS'}
    if contract.precision > contract.max_precision_bits:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT',
                'reason': 'precision limit exceeded'}
    encoded_bits = 8 * len(_description(network))
    if encoded_bits > contract.description_length:
        return {'valid': False, 'status': 'OUTSIDE_THEOREM_INPUT_HYPOTHESES',
                'hypothesis': 'description_length',
                'encoded_description_bits': encoded_bits,
                'declared_description_bits': contract.description_length}
    entries = sum(len(f.table) for f in network.factors)
    max_bits = max((abs(v).bit_length() for f in network.factors for v in f.table), default=0)
    if len(network.factors) > contract.max_factors or entries > contract.max_table_entries or max_bits > contract.entry_bit_limit:
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT',
                'factor_count': len(network.factors), 'table_entries': entries,
                'max_entry_bits': max_bits}
    schedule = schedule_preflight(contract.size_parameter, network.edges,
                                  max((len(f.ports) for f in network.factors), default=0),
                                  contract.depth, size_constant=contract.size_constant)
    if schedule['status'] in ('INVALID_DEGREE', 'INVALID_RECURSIVE_SIZE_BOUND',
                              'INVALID_DEGREE_BOUND'):
        return {'valid': False, 'status': 'OUTSIDE_THEOREM_INPUT_HYPOTHESES',
                'schedule_status': schedule['status'], 'schedule': schedule}
    if schedule['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT':
        return {'valid': False, 'status': 'INCONCLUSIVE_RESOURCE_LIMIT', 'schedule': schedule}
    if schedule['status'] not in ('ACTIVE_NUMERIC_PRECONDITIONS_MET', 'DIRECT_LEAF_ALLOWED'):
        return {'valid': False, 'status': 'INCONCLUSIVE_SCHEDULE_OR_PACKING',
                'schedule': schedule}
    return {'valid': True, 'status': 'FINITE_CALL_CONTRACT_CHECKED',
            'manuscript_revision': contract.manuscript_revision,
            'description_length': contract.description_length,
            'ring': RING_DESCRIPTION, 'precision': contract.precision,
            'truncation_order': contract.truncation_order,
            'input_entry_kind': 'explicit_integer_tables',
            'extension_ring_validated': False,
            'precision_increment_formula_validated': False,
            'canonical_entry_lifts': tuple(
                tuple(v % (1 << created_at) for v in factor.table)
                for factor, created_at in zip(network.factors, contract.entry_creation_precisions)),
            'entry_creation_precisions': contract.entry_creation_precisions,
            'precision_path': contract.precision_path,
            'schedule': schedule, 'universal_theorem_proven': False}
