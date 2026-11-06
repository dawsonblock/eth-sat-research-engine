"""Canonical finite encoding of padded directed-class slots as packet slots.

The address convention implements the finite indexing used by
`lem:tensor-packets`: unequal symbol coordinates select an orientation bit;
equal coordinates use the remaining packet-slot bits as a copy index.
This module is an executable finite refinement target. It does not by itself
prove the source's universal construction or its recursive contraction lemma.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class PacketAddress:
    """Canonical address of one padded slot.

    `pattern` is an ordered tuple of `(low, high)` pairs. `packet` is the
    index within that pattern. `slot` is the low-to-high coordinate bit word
    represented as an integer in `[0, 2**a)`.
    """

    pattern: tuple[tuple[int, int], ...]
    packet: int
    slot: int


@dataclass(frozen=True, order=True)
class DirectedClassOffset:
    """A row/column tagged directed symbol class and a padded offset."""

    row: tuple[int, ...]
    column: tuple[int, ...]
    offset: int


def _validate_dimensions(radix: int, width: int, padded_height: int) -> None:
    if type(radix) is not int or radix < 1:
        raise ValueError("radix must be a positive integer")
    if type(width) is not int or width < 0:
        raise ValueError("width must be a nonnegative integer")
    if type(padded_height) is not int or padded_height < 0:
        raise ValueError("padded height must be a nonnegative integer")
    L = 1 << width
    if padded_height % L:
        raise ValueError("padded height must be divisible by packet width")


def _validate_words(row, column, radix: int, width: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if not isinstance(row, (tuple, list)) or not isinstance(column, (tuple, list)):
        raise ValueError("row and column labels must be sequences")
    row, column = tuple(row), tuple(column)
    if len(row) != width or len(column) != width:
        raise ValueError("label width mismatch")
    if any(type(x) is not int or not 0 <= x < radix for x in row + column):
        raise ValueError("label symbol outside radix")
    # Row and column remain separate tagged words even when their coordinates
    # contain equal integers.
    return row, column


def _pattern_and_equal_coordinates(row: tuple[int, ...], column: tuple[int, ...]):
    pattern = tuple((min(x, y), max(x, y)) for x, y in zip(row, column))
    equal_coordinates = tuple(i for i, (x, y) in enumerate(pattern) if x == y)
    return pattern, equal_coordinates


def encode_class_offset(
    row,
    column,
    offset: int,
    *,
    radix: int,
    width: int,
    padded_height: int,
) -> PacketAddress:
    """Encode one `(directed class, padded offset)` as a pattern packet slot."""
    _validate_dimensions(radix, width, padded_height)
    row, column = _validate_words(row, column, radix, width)
    if type(offset) is not int or not 0 <= offset < padded_height:
        raise ValueError("offset outside padded class")

    pattern, equal_coordinates = _pattern_and_equal_coordinates(row, column)
    copies = 1 << len(equal_coordinates)
    packet, copy_index = divmod(offset, copies)

    slot = 0
    copy_rank = 0
    for coordinate, ((low, high), row_symbol, col_symbol) in enumerate(
        zip(pattern, row, column)
    ):
        if low != high:
            bit = int(row_symbol > col_symbol)
        else:
            bit = (copy_index >> copy_rank) & 1
            copy_rank += 1
        slot |= bit << coordinate
    return PacketAddress(pattern, packet, slot)


def decode_packet_address(
    address: PacketAddress,
    *,
    radix: int,
    width: int,
    padded_height: int,
) -> DirectedClassOffset:
    """Decode a valid packet address back to its directed class and offset."""
    _validate_dimensions(radix, width, padded_height)
    if not isinstance(address, PacketAddress):
        raise ValueError("invalid packet address type")
    if (not isinstance(address.pattern, tuple) or len(address.pattern) != width or
            any(not isinstance(pair, tuple) or len(pair) != 2 or
                type(pair[0]) is not int or type(pair[1]) is not int or
                not 0 <= pair[0] <= pair[1] < radix for pair in address.pattern)):
        raise ValueError("invalid unordered symbol pattern")
    if type(address.packet) is not int or address.packet < 0:
        raise ValueError("invalid packet index")
    L = 1 << width
    if type(address.slot) is not int or not 0 <= address.slot < L:
        raise ValueError("slot outside packet")

    equal_coordinates = tuple(i for i, (low, high) in enumerate(address.pattern)
                              if low == high)
    copies = 1 << len(equal_coordinates)
    if address.packet >= padded_height // copies:
        raise ValueError("packet index outside padded pattern block")

    row, column = [], []
    copy_index = 0
    copy_rank = 0
    for coordinate, (low, high) in enumerate(address.pattern):
        bit = (address.slot >> coordinate) & 1
        if low != high:
            row.append(high if bit else low)
            column.append(low if bit else high)
        else:
            row.append(low)
            column.append(low)
            copy_index |= bit << copy_rank
            copy_rank += 1

    offset = address.packet * copies + copy_index
    if offset >= padded_height:
        # This should follow from the packet bound and copy bit width; keep the
        # check at the external validation boundary nonetheless.
        raise ValueError("decoded offset outside padded class")
    return DirectedClassOffset(tuple(row), tuple(column), offset)


def edge_occurrence_address(packing, edge_id: int) -> PacketAddress:
    """Return the canonical padded-slot address of one edge occurrence id."""
    if type(edge_id) is not int or not 0 <= edge_id < len(packing.edges):
        raise ValueError("edge occurrence id outside input")
    row_vertex, column_vertex = packing.edges[edge_id]
    row = tuple(packing.rows[row_vertex])
    column = tuple(packing.cols[column_vertex])
    bucket = packing.classes.get((row, column))
    if bucket is None:
        raise ValueError("edge occurrence is absent from its directed class")
    offset = bisect_left(bucket, edge_id)
    if offset == len(bucket) or bucket[offset] != edge_id:
        raise ValueError("edge occurrence id is absent from its class bucket")
    return encode_class_offset(row, column, offset, radix=packing.r, width=packing.a,
                               padded_height=packing.H)


def edge_occurrence_at_address(packing, address: PacketAddress) -> int | None:
    """Resolve an address against a finite packing; return None for padding."""
    decoded = decode_packet_address(address, radix=packing.r, width=packing.a,
                                   padded_height=packing.H)
    bucket = packing.classes.get((decoded.row, decoded.column), ())
    return bucket[decoded.offset] if decoded.offset < len(bucket) else None

