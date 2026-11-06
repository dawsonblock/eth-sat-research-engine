from copy import deepcopy

import pytest

from veritas.research.eth_packing_v26.complete_bipartite import (
    MIN_ELIGIBLE_N,
    complete_bipartite_packet_address,
    construct_complete_bipartite_active_call,
)
from veritas.research.eth_packing_v26.complete_bipartite_check import (
    verify_complete_bipartite_certificate,
)
from veritas.research.eth_packing_v26.streaming import construct_streaming_d3_packing


def test_fixed_radix_packing_lemma_instance_checks_all_bounds():
    built = construct_complete_bipartite_active_call(MIN_ELIGIBLE_N)
    assert built["status"] == "READY_FOR_INDEPENDENT_CHECK"
    certificate = built["certificate"]
    checked = verify_complete_bipartite_certificate(certificate)
    assert checked["valid"]
    assert checked["status"] == "COMPRESSED_FIXED_RADIX_D3_INSTANCE_REPLAYED"
    assert checked["paper_radix_64"] is True
    assert checked["numeric_active_call_eligible"] is False
    assert checked["packing_lemma_inequalities_checked"] is True
    assert checked["source_schedule_checked"] is False
    assert checked["N_per_side"] == 33_554_432
    assert checked["M"] == 1_125_899_906_842_624
    assert checked["edges_enumerated"] == 0
    assert checked["directed_classes_checked_arithmetically"] == 4096
    assert checked["child_wire_strictly_below_M_over_8"] is True
    assert checked["universal_packing_lemma_proven"] is False
    assert checked["theorem_mode_enabled"] is False


def test_precondition_failure_returns_no_compressed_certificate():
    built = construct_complete_bipartite_active_call(MIN_ELIGIBLE_N - 64)
    assert built["status"] == "INCONCLUSIVE_D3_PRECONDITIONS"
    assert built["certificate"] is None
    assert not all(built["preconditions"].values())


def test_compressed_packet_address_is_injective_on_exhaustive_small_graph():
    n = 64
    addresses = set()
    for i in range(n):
        for j in range(n):
            address = complete_bipartite_packet_address(n, i, j)
            key = (tuple(address["unordered_pair"]),
                   address["packet_index"], address["slot"])
            assert key not in addresses
            addresses.add(key)
    assert len(addresses) == n*n


def test_periodic_label_rule_matches_generic_conditional_expectation_on_small_Knn():
    n = 4
    edges = [(i, j) for i in range(n) for j in range(n)]
    packed = construct_streaming_d3_packing(
        edges, r=64, a=1, max_work=1_000_000,
        max_candidate_evaluations=100_000,
    ).packing
    assert packed.rows == {i: (i,) for i in range(n)}
    assert packed.cols == {j: (j,) for j in range(n)}


def test_independent_checker_rejects_arithmetic_and_policy_mutations():
    original = construct_complete_bipartite_active_call(MIN_ELIGIBLE_N)["certificate"]
    assert verify_complete_bipartite_certificate(original)["valid"]
    mutations = (
        lambda c: c["parameters"].__setitem__("M", c["parameters"]["M"] - 1),
        lambda c: c["labeling"].__setitem__("row_rule", "all_zero"),
        lambda c: c["packetization"].__setitem__("uniform_padded_height", 0),
        lambda c: c["loads"].__setitem__("child_wire_count", 0),
        lambda c: c["qualification"].__setitem__("theorem_mode_enabled", True),
        lambda c: c["resource_ledger"].__setitem__("edges_materialized", True),
    )
    for mutate in mutations:
        altered = deepcopy(original)
        mutate(altered)
        assert not verify_complete_bipartite_certificate(altered)["valid"]


def test_legacy_overclaim_is_replayed_without_promoting_it():
    legacy = construct_complete_bipartite_active_call(MIN_ELIGIBLE_N)["certificate"]
    legacy["schema"] = "VERITAS_ETH_D3_KNN_COMPRESSED_V1"
    legacy["claim"] = "COMPRESSED_COMPLETE_BIPARTITE_D3_ACTIVE_CALL"
    legacy["qualification"]["numeric_active_call_eligible"] = True
    checked = verify_complete_bipartite_certificate(legacy)
    assert checked["valid"]
    assert checked["legacy_active_call_claim_discarded"] is True
    assert checked["numeric_active_call_eligible"] is False


def test_new_schema_rejects_active_call_overclaim():
    certificate = construct_complete_bipartite_active_call(MIN_ELIGIBLE_N)["certificate"]
    certificate["qualification"]["numeric_active_call_eligible"] = True
    assert not verify_complete_bipartite_certificate(certificate)["valid"]


@pytest.mark.parametrize("args", [
    (64, -1, 0),
    (64, 0, 64),
    (63, 0, 0),
])
def test_packet_address_rejects_invalid_endpoints(args):
    with pytest.raises(ValueError):
        complete_bipartite_packet_address(*args)
