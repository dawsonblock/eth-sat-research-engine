"""Explicit finite algebraic aggregation; the original weighted stream is unchanged.

Modes with the same packet, source/target groups and source linear form may
be identified by summing their target coefficients. A target row is affine
in the resulting formal variables. Its product can contain only exponents
obtained by choosing at most one variable from each row. Exponents may exceed
one when several rows use the same variable. Neither rule assumes a cycle.
"""
from dataclasses import dataclass

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.parent_child_r98.model import ModeSet, Refusal, canonical, decode, digest
from .basis import _count, verify_packet_modes


@dataclass(frozen=True)
class SupportCertificate:
    payload: bytes

    @property
    def record(self):
        return decode(self.payload)

    @property
    def content_digest(self):
        return digest(self.payload)


def fold_source_forms(parent, layout, original, *, budget):
    """Sum coefficients only when the entire source form and ownership agree."""
    verify_packet_modes(parent, layout, original, budget=budget)
    record = original.certificate
    ring = ExtensionRing(record['precision'], parent.defining_polynomial,
                         max_precision_bits=budget.policy.max_precision)
    grouped = {}
    for mode in record['modes']:
        key = canonical([mode['packet'], mode['source_group'], mode['target_group'],
                         mode['column_terms']])
        if key not in grouped:
            grouped[key] = (dict(mode), {})
        head, rows = grouped[key]
        head['weight'] = min(head['weight'], mode['weight'])
        for row, coefficient in mode['rows']:
            rows[row] = ring.add(rows.get(row, ring.zero), tuple(coefficient[0]))
            budget.tick(ring.e)
    result = []
    for head, rows in grouped.values():
        head['rows'] = [[row, [list(value)]] for row, value in sorted(rows.items()) if value != ring.zero]
        if head['rows']:
            result.append(head)
    record['modes'] = result
    record['mode_tuple_count'] = _count(result, record['precision'], budget)
    raw = canonical(record)
    if len(raw) > min(20_000_000, budget.policy.max_certificate_bytes):
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'folded basis byte cap')
    return ModeSet(layout.content_digest, raw)


def build_support(original, folded, *, budget, row_certificate=None):
    """Boolean-support polynomial multiplication, with the weighted cutoff.

    This is an overapproximation of nonzero coefficients: cancellations may
    leave additional zeros. Every omitted exponent is zero or divisible by
    the point modulus. Intermediate support overflow refuses the whole call.
    """
    record = folded.certificate
    modes, precision = record['modes'], record['precision']
    incidence = {}
    active = None if row_certificate is None else set(row_certificate['nonconstant_row_ports'])
    for mid, mode in enumerate(modes):
        for row, _ in mode['rows']:
            if active is None or row in active:
                incidence.setdefault((mode['packet'], row), []).append(mid)
    weights = tuple(mode['weight'] for mode in modes)
    states = {(0,) * len(modes): 0}
    for row in sorted(incidence):
        updated = dict(states)
        for beta, weight in states.items():
            for mid in incidence[row]:
                budget.tick(len(modes) + 1)
                if weight + weights[mid] >= precision:
                    continue
                value = list(beta)
                value[mid] += 1
                updated[tuple(value)] = weight + weights[mid]
                if len(updated) > budget.policy.max_tuples:
                    raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'complete supported tuple cap')
        states = updated
    payload = canonical({
        'schema': 'VERITAS_R99_EXACT_AFFINE_SUPPORT_V1',
        'original_modes_digest': original.content_digest,
        'folded_modes_digest': folded.content_digest,
        'original_weighted_tuple_count': original.certificate['mode_tuple_count'],
        'folded_weighted_tuple_count': record['mode_tuple_count'],
        'tuples': sorted(states),
        'original_weighted_stream_enumerated': False,
        'rule': 'IDENTICAL_SOURCE_FORM_SUM_AND_AFFINE_ROW_SUPPORT',
        'source_qualified': False,
        'row_certificate': row_certificate,
    })
    if len(payload) > min(20_000_000, budget.policy.max_certificate_bytes):
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'complete supported tuple byte cap')
    return SupportCertificate(payload)
