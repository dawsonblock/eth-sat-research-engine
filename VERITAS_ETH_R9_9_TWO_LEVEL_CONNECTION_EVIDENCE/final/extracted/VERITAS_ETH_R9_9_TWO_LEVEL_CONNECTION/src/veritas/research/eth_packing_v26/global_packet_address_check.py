"""Independent finite audit of edge occurrence and padded packet positions.

The expected class ranks are rebuilt from the input edge order. The dense
reference decoder is separate from the production codec. The audit checks
the supplied labels; it does not prove how the constructor selected them.
"""
from __future__ import annotations

from collections.abc import Mapping
from itertools import product

from .expectation import PackingBudgetExceeded, validate_edges
from .global_packet_address import GlobalPacketIndex, build_global_packet_index
from .implicit import ImplicitPacking
from .packet_bijection import PacketAddress
from .packet_bijection_check import _reference_decode


def _audit(packing, index, max_edges, max_dense_slots, max_work):
    if not isinstance(packing, ImplicitPacking):
        raise ValueError("ImplicitPacking required")
    if type(max_dense_slots) is not int or not 0 <= max_dense_slots <= 1_000_000:
        raise ValueError("invalid dense slot cap")
    if type(max_edges) is not int or not 0 <= max_edges <= 1_000_000:
        raise ValueError("invalid edge cap")
    if type(max_work) is not int or max_work < 0:
        raise ValueError("invalid audit work cap")
    if not isinstance(packing.edges, (tuple, list)) or len(packing.edges) > max_edges:
        raise PackingBudgetExceeded("edge cap exceeded")
    if (type(packing.r) is not int or not 2 <= packing.r <= 64 or
            type(packing.a) is not int or not 1 <= packing.a <= 64):
        raise ValueError("invalid dimensions")
    if not all(isinstance(x, Mapping) for x in (packing.rows, packing.cols, packing.classes)):
        raise ValueError("invalid label or class mapping")
    if any(len(x) > len(packing.edges) for x in (packing.rows, packing.cols, packing.classes)):
        raise ValueError("extra vertices or classes")
    if len(packing.edges) * (2 * packing.a + 5) > max_work:
        raise PackingBudgetExceeded("edge audit work cap exceeded")
    if index is None:
        index = build_global_packet_index(packing, max_edges=max_edges, max_work=max_work)
    if not isinstance(index, GlobalPacketIndex):
        raise ValueError("GlobalPacketIndex required")
    if any(type(x) is not int for x in (index.radix, index.width, index.padded_height)):
        raise ValueError("invalid index dimensions")
    if (not isinstance(index._edges, tuple) or
            any(not isinstance(e, tuple) or len(e) != 2 or
                any(type(v) is not int for v in e) for e in index._edges) or
            not isinstance(index._addresses, tuple) or
            not isinstance(index._occupied, Mapping)):
        raise ValueError("invalid immutable index representation")

    edges = validate_edges(packing.edges)
    m, r, a = len(edges), packing.r, packing.a
    if set(packing.rows) != {u for u, _ in edges} or set(packing.cols) != {v for _, v in edges}:
        raise ValueError("vertex label domain mismatch")
    for labels in (packing.rows, packing.cols):
        if any(not isinstance(word, (list, tuple)) or len(word) != a
               for word in labels.values()):
            raise ValueError("malformed or oversized label word")
    rows = {u: tuple(word) for u, word in packing.rows.items()}
    columns = {v: tuple(word) for v, word in packing.cols.items()}
    for labels in (rows, columns):
        for vertex, word in labels.items():
            if (type(vertex) is not int or vertex < 0 or vertex.bit_length() > 4096 or
                    len(word) != a or
                    any(type(x) is not int or not 0 <= x < r for x in word)):
                raise ValueError("invalid tagged vertex label")

    classes = {}
    for edge_id, (u, v) in enumerate(edges):
        classes.setdefault((rows[u], columns[v]), []).append(edge_id)
    expected_classes = {key: tuple(ids) for key, ids in classes.items()}
    if len(packing.classes) > m:
        raise ValueError("too many class buckets")
    actual_classes = {}
    count = 0
    for key, ids in packing.classes.items():
        if not isinstance(ids, (tuple, list)) or len(ids) > m:
            raise ValueError("malformed or oversized class bucket")
        count += len(ids)
        if count > m or any(type(i) is not int for i in ids):
            raise ValueError("invalid class bucket entries")
        actual_classes[key] = tuple(ids)
    if actual_classes != expected_classes:
        raise ValueError("class bucket order or content mismatch")
    width = 1 << a
    max_load = max((len(ids) for ids in expected_classes.values()), default=0)
    height = ((max_load + width - 1) // width) * width
    if type(packing.H) is not int or packing.H != height:
        raise ValueError("padded height mismatch")
    if (index.radix != r or index.width != a or index.padded_height != height or
            index._edges != edges or index._rows != tuple(sorted(rows.items())) or
            index._columns != tuple(sorted(columns.items())) or
            len(index._addresses) != m or
            any(type(v) is not int or any(type(x) is not int for x in word)
                for labels in (index._rows, index._columns) for v, word in labels)):
        raise ValueError("index does not match the source packing")

    dense_size = (r ** (2 * a)) * height
    estimated_work = m * (2 * a + 5) + dense_size * (a + 1)
    if dense_size > max_dense_slots or estimated_work > max_work:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT",
                "reason": "dense address or work cap exceeded",
                "padded_slots": dense_size, "max_dense_slots": max_dense_slots,
                "estimated_work": estimated_work, "max_work": max_work,
                "full_padded_domain_checked": False}

    # Construct the expected addresses directly from the original edge list,
    # independently of the production encoder and its class buckets.
    ranks, expected = {}, {}
    for edge_id, (u, v) in enumerate(edges):
        row, col = rows[u], columns[v]
        cls = (row, col)
        rank = ranks.get(cls, 0)
        ranks[cls] = rank + 1
        pattern = tuple((min(x, y), max(x, y)) for x, y in zip(row, col))
        equal = [i for i, (low, high) in enumerate(pattern) if low == high]
        packet, copy = divmod(rank, 1 << len(equal))
        bits = [int(row[d] > col[d]) for d in range(a)]
        for copy_bit, coordinate in enumerate(equal):
            bits[coordinate] = (copy // (2 ** copy_bit)) % 2
        slot = sum(bit * (2 ** d) for d, bit in enumerate(bits))
        address = PacketAddress(pattern, packet, slot)
        if address in expected:
            raise ValueError("independent reference detected an address collision")
        expected[address] = edge_id
        if (index.address_of(edge_id) != address or index.edge_at(address) != edge_id or
                packing.packet_slot(pattern, packet, slot) != edge_id):
            raise ValueError("edge address or builder slot mismatch")
    if (index.occupied_count != m or any(type(i) is not int for i in index._occupied.values()) or
            dict(index._occupied) != expected):
        raise ValueError("occupied-slot inverse mismatch")

    # Enumerate the entire padded codomain only after the explicit cap check.
    checked = occupied = 0
    if height:
        choices = tuple((low, high) for low in range(r) for high in range(low, r))
        for pattern in product(choices, repeat=a):
            equal_count = sum(low == high for low, high in pattern)
            for packet in range(height // (1 << equal_count)):
                for slot in range(width):
                    address = PacketAddress(tuple(pattern), packet, slot)
                    row, col, offset = _reference_decode(
                        tuple(pattern), packet, slot, radix=r, width=a, padded_height=height)
                    bucket = expected_classes.get((row, col), ())
                    reference = bucket[offset] if offset < len(bucket) else None
                    if (index.edge_at(address) != reference or
                            packing.packet_slot(pattern, packet, slot) != reference):
                        raise ValueError("padded slot inverse mismatch")
                    checked += 1
                    occupied += reference is not None
    if checked != dense_size or occupied != m:
        raise ValueError("padded address or occupied edge count mismatch")
    return {"valid": True, "status": "FINITE_GLOBAL_PACKET_INDEX_AUDITED",
            "edge_occurrences": m, "occupied_slots": occupied,
            "padded_slots_checked": checked, "padding_slots": checked - occupied,
            "full_padded_domain_checked": True,
            "label_selection_verified": False,
            "executable_refinement_proven": False,
            "universal_theorem_proven": False}


def audit_global_packet_index(packing, *, index=None, max_edges=100_000,
                              max_dense_slots=50_000, max_work=5_000_000):
    try:
        return _audit(packing, index, max_edges, max_dense_slots, max_work)
    except (PackingBudgetExceeded, MemoryError, RecursionError) as exc:
        return {"valid": False, "status": "INCONCLUSIVE_RESOURCE_LIMIT",
                "reason": str(exc), "full_padded_domain_checked": False}
    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        return {"valid": False, "status": "INVALID_PACKET_INDEX",
                "reason": str(exc), "full_padded_domain_checked": False}
