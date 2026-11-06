from copy import deepcopy
from dataclasses import replace
from itertools import product
from types import MappingProxyType

import pytest

from veritas.research.eth_packing_v26 import (
    PacketAddress, audit_global_packet_index, build_global_packet_index,
    construct_implicit_packing, construct_streaming_d3_packing,
    decode_global_packet_address, verify_streaming_d3_certificate,
)
from veritas.research.eth_packing_v26.expectation import PackingBudgetExceeded


@pytest.mark.parametrize("edges,r,a", [
    ([], 2, 1),
    ([(0, 0)], 2, 1),
    ([(0, 0), (0, 0), (1, 2), (0, 2), (1, 1)], 2, 2),
    ([(0, i) for i in range(12)] + [(0, 0), (0, 0)], 2, 1),
    ([(0, 1), (1, 0), (0, 1), (2, 0)], 3, 1),
])
@pytest.mark.parametrize("builder", ["coordinate", "whole_word"])
def test_index_and_full_padded_inverse_for_both_builders(edges, r, a, builder):
    if builder == "coordinate":
        packing = construct_implicit_packing(edges, r=r, a=a, max_work=3_000_000)
    else:
        packing = construct_streaming_d3_packing(edges, r=r, a=a,
                                                  max_work=3_000_000).packing
    index = build_global_packet_index(packing)
    result = audit_global_packet_index(packing, index=index, max_dense_slots=50_000)
    assert result["valid"] and result["full_padded_domain_checked"]
    assert result["occupied_slots"] == len(edges)
    assert result["label_selection_verified"] is False
    assert result["executable_refinement_proven"] is False
    addresses = [index.address_of(i) for i in range(len(edges))]
    assert len(set(addresses)) == len(edges)
    for edge_id, address in enumerate(addresses):
        assert index.edge_at(address) == edge_id
        assert decode_global_packet_address(packing, address) == edge_id


def test_valid_padding_decodes_to_none_and_invalid_slot_is_rejected():
    packing = construct_implicit_packing([(0, 0)], r=2, a=2)
    index = build_global_packet_index(packing)
    pattern = ((0, 0), (0, 0))
    assert index.edge_at(PacketAddress(pattern, 0, 1)) is None
    with pytest.raises(ValueError, match="slot"):
        index.edge_at(PacketAddress(pattern, 0, 4))
    with pytest.raises(ValueError, match="packet index"):
        index.edge_at(PacketAddress(pattern, 1, 0))
    with pytest.raises(ValueError, match="edge occurrence"):
        index.address_of(True)


def test_corrupted_rank_order_bucket_or_height_is_rejected():
    packing = construct_implicit_packing([(0, 0), (0, 0), (1, 1)], r=2, a=1)
    key = next(k for k, ids in packing.classes.items() if len(ids) >= 2)
    for corrupt in (
        {**packing.classes, key: tuple(reversed(packing.classes[key]))},
        {**packing.classes, key: packing.classes[key][:-1]},
        {**packing.classes, key: (True,) + packing.classes[key][1:]},
    ):
        damaged = replace(packing, classes=corrupt)
        with pytest.raises(ValueError):
            build_global_packet_index(damaged)
        assert audit_global_packet_index(damaged)["valid"] is False
    damaged = replace(packing, H=packing.H + packing.L)
    assert audit_global_packet_index(damaged)["status"] == "INVALID_PACKET_INDEX"


def test_same_count_address_substitution_and_reverse_map_tampering_fail():
    packing = construct_implicit_packing([(0, 0), (0, 0), (1, 1)], r=2, a=2)
    index = build_global_packet_index(packing)
    altered = replace(index, _addresses=(index._addresses[1],) + index._addresses[1:])
    assert audit_global_packet_index(packing, index=altered)["status"] == "INVALID_PACKET_INDEX"
    inverse = dict(index._occupied)
    first = index.address_of(0)
    inverse[first] = 1
    altered = replace(index, _occupied=MappingProxyType(inverse))
    assert audit_global_packet_index(packing, index=altered)["status"] == "INVALID_PACKET_INDEX"
    different = construct_implicit_packing([(4, 4), (4, 4), (5, 5)], r=2, a=2)
    assert audit_global_packet_index(different, index=index)["status"] == "INVALID_PACKET_INDEX"


def test_audit_detects_mutated_builder_lookup(monkeypatch):
    from veritas.research.eth_packing_v26.implicit import ImplicitPacking

    packing = construct_implicit_packing([(0, 0), (0, 1)], r=2, a=1)
    index = build_global_packet_index(packing)
    monkeypatch.setattr(ImplicitPacking, "packet_slot", lambda *args: None)
    assert audit_global_packet_index(packing, index=index)["status"] == "INVALID_PACKET_INDEX"


def test_budget_failures_do_not_report_a_complete_audit():
    packing = construct_implicit_packing([(0, 0), (0, 0)], r=2, a=2)
    with pytest.raises(PackingBudgetExceeded):
        build_global_packet_index(packing, max_edges=1)
    with pytest.raises(PackingBudgetExceeded):
        build_global_packet_index(packing, max_work=1)
    result = audit_global_packet_index(packing, max_dense_slots=0)
    assert result["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert result["valid"] is False and result["full_padded_domain_checked"] is False


@pytest.mark.parametrize("edges", [[], [(1, 1)]])
def test_forged_boolean_index_dimensions_and_identifiers_are_rejected(edges):
    packing = construct_implicit_packing(edges, r=2, a=1)
    index = build_global_packet_index(packing)
    for altered in (replace(index, width=True), replace(index, padded_height=False)):
        assert audit_global_packet_index(packing, index=altered)["valid"] is False
    if edges:
        altered = replace(index, _edges=((True, True),))
        assert audit_global_packet_index(packing, index=altered)["valid"] is False


def test_first_minimum_tie_and_order_mutations_are_rejected_by_rational_replay():
    built = construct_streaming_d3_packing([(0, 0)], r=2, a=2, max_work=100_000)
    assert built.certificate["steps"][0]["label"] == [0, 0]
    assert verify_streaming_d3_certificate(built.certificate)["valid"]
    altered = deepcopy(built.certificate)
    altered["steps"][0]["label"] = [1, 1]
    assert not verify_streaming_d3_certificate(altered)["valid"]
    altered = deepcopy(built.certificate)
    altered["steps"].reverse()
    assert not verify_streaming_d3_certificate(altered)["valid"]


def test_two_labelers_have_different_documented_order_semantics():
    edges = [(0, 0), (1, 1)]
    coordinate = construct_implicit_packing(edges, r=2, a=1)
    whole_word = construct_streaming_d3_packing(edges, r=2, a=1).packing
    assert dict(coordinate.rows) == {0: (0,), 1: (0,)}
    assert dict(whole_word.rows) == {0: (0,), 1: (1,)}
    assert audit_global_packet_index(coordinate)["valid"]
    assert audit_global_packet_index(whole_word)["valid"]


def test_exhaustive_small_edge_multisets_preserve_occurrence_ids():
    pairs = tuple(product(range(2), repeat=2))
    for m in range(4):
        for edges in product(pairs, repeat=m):
            packing = construct_implicit_packing(edges, r=2, a=1)
            result = audit_global_packet_index(packing, max_dense_slots=10_000)
            assert result["valid"], (edges, result)
