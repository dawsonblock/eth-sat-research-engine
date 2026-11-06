"""Complete-grid recovery for an independently audited three-mode cycle.

The graph is a matching; its deliberately regrouped three crossing modes form
a genuine cycle, with 19 additional nonempty isolated groups. Every point is
compared to an independent closed-form calculation over a separately written
integer-polynomial reference ring. This does not claim a source-regime result
or a connected 22-edge input network.
"""

import base64
from copy import deepcopy
from dataclasses import replace
import zlib

import pytest

from test_cycle_transfer_fixture import three_crossing_matching
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic
from veritas.research.parent_child_r98.model import canonical, decode
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY


@pytest.fixture(scope="module")
def complete_cycle_grid():
    from veritas.research.parent_child_r98.cycle_transfer_recovery import contract_cycle_transfer

    parent, layout, _ = three_crossing_matching(extension_degree=7, precision=128)
    # The exact call cap also detects double counting or silent omitted states.
    policy = replace(DEFAULT_SHRINKING_POLICY, max_certificate_bytes=100_000_000,
                     max_calls=9899)
    report = contract_cycle_transfer(parent, layout, policy=policy, max_points=256)
    assert report["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY", report
    return parent, layout, policy, report


def independent_matching_point(parent, node, zeta, precision):
    """For each edge sum R(y)C(x)l_y(Wx) = 7+10W, then raise to 22."""
    ar = ReferenceArithmetic(precision, parent.defining_polynomial, 1, 10_000_000,
                             max_precision_bits=65536)
    z = (tuple(zeta),)
    if node == 1:
        # W(1+4z) = -4z(3+4z)(1+2z).
        w = ar.mul(ar.scalar(-4), ar.mul(z, ar.mul(
            ar.add(ar.scalar(3), ar.mul(ar.scalar(4), z)),
            ar.add(ar.scalar(1), ar.mul(ar.scalar(2), z)))))
    else:
        # W(-1+4z) = 4z(1+4z)(1-2z).
        w = ar.mul(ar.scalar(4), ar.mul(z, ar.mul(
            ar.add(ar.scalar(1), ar.mul(ar.scalar(4), z)),
            ar.add(ar.scalar(1), ar.mul(ar.scalar(-2), z)))))
    return ar.power(ar.add(ar.scalar(7), ar.mul(ar.scalar(10), w)), 22)


def unpack_point(encoded):
    return decode(zlib.decompress(base64.b64decode(encoded, validate=True)))


def test_complete_cycle_grid_recomputes_points_and_recovers_exact_parent(complete_cycle_grid):
    from veritas.research.parent_child_r98.cycle_transfer_recovery import verify_transfer_recovery_certificate

    parent, layout, policy, report = complete_cycle_grid
    assert report["result"] == ((17**22, 0, 0, 0, 0, 0, 0),)
    assert report["point_evaluations"] == 134
    assert report["ledger"]["actual_calls"] == 9899
    assert report["full_hermite_grid"] == "COMPLETE"
    assert report["source_qualified"] is False
    assert report["parent_contraction_recovered"] is True
    payload = decode(report["certificate"], cap=policy.max_certificate_bytes)
    assert payload["schema"] == "VERITAS_R98_CYCLE_TRANSFER_RECOVERY_V1"
    assert len(payload["point_certificates"]) == 134
    seen = set()
    for encoded in payload["point_certificates"]:
        point = unpack_point(encoded)
        node, zeta, precision = point["node"], point["zeta"], point["precision"]
        key = (node, tuple(zeta))
        assert key not in seen
        seen.add(key)
        assert precision == 1536
        assert tuple(map(tuple, point["result"])) == independent_matching_point(parent, node, zeta, precision)
    assert {node for node, _ in seen} == {-1, 1}
    assert sum(node == -1 for node, _ in seen) == sum(node == 1 for node, _ in seen) == 67
    checked = verify_transfer_recovery_certificate(parent, layout, report["certificate"],
                                                    policy=policy, max_points=256)
    assert checked["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_RECOVERY", checked
    assert checked["result"] == report["result"]


@pytest.mark.parametrize("mutation", ("drop", "duplicate", "bad_base64", "altered_point"))
def test_incomplete_or_corrupted_point_stream_never_recovers(complete_cycle_grid, mutation):
    from veritas.research.parent_child_r98.cycle_transfer_recovery import verify_transfer_recovery_certificate

    parent, layout, policy, report = complete_cycle_grid
    payload = deepcopy(decode(report["certificate"], cap=policy.max_certificate_bytes))
    if mutation == "drop":
        payload["point_certificates"].pop()
    elif mutation == "duplicate":
        payload["point_certificates"][1] = payload["point_certificates"][0]
    elif mutation == "bad_base64":
        payload["point_certificates"][0] = "!invalid!"
    else:
        point = unpack_point(payload["point_certificates"][0])
        point["node"] *= -1
        payload["point_certificates"][0] = base64.b64encode(zlib.compress(canonical(point), 9)).decode("ascii")
    checked = verify_transfer_recovery_certificate(parent, layout, canonical(payload),
                                                    policy=policy, max_points=256)
    assert not checked["status"].startswith("PASS_"), checked
    assert "result" not in checked


def test_field_size_and_precision_caps_refuse_without_partial_result():
    from veritas.research.parent_child_r98.cycle_transfer_recovery import contract_cycle_transfer

    parent, layout, _ = three_crossing_matching(extension_degree=2, precision=8)
    report = contract_cycle_transfer(parent, layout, max_points=256)
    assert report["status"].startswith("INCONCLUSIVE_") and "result" not in report
    parent, layout, _ = three_crossing_matching(extension_degree=7, precision=128)
    policy = replace(DEFAULT_SHRINKING_POLICY, max_precision=1024)
    report = contract_cycle_transfer(parent, layout, policy=policy, max_points=256)
    assert report["status"].startswith("INCONCLUSIVE_") and "result" not in report


@pytest.mark.parametrize("field,value", (("max_work", 1), ("max_certificate_bytes", 100_000),
                                         ("max_calls", 9898)))
def test_full_grid_resource_cap_refuses_without_partial_result(field, value):
    from veritas.research.parent_child_r98.cycle_transfer_recovery import contract_cycle_transfer

    parent, layout, _ = three_crossing_matching(extension_degree=7, precision=128)
    policy = replace(DEFAULT_SHRINKING_POLICY, **{field: value})
    report = contract_cycle_transfer(parent, layout, policy=policy, max_points=256)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "result" not in report and "certificate" not in report
