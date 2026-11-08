"""Point-scoped content addressing; no arithmetic or global blob cache."""
from hashlib import sha256
from veritas.research.parent_child_r98.model import canonical


def encode_point(event):
    if event.get('kind') != 'point':
        return event
    blobs = {}
    record = dict(event)
    for name in ('original', 'folded'):
        modes = dict(event[name])
        local = []
        for row, column, value in modes['local']:
            key = sha256(canonical(value)).hexdigest()
            if key in blobs and canonical(blobs[key]) != canonical(value):
                raise ValueError('coefficient digest collision')
            blobs[key] = value
            local.append([row, column, {'coefficient_sha256': key}])
        modes['local'] = local
        record[name] = modes
    return {'kind': 'coefficient_point', 'schema': 'VERITAS_COEFFICIENT_POINT_V1',
            'coefficients': blobs, 'point': record}
