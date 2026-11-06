"""Bounded evidence decoding and recovery-grid replay fault tests."""

import base64
from dataclasses import replace
from types import SimpleNamespace
import zlib

import pytest

from test_cycle_transfer_fixture import three_crossing_matching
from veritas.research.parent_child_r98 import transfer_recovery_verify as verifier
from veritas.research.parent_child_r98.model import Budget, Refusal, canonical, decode
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY


def _encode(raw):
    return base64.b64encode(zlib.compress(raw, level=9)).decode("ascii")


def _budget(**changes):
    return Budget(replace(DEFAULT_SHRINKING_POLICY, **changes))


def test_bounded_point_decode_accepts_exactly_full_valid_stream():
    raw = b"x" * 1000
    decoded, compressed = verifier._bounded_point_decode(_encode(raw),
                                                          remaining_bytes=len(raw),
                                                          budget=_budget())
    assert decoded == raw and compressed == len(zlib.compress(raw, level=9))


@pytest.mark.parametrize("kind", ("base64", "truncated", "trailing", "second_stream"))
def test_bounded_point_decode_rejects_bad_or_multiple_streams(kind):
    wire = zlib.compress(b"certificate")
    if kind == "base64":
        encoded = "@invalid!"
    else:
        if kind == "truncated":
            wire = wire[:-1]
        elif kind == "trailing":
            wire += b"garbage"
        else:
            wire += zlib.compress(b"second")
        encoded = base64.b64encode(wire).decode("ascii")
    with pytest.raises(ValueError):
        verifier._bounded_point_decode(encoded, remaining_bytes=4096, budget=_budget())


def test_bounded_point_decode_refuses_decompression_bomb_and_work_exhaustion():
    encoded = _encode(b"x" * 100_000)
    with pytest.raises(Refusal, match="decompressed evidence"):
        verifier._bounded_point_decode(encoded, remaining_bytes=32, budget=_budget())
    with pytest.raises(Refusal, match="work/time"):
        verifier._bounded_point_decode(encoded, remaining_bytes=100_000,
                                       budget=_budget(max_work=1))


@pytest.fixture
def framing(monkeypatch):
    """Small framing double; real child semantics are tested by point replay tests."""
    parent, layout, _ = three_crossing_matching()
    point_specs = ((-1, (0, 0), 1416), (1, (1, 0), 1416))
    monkeypatch.setattr(verifier, "make_general_plan", lambda *a, **k:
                        SimpleNamespace(nodes=(1,), degree_bound=1))
    monkeypatch.setattr(verifier, "general_points", lambda *a, **k: iter(point_specs))
    def replay(parent, layout, raw, *, expected_point, budget):
        point = decode(raw)
        actual = (point["node"], tuple(point["zeta"]), point["precision"])
        if actual != expected_point:
            return {"status": "INVALID_CYCLE_TRANSFER_CERTIFICATE", "reason": "point binding"}
        return {"status": "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT",
                "result": ((point["value"], 0),)}
    monkeypatch.setattr(verifier, "verify_transfer_certificate", replay)
    def recover(parent, layout, rows, **kwargs):
        assert [r[3][0] for r in rows] == [3, 5]
        return ((7, 0),), SimpleNamespace(payload=b'{"fixture":"recovery"}')
    monkeypatch.setattr(verifier, "recover_general_grid", recover)
    monkeypatch.setattr(verifier, "contract_independent", lambda *a, **k: ((7, 0),))
    points = [_encode(canonical({"node": node, "zeta": list(zeta), "precision": p, "value": v}))
              for (node, zeta, p), v in zip(point_specs, (3, 5))]
    data = {"schema": verifier.SCHEMA, "parent_digest": parent.content_digest,
            "layout_digest": layout.content_digest, "point_certificates": points,
            "recovery_certificate": '{"fixture":"recovery"}', "result": [[7, 0]]}
    return parent, layout, data


def test_framing_replays_each_point_before_recovery(framing):
    parent, layout, data = framing
    result = verifier.verify_transfer_recovery_certificate(parent, layout, canonical(data))
    assert result["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY", result
    assert result["replayed_points"] == 2 and result["result"] == ((7, 0),)
    assert not result["oracle_supplied_answer"] and not result["source_qualified"]


def test_invalid_parent_and_layout_are_rejected_without_result(framing):
    parent, layout, data = framing
    for bad_parent, bad_layout in ((None, layout), (parent, None)):
        result = verifier.verify_transfer_recovery_certificate(
            bad_parent, bad_layout, canonical(data)
        )
        assert result["status"] == "INVALID_TRANSFER_RECOVERY_CERTIFICATE"
        assert "result" not in result


def test_cumulative_decompressed_point_evidence_cannot_exceed_policy(framing):
    parent, layout, data = framing
    points = []
    for encoded in data["point_certificates"]:
        item = decode(zlib.decompress(base64.b64decode(encoded)))
        item["padding"] = "x" * 800
        points.append(_encode(canonical(item)))
    data["point_certificates"] = points
    payload = canonical(data)
    assert len(payload) < 1000
    policy = replace(DEFAULT_SHRINKING_POLICY, max_certificate_bytes=1000)
    result = verifier.verify_transfer_recovery_certificate(parent, layout, payload, policy=policy)
    assert result["status"] == "INCONCLUSIVE_RESOURCE_LIMIT" and "result" not in result


def test_combined_point_and_recovery_evidence_cannot_exceed_policy(framing, monkeypatch):
    parent, layout, data = framing
    points = []
    for encoded in data["point_certificates"]:
        item = decode(zlib.decompress(base64.b64decode(encoded)))
        item["padding"] = "x" * 800
        points.append(_encode(canonical(item)))
    data["point_certificates"] = points
    recovery = canonical({"padding": "y" * 800})
    data["recovery_certificate"] = recovery.decode("ascii")
    monkeypatch.setattr(verifier, "recover_general_grid", lambda *a, **k:
                        (((7, 0),), SimpleNamespace(payload=recovery)))
    payload = canonical(data)
    assert len(payload) < 2000
    policy = replace(DEFAULT_SHRINKING_POLICY, max_certificate_bytes=2000)
    result = verifier.verify_transfer_recovery_certificate(parent, layout, payload, policy=policy)
    assert result["status"] == "INCONCLUSIVE_RESOURCE_LIMIT" and "result" not in result


@pytest.mark.parametrize("mutation", ("drop", "duplicate", "swap", "bad_recovery", "bad_result", "boolean_result"))
def test_framing_rejects_incomplete_substituted_or_altered_evidence(framing, mutation):
    parent, layout, data = framing
    if mutation == "drop":
        data["point_certificates"].pop()
    elif mutation == "duplicate":
        data["point_certificates"][1] = data["point_certificates"][0]
    elif mutation == "swap":
        data["point_certificates"].reverse()
    elif mutation == "bad_recovery":
        data["recovery_certificate"] = '{"fixture":"changed"}'
    elif mutation == "bad_result":
        data["result"][0][0] = 6
    else:
        data["result"][0][1] = False
    result = verifier.verify_transfer_recovery_certificate(parent, layout, canonical(data))
    assert not result["status"].startswith("PASS_") and "result" not in result
