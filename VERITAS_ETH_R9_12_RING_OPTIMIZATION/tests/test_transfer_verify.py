"""Adversarial replay of actual finite transfer child certificates."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from test_cycle_transfer_fixture import three_crossing_matching
from veritas.research.parent_child_r98.cycle_transfer import evaluate_cycle_transfer
from veritas.research.parent_child_r98.model import canonical, decode, digest
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.transfer_verify import verify_transfer_certificate


@pytest.fixture(scope="module")
def example():
    parent, layout, _ = three_crossing_matching()
    result = evaluate_cycle_transfer(parent, layout, 1, (1, 0))
    assert result["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", result
    return parent, layout, result["certificate"], result["result"]


def _verify(example, data, **kwargs):
    parent, layout, _, _ = example
    return verify_transfer_certificate(parent, layout, canonical(data), **kwargs)


def _alter_child(data, mutate, *, update_hash=True):
    group = next(g for g in data["groups"] if g["mode_indices"] and g["children"])
    obj = decode(group["children"][0].encode("ascii"))
    mutate(obj["child"])
    if update_hash:
        obj["sha256"] = digest(obj["child"])
    group["children"][0] = canonical(obj).decode("ascii")


def test_fresh_certificate_replays_every_child_state_and_original_parent(example):
    parent, layout, payload, result = example
    checked = verify_transfer_certificate(parent, layout, payload,
                                          expected_point=(1, (1, 0), 1416))
    assert checked["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", checked
    assert checked["result"] == result
    assert checked["mode_count"] == 3 and checked["groups"] == 64
    assert checked["local_child_states_checked"] == 3 * 4 + 61
    assert checked["parent_point_check"] == "INDEPENDENT_HALF_EDGE_ELIMINATION"
    assert checked["source_qualified"] is False


@pytest.mark.parametrize("mutation", ("dropped_group", "dropped_child", "changed_value",
                                       "source_target", "changed_zeta", "changed_precision",
                                       "boolean_mode_field", "boolean_mode_index"))
def test_incomplete_or_altered_transfer_evidence_is_rejected(example, mutation):
    data = decode(example[2])
    if mutation == "dropped_group":
        data["groups"].pop()
    elif mutation == "dropped_child":
        data["groups"][0]["children"].pop()
    elif mutation == "changed_value":
        data["groups"][0]["values"][0][0][0] ^= 1
    elif mutation == "source_target":
        mode = data["modes"][0]
        mode[2], mode[3] = mode[3], mode[2]
    elif mutation == "changed_zeta":
        data["zeta"] = [0, 0]
    elif mutation == "changed_precision":
        data["precision"] += 1
    elif mutation == "boolean_mode_field":
        mode = data["modes"][0]
        field = next(i for i, value in enumerate(mode) if value in (0, 1))
        mode[field] = bool(mode[field])
    elif mutation == "boolean_mode_index":
        group = next(g for g in data["groups"] if 0 in g["mode_indices"])
        group["mode_indices"][group["mode_indices"].index(0)] = False
    report = _verify(example, data)
    assert not report["status"].startswith("PASS_"), report
    assert "result" not in report


def test_copied_child_digest_rejects_corrupted_half_edge(example):
    data = decode(example[2])
    _alter_child(data, lambda child: child["edge_map"][0].__setitem__(5, 1), update_hash=False)
    report = _verify(example, data)
    assert not report["status"].startswith("PASS_") and "result" not in report


def test_rehashed_child_with_wrong_port_owner_is_still_rejected(example):
    data = decode(example[2])
    _alter_child(data, lambda child: child["edge_map"][0].__setitem__(5, 1))
    report = _verify(example, data)
    assert "half-edge" in report["reason"] and "result" not in report


def test_rehashed_child_with_changed_original_creation_precision_is_rejected(example):
    data = decode(example[2])
    def mutate(child):
        tensor = next(v["tensor"] for v in child["vertices"] if v["side"] == "row")
        tensor["creation_precision"] -= 1
        desc = json.loads(tensor["description"])
        desc["creation_precision"] -= 1
        tensor["description"] = json.dumps(desc, sort_keys=True, separators=(",", ":"))
    _alter_child(data, mutate)
    report = _verify(example, data)
    assert not report["status"].startswith("PASS_") and "result" not in report


def test_altered_beta_with_rehashed_child_cannot_change_local_state(example):
    data = decode(example[2])
    _alter_child(data, lambda child: child["beta"]["values"].__setitem__(0, 2))
    report = _verify(example, data)
    assert "beta" in report["reason"] and "result" not in report


def test_same_count_substitution_of_local_states_is_rejected(example):
    data = decode(example[2])
    group = next(g for g in data["groups"] if len(g["values"]) == 4)
    group["values"][0], group["values"][1] = group["values"][1], group["values"][0]
    group["children"][0], group["children"][1] = group["children"][1], group["children"][0]
    report = _verify(example, data)
    assert "beta" in report["reason"] and "result" not in report


def test_rehashed_child_with_changed_packet_coefficient_is_rejected(example):
    data = decode(example[2])
    def mutate(child):
        for vertex in child["vertices"]:
            tensor = vertex["tensor"]
            recipe = decode(tensor["description"].encode("ascii"))
            if recipe["kind"] == "packet" and recipe["data"][3]:
                recipe["data"][3][0][1][0][0][0] = 0
                tensor["description"] = canonical(recipe).decode("ascii")
                return
        raise AssertionError("fixture requires an actual targeted mode")
    _alter_child(data, mutate)
    report = _verify(example, data)
    assert "packet assignment, coefficient" in report["reason"] and "result" not in report


def test_expected_point_binds_the_consumer_and_budget_refuses_without_result(example):
    parent, layout, payload, _ = example
    bad = verify_transfer_certificate(parent, layout, payload,
                                      expected_point=(-1, (1, 0), 1416))
    assert "expected interpolation point" in bad["reason"] and "result" not in bad
    boolean = verify_transfer_certificate(parent, layout, payload,
                                          expected_point=(1, (True, 0), 1416))
    assert "expected interpolation point" in boolean["reason"] and "result" not in boolean
    policy = replace(DEFAULT_SHRINKING_POLICY, max_certificate_bytes=len(payload)-1)
    refused = verify_transfer_certificate(parent, layout, payload, policy=policy)
    assert refused["status"] == "INCONCLUSIVE_RESOURCE_LIMIT" and "result" not in refused
