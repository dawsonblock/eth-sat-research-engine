"""Bounded independent transport decoding, before mathematical verification."""
import base64
from hashlib import sha256
import zlib
from veritas.research.parent_child_r98.model import Refusal, decode


def unpack_record(envelope, *, max_expanded_bytes):
    if (set(envelope) != {'kind', 'schema', 'decoded_size', 'content_sha256', 'data'} or
            envelope['kind'] != 'compressed_record' or envelope['schema'] != 'VERITAS_ZLIB_RECORD_V1'):
        raise ValueError('compressed record fields')
    size = envelope['decoded_size']
    if type(size) is not int or size < 0:
        raise ValueError('invalid expanded size')
    if size > max_expanded_bytes:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'record expansion byte cap')
    data = envelope['data']
    if type(data) is not str:
        raise ValueError('compressed payload must be ASCII base64')
    try:
        wire = base64.b64decode(data, validate=True)
        if base64.b64encode(wire).decode('ascii') != data:
            raise ValueError('noncanonical base64')
        decoder = zlib.decompressobj()
        # Never allocate the claimed output beyond its separately validated cap.
        raw = decoder.decompress(wire, size+1)
    except (zlib.error, UnicodeError) as exc:
        raise ValueError('invalid compressed payload') from exc
    if (len(raw) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or
            sha256(raw).hexdigest() != envelope['content_sha256']):
        raise ValueError('compressed record length, framing or digest mismatch')
    record = decode(raw, cap=max_expanded_bytes)
    if type(record) is not dict or record.get('kind') == 'compressed_record':
        raise ValueError('nested or non-record compression')
    return record
