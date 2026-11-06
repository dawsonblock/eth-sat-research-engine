"""Independent folding and support checker; no production child/entry calls.

The support checker enumerates bounded exponent multisets and tests whether
their occurrences admit an injective assignment to eligible target rows.
This is independent of the producer's successive support-polynomial product.
"""
from itertools import combinations_with_replacement
from math import comb

from veritas.research.parent_child_r98.model import Refusal, canonical
from .basis import verify_packet_modes, _count


def _check_fold(parent, layout, original, folded, budget):
    verify_packet_modes(parent, layout, original, budget=budget)
    src, got = original.certificate, folded.certificate
    if folded.layout_digest != layout.content_digest:
        raise ValueError('folded layout binding changed')
    buckets, keys = [], []
    for mode in src['modes']:
        key = (mode['packet'], mode['source_group'], mode['target_group'],
               tuple(tuple(term) for term in mode['column_terms']))
        if key not in keys:
            keys.append(key)
            buckets.append([])
        buckets[keys.index(key)].append(mode)
        budget.tick(len(keys))
    expected = []
    modulus, e = 1 << src['precision'], src['extension_degree']
    for bucket in buckets:
        head = dict(bucket[0])
        head['weight'] = min(m['weight'] for m in bucket)
        row_ids = sorted({row for m in bucket for row, _ in m['rows']})
        head['rows'] = []
        for row in row_ids:
            values = [coefficient[0] for m in bucket for r, coefficient in m['rows'] if r == row]
            value = [sum(v[c] for v in values) % modulus for c in range(e)]
            budget.tick(e * len(values))
            if any(value):
                if any(c % (1 << head['weight']) for c in value):
                    raise ValueError('folded target divisibility failed')
                head['rows'].append([row, [value]])
        if head['rows']:
            expected.append(head)
    src['modes'] = expected
    src['mode_tuple_count'] = _count(expected, src['precision'], budget)
    if canonical(src) != canonical(got):
        raise ValueError('altered folded coefficients, source form or ownership')


def _match(units, eligible, budget):
    owner = {}

    def assign(unit, seen):
        for row in eligible[units[unit]]:
            budget.tick()
            if row in seen:
                continue
            seen.add(row)
            if row not in owner or assign(owner[row], seen):
                owner[row] = unit
                return True
        return False

    return all(assign(unit, set()) for unit in range(len(units)))


def verify_support(parent, layout, original, folded, certificate, *, budget):
    _check_fold(parent, layout, original, folded, budget)
    data, folded_record = certificate.record, folded.certificate
    modes, precision = folded_record['modes'], folded_record['precision']
    active = None
    if data.get('row_certificate') is not None:
        from .row_degree import verify_row_degree
        active = set(verify_row_degree(parent, layout.a, data['row_certificate'], budget=budget))
    eligible = [tuple((m['packet'], row) for row, _ in m['rows'] if active is None or row in active) for m in modes]
    rows = len({r for targets in eligible for r in targets})
    candidates = comb(rows + len(modes), len(modes))
    if candidates > min(1_000_000, budget.policy.max_work - budget.work):
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'independent complete support candidate cap')
    # Avoid interpreter recursion limits in the augmenting-path checker.
    if rows > 512:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'independent support matching depth cap')
    expected = []
    for total in range(rows + 1):
        for units in combinations_with_replacement(range(len(modes)), total):
            budget.tick(len(units) + 1)
            if sum(modes[mid]['weight'] for mid in units) >= precision:
                continue
            if not _match(units, eligible, budget):
                continue
            beta = [0] * len(modes)
            for mid in units:
                beta[mid] += 1
            expected.append(beta)
            if len(expected) > budget.policy.max_tuples:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'independent supported tuple cap')
    record = {
        'schema': 'VERITAS_R99_EXACT_AFFINE_SUPPORT_V1',
        'original_modes_digest': original.content_digest,
        'folded_modes_digest': folded.content_digest,
        'original_weighted_tuple_count': original.certificate['mode_tuple_count'],
        'folded_weighted_tuple_count': folded.certificate['mode_tuple_count'],
        'tuples': sorted(expected),
        'original_weighted_stream_enumerated': False,
        'rule': 'IDENTICAL_SOURCE_FORM_SUM_AND_AFFINE_ROW_SUPPORT',
        'source_qualified': False,
        'row_certificate': data.get('row_certificate'),
    }
    if canonical(record) != certificate.payload:
        raise ValueError('incomplete, duplicate, substituted or altered support certificate')
    return {'support_completeness': 'INDEPENDENT_EXPONENT_MATCHING',
            'evaluated_tuples': len(expected), 'candidate_count': candidates,
            'original_weighted_stream_enumerated': False, 'source_qualified': False}
