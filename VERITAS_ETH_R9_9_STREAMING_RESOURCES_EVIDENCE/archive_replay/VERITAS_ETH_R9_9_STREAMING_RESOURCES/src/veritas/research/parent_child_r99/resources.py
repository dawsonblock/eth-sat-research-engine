"""Bounded finite ring preparation and exact computation reuse.

No arbitrary change of extension basis is an embedding. Only scalar root
recipes can be transported by this adapter; generated packet recipes refuse.
"""
from collections import OrderedDict
from dataclasses import replace

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.parent_child_r98.model import canonical, decode, digest, Refusal, Semantics
from veritas.research.tapered_v4.source_recipes import make_reference, EntryLimits


def prepare_scalar_field(parent, required_points, *, max_degree=12):
    if type(required_points) is not int or not 1 <= required_points <= 4096:
        raise ValueError('bounded positive interpolation grid required')
    if type(max_degree) is not int or not 2 <= max_degree <= 12:
        raise ValueError('extension degree cap must be 2..12')
    degree = max(2, (required_points - 1).bit_length())
    if degree > max_degree:
        raise Refusal('INCONCLUSIVE_RESOURCE_LIMIT', 'interpolation extension cap')
    if parent.defining_polynomial.bit_length() - 1 >= degree:
        return parent
    if (parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT or parent.depth != 0 or
            parent.ancestry_digest is not None or parent.source_context is not None):
        raise ValueError('field transport is restricted to finite scalar roots')
    f = first_irreducible(degree)
    # Independent bounded trial division, separate from the Rabin constructor.
    for d in range(1, degree // 2 + 1):
        for divisor in range(1 << d, 1 << (d + 1)):
            remainder = f
            while remainder.bit_length() >= divisor.bit_length():
                remainder ^= divisor << (remainder.bit_length() - divisor.bit_length())
            if not remainder:
                raise ValueError('extension polynomial has a proper factor')
    vertices = []
    for vertex in parent.vertices:
        ref = vertex.tensor
        data = decode(ref.description)['data']
        kind = ref.recipe_kind.split(':')[-1]
        if kind == 'dense':
            if any(len(entry) != 1 or any(entry[0][1:]) for entry in data):
                raise ValueError('non-scalar extension entries require a certified embedding')
            data = [[[entry[0][0]] + [0] * (degree - 1)] for entry in data]
        elif kind not in ('equality', 'clause'):
            raise ValueError('cannot transport generated packet recipes')
        updated = make_reference(kind=kind, arity=ref.arity, creation_precision=ref.creation_precision,
            defining_polynomial=f, jet_length=1, data=data,
            limits=EntryLimits(max_precision_bits=max(1024, ref.creation_precision)))
        vertices.append(replace(vertex, tensor=updated))
    return replace(parent, defining_polynomial=f, vertices=tuple(vertices))


def computation_key(call, schedule):
    record = call.record()
    # Ancestry is provenance, not an entry operand. All graph labels, ordered
    # ports, immutable recipe bytes, creation/evaluation precision, depth and
    # source context are retained. No graph-isomorphism or ring-lift guessing.
    record.pop('ancestry_digest')
    return digest({'version': 1, 'call': record, 'remaining_schedule': schedule,
                   'algorithm': 'FULL_TAPERED_CERTIFIED_SUPPORT_STREAM_V1'})


class ExactCache:
    def __init__(self, max_bytes):
        if type(max_bytes) is not int or max_bytes < 0:
            raise ValueError('nonnegative cache byte budget required')
        self.max_bytes, self.bytes, self.peak = max_bytes, 0, 0
        self.hits = self.misses = self.evictions = 0
        self.values = OrderedDict()

    def get(self, key):
        if key not in self.values:
            self.misses += 1
            return None
        self.hits += 1
        self.values.move_to_end(key)
        return self.values[key][0]

    def put(self, key, value):
        size = len(key) + len(canonical(value))
        if size > self.max_bytes:
            return
        if key in self.values:
            self.bytes -= self.values.pop(key)[1]
        while self.bytes + size > self.max_bytes:
            _, (_, old) = self.values.popitem(last=False)
            self.bytes -= old
            self.evictions += 1
        self.values[key] = (value, size)
        self.bytes += size
        self.peak = max(self.peak, self.bytes)

    def report(self):
        return {'hits': self.hits, 'misses': self.misses, 'evictions': self.evictions,
                'peak_payload_bytes': self.peak, 'max_payload_bytes': self.max_bytes,
                'python_object_overhead_included': False}
