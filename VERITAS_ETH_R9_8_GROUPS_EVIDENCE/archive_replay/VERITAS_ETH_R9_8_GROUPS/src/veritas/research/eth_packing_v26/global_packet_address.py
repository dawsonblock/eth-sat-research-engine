"""Bounded index from real edge occurrences to canonical packet addresses.

This adapter accepts either existing ``ImplicitPacking`` constructor.  It
checks the class buckets against the ordered input edges before using the
production codec.  It does not certify how the vertex labels were selected.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .expectation import PackingBudgetExceeded, validate_edges
from .implicit import ImplicitPacking
from .packet_bijection import (
    PacketAddress,
    decode_packet_address as decode_class_address,
    edge_occurrence_address,
)

MAX_INDEX_EDGES = 1_000_000
MAX_INDEX_WIDTH = 64
MAX_VERTEX_ID_BITS = 4096


@dataclass(frozen=True)
class GlobalPacketIndex:
    """Immutable address table for an already-constructed finite packing."""

    radix: int
    width: int
    padded_height: int
    _edges: tuple = field(repr=False)
    _rows: tuple = field(repr=False)
    _columns: tuple = field(repr=False)
    _addresses: tuple[PacketAddress, ...] = field(repr=False)
    _occupied: Mapping = field(repr=False, compare=False)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def occupied_count(self) -> int:
        return len(self._occupied)

    def address_of(self, edge_id: int) -> PacketAddress:
        if type(edge_id) is not int or not 0 <= edge_id < self.edge_count:
            raise ValueError("edge occurrence id outside input")
        return self._addresses[edge_id]

    def edge_at(self, address: PacketAddress) -> int | None:
        """Return an edge occurrence, or None for a valid padded slot."""
        decode_class_address(address, radix=self.radix, width=self.width,
                             padded_height=self.padded_height)
        return self._occupied.get(address)


def _checked_source(packing, *, max_edges: int, max_work: int):
    if not isinstance(packing, ImplicitPacking):
        raise ValueError("ImplicitPacking required")
    if type(max_edges) is not int or not 0 <= max_edges <= MAX_INDEX_EDGES:
        raise ValueError("invalid edge cap")
    if type(max_work) is not int or max_work < 0:
        raise ValueError("invalid index work cap")
    if not isinstance(packing.edges, (tuple, list)):
        raise ValueError("edges must be a finite sequence")
    if len(packing.edges) > max_edges:
        raise PackingBudgetExceeded("global packet index edge cap exceeded")
    if (type(packing.r) is not int or not 2 <= packing.r <= 64 or
            type(packing.a) is not int or not 1 <= packing.a <= MAX_INDEX_WIDTH):
        raise ValueError("unsupported radix or label width")
    if not all(isinstance(x, Mapping) for x in (packing.rows, packing.cols, packing.classes)):
        raise ValueError("invalid label or class mapping")
    m, a = len(packing.edges), packing.a
    if len(packing.rows) > m or len(packing.cols) > m or len(packing.classes) > m:
        raise ValueError("extra vertices or classes")
    # Coarse admission metric includes binary searches within class buckets
    # and sorting the retained vertex labels; this is not a bit-work bound.
    estimated = (m * (4 * a + 10 + m.bit_length()) +
                 (len(packing.rows) + len(packing.cols)) * (a + m.bit_length()))
    if estimated > max_work:
        raise PackingBudgetExceeded("global packet index work cap exceeded")
    edges = validate_edges(packing.edges)
    if any(u.bit_length() > MAX_VERTEX_ID_BITS or v.bit_length() > MAX_VERTEX_ID_BITS
           for u, v in edges):
        raise ValueError("vertex identifier exceeds index cap")
    if set(packing.rows) != {u for u, _ in edges} or set(packing.cols) != {v for _, v in edges}:
        raise ValueError("vertex labels do not match input edges")

    def labels(source):
        result = {}
        for vertex, word in source.items():
            if (type(vertex) is not int or vertex < 0 or
                    not isinstance(word, (list, tuple)) or len(word) != a or
                    any(type(x) is not int or not 0 <= x < packing.r for x in word)):
                raise ValueError("invalid tagged vertex label")
            result[vertex] = tuple(word)
        return result

    rows, columns = labels(packing.rows), labels(packing.cols)
    classes = {}
    for edge_id, (u, v) in enumerate(edges):
        classes.setdefault((rows[u], columns[v]), []).append(edge_id)
    expected = {key: tuple(ids) for key, ids in classes.items()}
    actual, bucket_entries = {}, 0
    for key, ids in packing.classes.items():
        if not isinstance(ids, (tuple, list)) or len(ids) > m:
            raise ValueError("malformed or oversized class bucket")
        bucket_entries += len(ids)
        if bucket_entries > m:
            raise ValueError("too many class bucket entries")
        if any(type(i) is not int for i in ids):
            raise ValueError("invalid edge occurrence id in class bucket")
        actual[key] = tuple(ids)
    if actual != expected:
        raise ValueError("class buckets do not preserve edge occurrence order")
    width = 1 << a
    maximum = max((len(ids) for ids in expected.values()), default=0)
    height = ((maximum + width - 1) // width) * width
    if type(packing.H) is not int or packing.H != height:
        raise ValueError("padded class height mismatch")
    return edges, rows, columns, expected, height


def build_global_packet_index(packing, *, max_edges=100_000,
                              max_work=5_000_000) -> GlobalPacketIndex:
    """Construct a bounded, collision-checked index of real edge occurrences."""
    edges, rows, columns, _, height = _checked_source(
        packing, max_edges=max_edges, max_work=max_work)
    addresses, occupied = [], {}
    for edge_id in range(len(edges)):
        address = edge_occurrence_address(packing, edge_id)
        if address in occupied:
            raise ValueError("two edge occurrences occupy one packet address")
        occupied[address] = edge_id
        addresses.append(address)
    return GlobalPacketIndex(
        packing.r, packing.a, height, edges, tuple(sorted(rows.items())),
        tuple(sorted(columns.items())), tuple(addresses), MappingProxyType(occupied))


def decode_packet_address(packing, address: PacketAddress, *, max_edges=100_000,
                          max_work=5_000_000) -> int | None:
    """Resolve an address after validating the packing; use ``index.edge_at``
    for repeated lookups to avoid rebuilding the index each time.
    """
    return build_global_packet_index(packing, max_edges=max_edges,
                                     max_work=max_work).edge_at(address)


def audit_global_packet_index(packing, *, index=None, max_edges=100_000,
                              max_dense_slots=50_000, max_work=5_000_000):
    """Run the independently coded bounded address and builder audit."""
    from .global_packet_address_check import audit_global_packet_index as audit
    return audit(packing, index=index, max_edges=max_edges,
                 max_dense_slots=max_dense_slots, max_work=max_work)
