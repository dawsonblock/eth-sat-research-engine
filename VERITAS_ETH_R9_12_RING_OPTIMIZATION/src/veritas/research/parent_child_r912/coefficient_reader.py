"""Independent bounded expansion. Does not import the producer codec.

Each point owns its table. No references survive across points, so a missing
entry cannot be satisfied from a prior point or from an unbounded shared cache.
"""
from hashlib import sha256
from veritas.research.parent_child_r98.model import canonical, Refusal


def expand_point(envelope, *, max_expanded_bytes):
    if set(envelope) != {'kind','schema','coefficients','point'} or (
            envelope['kind'] != 'coefficient_point' or
            envelope['schema'] != 'VERITAS_COEFFICIENT_POINT_V1'):
        raise ValueError('coefficient envelope fields')
    table, point = envelope['coefficients'], envelope['point']
    if type(table) is not dict or type(point) is not dict or set(point) != {'kind','original','folded','support'} or point['kind'] != 'point':
        raise ValueError('coefficient point fields')
    if len(table)>65536:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT','coefficient table dimension')
    sizes = {}
    for name,value in table.items():
        if type(name) is not str or len(name)!=64 or any(c not in '0123456789abcdef' for c in name):
            raise ValueError('coefficient digest encoding')
        if type(value) is not list:
            raise ValueError('coefficient array required')
        raw = canonical(value)
        if sha256(raw).hexdigest()!=name:
            raise ValueError('altered coefficient content')
        sizes[name]=len(raw)
    # Reject expansion bombs before constructing the expanded canonical record.
    used=set(); allowance=len(canonical(point))
    rebuilt=dict(point)
    for side in ('original','folded'):
        if type(point[side]) is not dict or type(point[side].get('local')) is not list:
            raise ValueError('coefficient mode record')
        modes=dict(point[side]); entries=[]
        for item in modes['local']:
            if type(item) is not list or len(item)!=3:
                raise ValueError('coefficient port entry')
            row,column,ref=item
            if type(row) is not int or type(column) is not int or row<0 or column<0:
                raise ValueError('coefficient port identifier')
            if type(ref) is not dict or set(ref)!={'coefficient_sha256'}:
                raise ValueError('coefficient reference fields')
            key=ref['coefficient_sha256']
            if type(key) is not str or key not in sizes:
                raise ValueError('missing coefficient reference')
            used.add(key); allowance+=sizes[key]
            if allowance>max_expanded_bytes:
                raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT','expanded point byte cap')
            entries.append([row,column,table[key]])
        modes['local']=entries; rebuilt[side]=modes
    if used!=set(table):
        raise ValueError('unused coefficient definition')
    return rebuilt
