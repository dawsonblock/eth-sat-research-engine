"""Independent bounded checker for the global padded-slot/packet map.

The reference side enumerates every directed class and padded offset, while
the target side separately enumerates canonical unordered patterns, packet
indices, and physical slot words. This is deliberately finite and resource
capped; it is not a proof for arbitrary theorem parameters.
"""
from __future__ import annotations

from itertools import product

from .packet_bijection import encode_class_offset


def _key(address):
    return (tuple(tuple(pair) for pair in address.pattern), address.packet, address.slot)


def _reference_decode(pattern, packet, slot, *, radix, width, padded_height):
    """Decode by direct bit partition, independently of production decoder."""
    L = 1 << width
    if len(pattern) != width or not 0 <= slot < L or packet < 0:
        raise ValueError("invalid reference address")
    row, column, equal_positions = [], [], []
    for coordinate, pair in enumerate(pattern):
        if (not isinstance(pair, tuple) or len(pair) != 2 or
                type(pair[0]) is not int or type(pair[1]) is not int or
                not 0 <= pair[0] <= pair[1] < radix):
            raise ValueError("invalid reference pattern")
        low, high = pair
        bit = (slot >> coordinate) & 1
        if low < high:
            row.append(high if bit else low)
            column.append(low if bit else high)
        else:
            row.append(low)
            column.append(low)
            equal_positions.append(coordinate)
    copies = 1 << len(equal_positions)
    if padded_height % copies or packet >= padded_height // copies:
        raise ValueError("packet outside reference pattern block")
    copy_index = 0
    for rank, coordinate in enumerate(equal_positions):
        copy_index += ((slot >> coordinate) & 1) * (1 << rank)
    offset = packet * copies + copy_index
    if offset >= padded_height:
        raise ValueError("decoded offset outside reference class")
    return tuple(row), tuple(column), offset


def verify_global_packet_bijection(*, radix: int, width: int, padded_height: int,
                                   max_addresses: int = 250_000):
    """Exhaustively check the class-offset/address bijection within a cap.

    `padded_height=0` denotes the empty slot domain. The function returns
    `INCONCLUSIVE_RESOURCE_LIMIT` before enumeration if the finite domain is
    larger than `max_addresses`.
    """
    if type(radix) is not int or radix < 1:
        return {"valid": False, "status": "INVALID_INPUT", "reason": "radix"}
    if type(width) is not int or width < 0:
        return {"valid": False, "status": "INVALID_INPUT", "reason": "width"}
    if type(padded_height) is not int or padded_height < 0:
        return {"valid": False, "status": "INVALID_INPUT", "reason": "padded_height"}
    if type(max_addresses) is not int or max_addresses < 0:
        return {"valid": False, "status": "INVALID_INPUT", "reason": "max_addresses"}
    L = 1 << width
    if padded_height % L:
        return {"valid": False, "status": "INVALID_INPUT", "reason": "height_not_multiple_of_L"}

    directed_class_count = radix ** (2 * width)
    domain_size = directed_class_count * padded_height
    if domain_size > max_addresses:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT",
                "domain_size": domain_size, "max_addresses": max_addresses}
    if padded_height == 0:
        return {"valid": True, "status": "FINITE_GLOBAL_PACKET_BIJECTION_CHECKED",
                "directed_classes": directed_class_count, "padded_slots": 0,
                "packet_addresses": 0, "roundtrips": 0,
                "independent_set_equality": True}

    words = tuple(product(range(radix), repeat=width))
    seen = {}
    roundtrips = 0
    for row in words:
        for column in words:
            for offset in range(padded_height):
                address = encode_class_offset(
                    row, column, offset, radix=radix, width=width,
                    padded_height=padded_height)
                key = _key(address)
                if key in seen:
                    return {"valid": False, "status": "INVALID_BIJECTION",
                            "reason": "address_collision", "address": key}
                decoded = _reference_decode(*key, radix=radix, width=width,
                                            padded_height=padded_height)
                if decoded != (tuple(row), tuple(column), offset):
                    return {"valid": False, "status": "INVALID_BIJECTION",
                            "reason": "reference_inverse_mismatch", "address": key}
                seen[key] = (tuple(row), tuple(column), offset)
                roundtrips += 1

    # Independently enumerate every legal packet address from unordered
    # coordinate pairs, packet-block lengths, and all slot bit words.
    pair_choices = tuple((low, high) for low in range(radix)
                         for high in range(low, radix))
    expected = set()
    for pattern in product(pair_choices, repeat=width):
        equal_count = sum(low == high for low, high in pattern)
        copies_per_class_per_packet = 1 << equal_count
        if padded_height % copies_per_class_per_packet:
            return {"valid": False, "status": "INVALID_BIJECTION",
                    "reason": "pattern_copy_divisibility"}
        for packet in range(padded_height // copies_per_class_per_packet):
            for slot in range(L):
                expected.add((tuple(pattern), packet, slot))
    if set(seen) != expected:
        return {"valid": False, "status": "INVALID_BIJECTION",
                "reason": "address_set_mismatch",
                "emitted_addresses": len(seen), "expected_addresses": len(expected)}
    if len(expected) != domain_size:
        return {"valid": False, "status": "INVALID_BIJECTION",
                "reason": "cardinality_mismatch",
                "domain_size": domain_size, "address_size": len(expected)}
    return {"valid": True, "status": "FINITE_GLOBAL_PACKET_BIJECTION_CHECKED",
            "directed_classes": directed_class_count,
            "padded_slots": domain_size, "packet_addresses": len(expected),
            "roundtrips": roundtrips, "independent_set_equality": True}


def _verify_implicit_packing_packet_addresses(packing, *, max_addresses: int,
                                              max_edge_work: int):
    """Check the finite global bijection and every real edge in a packing.

    Compares each edge occurrence address against the emitted sparse packet
    view. Parallel/repeated input edges are distinguished by their occurrence
    IDs. Returns inconclusive before exhaustive work exceeds either cap.
    """
    from .implicit import sparse_active_packet_view

    base = verify_global_packet_bijection(radix=packing.r, width=packing.a,
                                          padded_height=packing.H,
                                          max_addresses=max_addresses)
    if not base.get("valid"):
        return base
    M = len(packing.edges)
    if type(max_edge_work) is not int or max_edge_work < 0:
        return {"valid": False, "status": "INVALID_INPUT", "reason": "max_edge_work"}
    if M > max_edge_work:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT",
                "edge_count": M, "max_edge_work": max_edge_work}

    # Import production encoder only as the target under test; derive expected
    # edge addresses by a separate reference construction below.
    from .packet_bijection import edge_occurrence_address
    expected = {}
    offsets = {}
    for (row, column), edge_ids in packing.classes.items():
        for offset, edge_id in enumerate(edge_ids):
            if edge_id in offsets:
                return {"valid": False, "status": "INVALID_BIJECTION",
                        "reason": "edge_occurrence_in_multiple_classes", "edge_id": edge_id}
            offsets[edge_id] = (tuple(row), tuple(column), offset)
    for packet in sparse_active_packet_view(packing, max_work=max_edge_work):
        pairs = tuple(tuple(pair) for pair in packet["symbol_pairs"])
        index = packet["index"]
        for slot, edge_id in packet["occupied_slots"]:
            key = (pairs, index, slot)
            if key in expected:
                return {"valid": False, "status": "INVALID_BIJECTION",
                        "reason": "duplicate_real_packet_slot", "address": key}
            expected[key] = edge_id

    for edge_id, (row_vertex, column_vertex) in enumerate(packing.edges):
        row = tuple(packing.rows[row_vertex])
        column = tuple(packing.cols[column_vertex])
        if edge_id not in offsets:
            return {"valid": False, "status": "INVALID_BIJECTION",
                    "reason": "edge_missing_from_class", "edge_id": edge_id}
        bucket_row, bucket_column, offset = offsets[edge_id]
        if (row, column) != (bucket_row, bucket_column):
            return {"valid": False, "status": "INVALID_BIJECTION",
                    "reason": "edge_wrong_class", "edge_id": edge_id}

        pattern = tuple((min(x, y), max(x, y)) for x, y in zip(row, column))
        equal_positions = tuple(i for i, (x, y) in enumerate(pattern) if x == y)
        copies = 1 << len(equal_positions)
        packet_index, copy_index = divmod(offset, copies)
        slot = 0
        equal_rank = 0
        for coordinate, ((low, high), x, y) in enumerate(zip(pattern, row, column)):
            if low != high:
                bit = int(x > y)
            else:
                bit = (copy_index >> equal_rank) & 1
                equal_rank += 1
            slot |= bit << coordinate
        expected_address = (pattern, packet_index, slot)
        actual_address = edge_occurrence_address(packing, edge_id)
        if _key(actual_address) != expected_address:
            return {"valid": False, "status": "INVALID_BIJECTION",
                    "reason": "production_encoder_mismatch", "edge_id": edge_id}
        if expected.get(expected_address) != edge_id:
            return {"valid": False, "status": "INVALID_BIJECTION",
                    "reason": "packet_builder_mismatch", "edge_id": edge_id}

    return {**base, "valid": True, "status": "FINITE_GLOBAL_PACKET_BIJECTION_AND_BUILDER_CHECKED",
            "edge_occurrences_checked": M,
            "real_slots_checked": len(expected),
            "edge_occurrence_multiplicity_preserved": len(set(expected.values())) == M}


def verify_implicit_packing_packet_addresses(packing, *, max_addresses: int = 250_000,
                                              max_edge_work: int = 1_000_000):
    """Fail-closed public wrapper for malformed or budget-limited packings."""
    from .expectation import PackingBudgetExceeded

    try:
        return _verify_implicit_packing_packet_addresses(
            packing, max_addresses=max_addresses, max_edge_work=max_edge_work)
    except PackingBudgetExceeded:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT"}
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        return {"valid": False, "status": "INVALID_PACKING", "reason": str(exc)}

