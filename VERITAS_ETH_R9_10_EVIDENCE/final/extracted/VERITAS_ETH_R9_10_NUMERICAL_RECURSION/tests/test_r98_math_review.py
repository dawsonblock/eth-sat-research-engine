"""Mathematical regressions found while reviewing the sealed R9.8 release."""

from dataclasses import replace
from itertools import product

import pytest

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing,
    implicit_sparse_mode_source,
)
from veritas.research.eth_packing_v26.packet_bijection import encode_class_offset
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.parent_child_r98 import (
    Budget,
    ExponentTuple,
    construct_children,
    from_described,
    verify_children,
)
from veritas.research.parent_child_r98.independent import parent_point
from veritas.research.parent_child_r98.model import PacketLayout, canonical
from veritas.research.parent_child_r98.modes import build_modes
from veritas.research.parent_child_r98.packing import audit_layout, construct_layout
from veritas.research.paper_verification.packing_checker import check_packing
from veritas.research.tensor import Factor, TensorNetwork


def matching_blocks(sizes):
    vertices, start = [], 0
    for index, count in enumerate(sizes):
        ports = tuple(range(start, start + count))
        start += count
        # Signed, nonconstant factors, so the arithmetic check is substantive.
        vertices.extend(
            (
                Factor(ports, tuple(j - 2 for j in range(1 << count)), f"row:{index}"),
                Factor(
                    ports, tuple(3 * j + 1 for j in range(1 << count)), f"col:{index}"
                ),
            )
        )
    return from_described(
        describe_integer_network(
            TensorNetwork(start, tuple(vertices)),
            creation_precision=5,
            defining_polynomial=first_irreducible(5),
        ),
        root_s=16,
        precision=5,
    )


def test_real_six_edge_canonical_packing_accepts_second_pattern_packet():
    parent = matching_blocks((3, 3))
    layout = construct_layout(parent, budget=Budget())
    src = layout.source
    assert src["H_pad"] == src["L"] == 4
    assert any(p["index"] == 1 for p in src["packets"])
    assert check_packing(src, parent.bipartite_edges())["occupied_packets"] == 3
    checked = audit_layout(parent, layout)
    assert checked["exact_edge_coverage"]
    assert not checked["source_eligible"]
    assert not checked["group_load_bound_met"]

    # A full point at zeta=0 has no cross modes. This validates the repaired
    # topology all the way through actual children and the half-edge oracle.
    budget = Budget()
    modes = build_modes(parent, layout, -1, (0,) * 5, budget=budget)
    assert modes.certificate["modes"] == []
    beta = ExponentTuple(modes.content_digest, ())
    children = construct_children(parent, layout, modes, beta, budget=budget)
    report = verify_children(parent, layout, modes, beta, children, budget=budget)
    ring = JetRing(
        ExtensionRing(modes.certificate["precision"], parent.defining_polynomial), 1
    )
    value = ring.one
    for child_value in report["values"]:
        value = ring.mul(value, child_value)
    assert value == parent_point(parent, layout, modes, budget=budget)
    assert report["child_count"] == 64
    assert not report["all_source_shrink"]


@pytest.mark.parametrize(
    "a,column", [(a, column) for a in (1, 2, 3) for column in product((0, 1), repeat=a)]
)
def test_pattern_capacity_depends_on_equal_coordinates(a, column):
    parent = matching_blocks((1,))
    original = implicit_sparse_mode_source(
        construct_implicit_packing(parent.bipartite_edges(), r=64, a=a)
    )
    row, height = (0,) * a, 2 * (1 << a)
    src = dict(original)
    src["H_pad"] = height
    src["row_labels"] = {"0": list(row)}
    src["column_labels"] = {"0": list(column)}
    copies = 1 << sum(x == y for x, y in zip(row, column))
    # Every padded offset is a legal packet/slot pair, including offsets whose
    # packet index exceeds the old, incorrect H/L threshold.
    for offset in range(height):
        address = encode_class_offset(
            row, column, offset, radix=64, width=a, padded_height=height
        )
        src["packets"] = [
            {
                "symbol_pairs": [list(x) for x in address.pattern],
                "index": address.packet,
                "occupied_slots": [[address.slot, 0]],
            }
        ]
        layout = PacketLayout(parent.content_digest, a, 1, canonical(src))
        assert audit_layout(parent, layout)["exact_edge_coverage"]
        assert address.packet < height // copies
    src["packets"][0]["index"] = height // copies
    with pytest.raises(ValueError, match="packet index exceeds capacity"):
        audit_layout(parent, replace(layout, source_bytes=canonical(src)))
