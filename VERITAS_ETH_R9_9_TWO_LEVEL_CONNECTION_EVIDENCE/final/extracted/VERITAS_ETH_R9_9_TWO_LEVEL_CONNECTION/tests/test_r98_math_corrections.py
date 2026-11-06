"""Regressions for ring identity, parent ancestry and mathematical scope."""

from dataclasses import replace

import pytest

from veritas.research.appendix_d_schedule import schedule_path_preflight
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.eth_recursive_contraction_v39.point_modes import (
    check_point_modes,
    make_point_modes,
)
from veritas.research.parent_child_r98 import (
    Budget,
    ExponentTuple,
    ModeSet,
    PointEvaluationCertificate,
    Policy,
    construct_children,
    contract_scaled,
    from_described,
    verify_children,
)
from veritas.research.parent_child_r98.engine import (
    evaluate_point,
    leaf,
    verify_point_certificate,
)
from veritas.research.parent_child_r98.independent import tuple_coefficient
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.parent_child_r98.model import canonical, decode
from veritas.research.parent_child_r98.modes import build_modes, verify_modes
from veritas.research.parent_child_r98.packing import (
    audit_layout,
    construct_layout,
    preconditions,
)
from veritas.research.tensor import Factor, TensorNetwork


def parent(f=19, n=1):
    factors = tuple(
        factor
        for i in range(n)
        for factor in (
            Factor((i,), (-2 + i, 3 + i), f"row:{i}"),
            Factor((i,), (4 - i, 5 - i), f"col:{i}"),
        )
    )
    return from_described(
        describe_integer_network(
            TensorNetwork(n, factors), creation_precision=5, defining_polynomial=f
        ),
        root_s=16,
        precision=5,
    )


@pytest.mark.parametrize("f", (13, 25, 41))
def test_nonscalar_point_retains_supplied_irreducible_polynomial(f):
    p, budget = parent(f), Budget()
    layout = construct_layout(p, budget=budget)
    degree = f.bit_length() - 1
    zeta = (0, 1) + (0,) * (degree - 2)
    modes = build_modes(p, layout, -1, zeta, budget=budget)
    assert modes.certificate["irreducible_polynomial"] == f
    assert check_point_modes(modes.certificate)["valid"]
    value, certificate, report = evaluate_point(
        p, layout, modes, budget=budget, capture=True
    )
    assert any(value[0][1:]), "fixture must exercise extension coordinates"
    assert (
        report["per_point_independent_oracle_status"]
        == "PASS_HALF_EDGE_FACTOR_ELIMINATION"
    )
    replay = verify_point_certificate(p, layout, modes, certificate)
    assert replay["result"] == value and not replay["source_qualified"]


def test_nondefault_ring_cross_modes_and_complete_weighted_stream():
    p, budget = parent(13, 2), Budget()
    layout = construct_layout(p, a=1, u=1, budget=budget)
    modes = build_modes(p, layout, -1, (0, 1, 0), budget=budget)
    assert modes.certificate["modes"]
    _, _, report = evaluate_point(p, layout, modes, budget=budget)
    assert report["tuples"] == modes.certificate["mode_tuple_count"]
    assert report["tuple_domain"] == "ALL_WEIGHTED_TUPLES_OVER_RETAINED_MODES"
    assert report["mode_basis_scope"] == "ZERO_REDUCED_GEOMETRIC_POINT_MODES"
    assert report["paper_formal_mode_domain_enumerated"] is False


def test_nondefault_ring_complete_hermite_recovery():
    result = contract_scaled(parent(25), levels=1)
    assert result["result"] == ((7, 0, 0, 0),)
    assert result["hermite_coefficient_precision"] == "COEFFICIENTWISE_CHECKED"
    assert result["mode_basis_scope"] == "ZERO_REDUCED_GEOMETRIC_POINT_MODES"
    assert result["source_qualified"] is False


def test_selected_multimode_coefficients_without_claiming_full_point_coverage():
    p, budget = parent(25, 3), Budget(Policy(max_tuples=100_000))
    layout = construct_layout(p, budget=budget)
    modes = build_modes(p, layout, -1, (0, 1, 0, 0), budget=budget)
    assert len(modes.certificate["modes"]) == 2
    assert modes.certificate["mode_tuple_count"] == 66_795
    ring = JetRing(ExtensionRing(modes.certificate["precision"], 25), 1)
    # This deliberately checks selected coefficients, not an incomplete sum
    # advertised as a complete point result. Full point tests are separate.
    for exponents in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2), (4, 0)):
        beta = ExponentTuple(modes.content_digest, exponents)
        cs = construct_children(p, layout, modes, beta, budget=budget)
        expected = verify_children(p, layout, modes, beta, cs, budget=budget)
        value = ring.one
        for child, oracle in zip(cs, expected["values"]):
            actual = leaf(child.as_parent(p), budget)
            assert actual == oracle
            value = ring.mul(value, actual)
        assert value == tuple_coefficient(p, layout, modes, beta, budget=budget)


def test_edge_free_network_with_inherited_scalars_is_not_assumed_unit():
    net = TensorNetwork(0, (Factor((), (2,), "row:0"), Factor((), (3,), "col:0")))
    p = from_described(
        describe_integer_network(net, creation_precision=5, defining_polynomial=25),
        root_s=16,
        precision=5,
    )
    result = contract_scaled(p, levels=2)
    assert result["result"] == ((6, 0, 0, 0),)
    assert result["status"] == "PASS_FINITE_SCALED_LEAF"
    assert result["parent_child_recursion_performed"] is False
    assert result["mode_basis_scope"] == "NOT_RUN_LEAF"


def test_zero_depth_reports_leaf_without_recursive_identity():
    result = contract_scaled(parent(), levels=0)
    assert result["status"] == "PASS_FINITE_SCALED_LEAF"
    assert result["result"] == ((7, 0, 0, 0),)
    assert result["parent_child_recursion_performed"] is False
    assert result["child_count_per_tuple"] is None
    assert result["hermite_recovery"] is None
    assert result["ledger"]["actual_calls"] == 1
    assert result["ledger"]["transitions"] == 0


@pytest.mark.parametrize("missing", (True, False))
def test_mode_replay_requires_explicit_polynomial_metadata(missing):
    p, budget = parent(), Budget()
    layout = construct_layout(p, budget=budget)
    cert = build_modes(p, layout, -1, (0, 0, 0, 0), budget=budget).certificate
    if missing:
        del cert["irreducible_polynomial"]
    else:
        cert["irreducible_polynomial"] = None
    report = check_point_modes(cert)
    assert report["valid"] is False
    assert report["status"] == "INVALID_POINT_MODES"


@pytest.mark.parametrize("bad_f", (True, 11, 21, (1 << 10000) | 25))
def test_explicit_mode_polynomial_must_have_correct_degree_and_be_irreducible(bad_f):
    p = parent()
    layout = construct_layout(p, budget=Budget())
    with pytest.raises(ValueError):
        make_point_modes(layout.source, extension_degree=4, defining_polynomial=bad_f)


def test_legacy_default_mode_polynomial_remains_compatible():
    layout = construct_layout(parent(), budget=Budget())
    implicit = make_point_modes(layout.source, extension_degree=4)
    explicit = make_point_modes(
        layout.source, extension_degree=4, defining_polynomial=19
    )
    assert explicit == implicit


@pytest.fixture(scope="module")
def children():
    p, budget = parent(), Budget()
    layout = construct_layout(p, budget=budget)
    modes = build_modes(p, layout, -1, (1, 0, 0, 0), budget=budget)
    beta = ExponentTuple(modes.content_digest, ())
    return p, layout, modes, construct_children(p, layout, modes, beta, budget=budget)


def test_child_adapter_binds_the_actual_parent(children):
    p, _, _, cs = children
    assert cs[0].as_parent(p).ancestry_digest == cs[0].content_digest
    with pytest.raises(ValueError, match="another parent"):
        cs[0].as_parent(replace(p, root_s=17))


@pytest.mark.parametrize(
    "change", ({"depth": 2}, {"precision": 5}, {"defining_polynomial": 25})
)
def test_child_adapter_checks_depth_precision_and_ring(children, change):
    p, _, _, cs = children
    unit = cs[1]
    assert unit.edge_count == 0 and not unit.vertices
    with pytest.raises(ValueError, match="does not extend"):
        replace(unit, **change).as_parent(p)


@pytest.mark.parametrize("position", range(1, 6))
def test_boolean_half_edge_metadata_is_rejected(children, position):
    child = children[-1][0]
    rows = list(child.edge_map)
    row = list(rows[0])
    assert row[position] == 0
    row[position] = False
    rows[0] = tuple(row)
    with pytest.raises(ValueError, match="typed natural"):
        replace(child, edge_map=tuple(rows))


@pytest.mark.parametrize(
    "field,value",
    (("packet_ids", (False,)), ("inherited", (("row", False), ("column", 0)))),
)
def test_boolean_origin_metadata_is_rejected(children, field, value):
    with pytest.raises(ValueError):
        replace(children[-1][0], **{field: value})


def test_duplicate_and_unordered_half_edge_metadata_is_rejected(children):
    child = children[-1][0]
    for rows in ((child.edge_map[0],) * 2, tuple(reversed(child.edge_map))):
        with pytest.raises(ValueError, match="noncanonical half-edge"):
            replace(child, edge_map=rows)


@pytest.mark.parametrize("field", ("jet_length", "mode_tuple_count"))
def test_boolean_point_arithmetic_metadata_is_rejected(children, field):
    p, layout, modes, _ = children
    data = modes.certificate
    assert data[field] == 1
    data[field] = True
    forged = ModeSet(layout.content_digest, canonical(data))
    with pytest.raises(ValueError, match="arithmetic metadata requires integers"):
        verify_modes(p, layout, forged, budget=Budget())


def test_boolean_packet_endpoint_metadata_is_rejected(children):
    p, layout, _, _ = children
    data = layout.source
    assert data["edges"][0][0] == 0
    data["edges"][0][0] = False
    with pytest.raises(ValueError, match="endpoints differ"):
        audit_layout(p, replace(layout, source_bytes=canonical(data)))


def test_point_certificate_cannot_promote_reduced_basis_to_full_paper_domain(children):
    p, layout, modes, _ = children
    _, certificate, _ = evaluate_point(p, layout, modes, budget=Budget(), capture=True)
    data = decode(certificate.payload)
    assert data["paper_formal_mode_domain_enumerated"] is False
    data["paper_formal_mode_domain_enumerated"] = True
    forged = PointEvaluationCertificate(canonical(data))
    assert (
        verify_point_certificate(p, layout, modes, forged)["status"]
        == "INVALID_POINT_CERTIFICATE"
    )


def test_preflight_does_not_claim_descendant_or_packing_evidence():
    report = preconditions(parent())
    assert report["scope"] == "CURRENT_NODE_NUMERICS_ONLY"
    assert not report["actual_packing_verified"]
    assert not report["descendant_schedules_verified"]
    assert not report["source_qualified"]


def test_positive_root_schedule_can_fail_at_a_still_active_child():
    s = 1 << 131080
    report = schedule_path_preflight(s, ((s, 1), (s // 32, 8)), max_size_bits=131081)
    assert report["calls"][0]["status"] == "ACTIVE_NUMERIC_PRECONDITIONS_MET"
    assert report["calls"][0]["u"] == 1
    assert report["calls"][1]["edges"] > report["calls"][1]["leaf_threshold"]
    assert report["status"] == "INCONCLUSIVE_SCHEDULE" and report["depth"] == 1
    assert report["calls"][1]["u"] == 0
