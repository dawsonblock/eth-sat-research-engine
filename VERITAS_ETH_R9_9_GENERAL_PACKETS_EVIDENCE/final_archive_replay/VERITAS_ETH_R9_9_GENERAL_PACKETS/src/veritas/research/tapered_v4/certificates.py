"""Bounded, hash-chained execution transcripts; not formal proofs."""
from __future__ import annotations

from hashlib import sha256
import json

from .budget import Inconclusive


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


class Transcript:
    def __init__(self, maximum_bytes):
        self.maximum_bytes = maximum_bytes
        self.serialized_bytes = 0
        self.head = '0' * 64
        self.events = []

    def add(self, payload):
        digest = sha256(bytes.fromhex(self.head) + canonical(payload)).hexdigest()
        item = {'previous': self.head, 'payload': payload, 'hash': digest}
        size = len(canonical(item))
        if self.serialized_bytes + size > self.maximum_bytes:
            raise Inconclusive('INCONCLUSIVE_RESOURCE_LIMIT', 'serialized certificate budget exhausted')
        self.events.append(item)
        self.serialized_bytes += size
        self.head = digest


def same_json(left, right):
    return canonical(left) == canonical(right)
