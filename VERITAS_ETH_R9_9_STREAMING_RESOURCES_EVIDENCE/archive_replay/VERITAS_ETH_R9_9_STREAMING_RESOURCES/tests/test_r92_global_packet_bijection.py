from dataclasses import replace

import pytest

from veritas.research.eth_packing_v26 import (
    PacketAddress,
    construct_implicit_packing,
    decode_packet_address,
    edge_occurrence_address,
    edge_occurrence_at_address,
    encode_class_offset,
    verify_global_packet_bijection,
    verify_implicit_packing_packet_addresses,
)


@pytest.mark.parametrize("radix,width", [(2, 1), (2, 2), (3, 1), (3, 2)])
@pytest.mark.parametrize("height_multiple", [0, 1, 2])
def test_global_address_map_is_exhaustively_bijective(radix, width, height_multiple):
    L = 1 << width
    result = verify_global_packet_bijection(
        radix=radix, width=width, padded_height=height_multiple * L,
        max_addresses=200_000)
    assert result["valid"] is True
    assert result["status"] == "FINITE_GLOBAL_PACKET_BIJECTION_CHECKED"
    assert result["padded_slots"] == result["packet_addresses"]
    assert result["roundtrips"] == result["padded_slots"]
    assert result["independent_set_equality"] is True


def test_production_encode_decode_roundtrips_side_tagged_words_and_offsets():
    # Same numeric IDs/symbols are legal on row and column sides; direction is
    # represented by the ordered row/column pair, not collapsed by equality.
    cases = [((0, 1, 1), (1, 1, 0)), ((0, 0), (0, 0)), ((2,), (0,))]
    for row, column in cases:
        radix = max((*row, *column)) + 1
        width = len(row)
        L = 1 << width
        H = 3 * L
        for offset in range(H):
            address = encode_class_offset(row, column, offset, radix=radix,
                                          width=width, padded_height=H)
            decoded = decode_packet_address(address, radix=radix, width=width,
                                            padded_height=H)
            assert (decoded.row, decoded.column, decoded.offset) == (row, column, offset)


def test_invalid_packet_addresses_and_nonmultiple_padding_are_rejected():
    with pytest.raises(ValueError, match="divisible"):
        encode_class_offset((0, 0), (0, 0), 0, radix=2, width=2, padded_height=3)
    with pytest.raises(ValueError, match="offset"):
        encode_class_offset((0,), (0,), -1, radix=2, width=1, padded_height=2)
    with pytest.raises(ValueError, match="slot"):
        decode_packet_address(PacketAddress(((0, 1),), 0, 2), radix=2,
                              width=1, padded_height=2)
    with pytest.raises(ValueError, match="pattern"):
        decode_packet_address(PacketAddress(((1, 0),), 0, 0), radix=2,
                              width=1, padded_height=2)


def test_global_checker_fails_closed_before_large_enumeration():
    result = verify_global_packet_bijection(radix=64, width=4, padded_height=16,
                                            max_addresses=1000)
    assert result["valid"] is False
    assert result["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert result["domain_size"] > result["max_addresses"]


@pytest.mark.parametrize("edges", [
    [],
    [(0, 0)],
    [(0, 0), (0, 0), (1, 1), (0, 1)],
    [(0, 1), (1, 0), (0, 1), (2, 0)],
])
def test_actual_sparse_builder_preserves_every_edge_occurrence(edges):
    packing = construct_implicit_packing(edges, r=2, a=1, max_work=100_000)
    audit = verify_implicit_packing_packet_addresses(
        packing, max_addresses=100_000, max_edge_work=100_000)
    assert audit["valid"] is True
    assert audit["status"] == "FINITE_GLOBAL_PACKET_BIJECTION_AND_BUILDER_CHECKED"
    assert audit["edge_occurrences_checked"] == len(edges)
    assert audit["real_slots_checked"] == len(edges)
    assert audit["edge_occurrence_multiplicity_preserved"] is True
    for edge_id in range(len(edges)):
        address = edge_occurrence_address(packing, edge_id)
        assert edge_occurrence_at_address(packing, address) == edge_id


def test_edge_occurrence_ids_are_not_collapsed_for_parallel_edges():
    packing = construct_implicit_packing([(5, 8), (5, 8), (5, 8)],
                                         r=2, a=1, max_work=100_000)
    addresses = [edge_occurrence_address(packing, eid) for eid in range(3)]
    assert len(set(addresses)) == 3
    assert [edge_occurrence_at_address(packing, address) for address in addresses] == [0, 1, 2]


def test_corrupted_class_table_fails_closed():
    packing = construct_implicit_packing([(0, 0), (0, 1)],
                                         r=2, a=1, max_work=100_000)
    corrupted = replace(packing, classes={})
    result = verify_implicit_packing_packet_addresses(
        corrupted, max_addresses=100_000, max_edge_work=100_000)
    assert result["valid"] is False
    assert result["status"] == "INVALID_PACKING"

