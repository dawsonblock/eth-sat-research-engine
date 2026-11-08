"""Optional lossless wire compression; coefficient addressing remains inside."""
import base64
from hashlib import sha256
import zlib
from veritas.research.parent_child_r98.model import canonical


def pack_record(record):
    raw = canonical(record)
    if len(raw) < 1024:
        return record
    compressed = zlib.compress(raw, level=6)
    envelope = {'kind': 'compressed_record', 'schema': 'VERITAS_ZLIB_RECORD_V1',
        'decoded_size': len(raw), 'content_sha256': sha256(raw).hexdigest(),
        'data': base64.b64encode(compressed).decode('ascii')}
    return envelope if len(canonical(envelope)) < len(raw) else record
