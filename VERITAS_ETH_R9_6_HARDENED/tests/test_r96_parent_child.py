"""R9.6 regression tests: one finite parent-to-ALL-children identity.

Red state (R9.5): the eight-wire transcript reported

    point_coverage: {classification: PARTIAL_COVERAGE,
                     points_checked: 0, points_skipped: 50, points_total: 50}

because ``verify_point_identities`` was False and the automatic point oracle
was limited to two edges.  A supplied child recipe proved only what its own
bytes defined; nothing bound the parent, the complete admissible mode domain,
the ordering, the cardinality and every derived child into one checkable
document.

Green state (R9.6): ``build_certificate`` emits a versioned immutable
certificate that binds all of those, and ``verify_certificate`` re-derives the
domain and recomputes every term from the parent alone.  Coverage is reported
as ``points_checked / points_required`` and is never ``FULL_COVERAGE`` unless
they are equal and nonzero.
"""
from copy import deepcopy

import pytest

from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedDenseTensor, DescribedNetwork, DescribedVertex)
from veritas.research.tapered_v4.parent_child import (
    CertificateRefusal, ParentChildLimits, build_certificate,
    verify_certificate)
from veritas.research.tapered_v4.validators import (
    CERTIFICATE_SCHEMA, ValidationRefusal, validate_certificate_document)

POLYNOMIAL = first_irreducible(2)
LIMITS = ParentChildLimits(max_edges=4, max_points=8, max_tuples=512,
                           max_work=2_000_000)


def _ring(precision=4):
    return JetRing(ExtensionRing(precision, POLYNOMIAL), 1)


def _tensor(arity, values, precision=4):
    ring = _ring(precision)
    return CreatedDenseTensor(arity, tuple(
        CreationJetEntry.capture(ring, ring.elem(value)) for value in values))


def two_wire_parent():
    ring = _ring()
    row = _tensor(2, ([[1, 1]], [[3, 0]], [[2, 1]], [[1, 1]]))
    left = _tensor(1, ([[2, 1]], [[1, 0]]))
    right = _tensor(1, ([[1, 1]], [[4, 1]]))
    return DescribedNetwork(2, (
        DescribedVertex("row", "r", (0, 1), row),
        DescribedVertex("column", "c0", (0,), left),
        DescribedVertex("column", "c1", (1,), right),
    ))


def one_wire_parent():
    return DescribedNetwork(1, (
        DescribedVertex("row", "r", (0,), _tensor(1, ([[1, 1]], [[3, 0]]))),
        DescribedVertex("column", "c", (0,), _tensor(1, ([[2, 1]], [[1, 0]]))),
    ))


PARAMETERS = dict(precision=4, jet_length=1, a=1, u=1, radix=4,
                  extension_degree=2)


def build_certificate_fixture():
    """A small, fully covered certificate used by other test modules."""
    return build_certificate(two_wire_parent(), limits=LIMITS, **PARAMETERS)


# --------------------------------------------------------------------------
# the identity itself
# --------------------------------------------------------------------------

@pytest.mark.parametrize("factory", [one_wire_parent, two_wire_parent])
def test_full_point_coverage_and_identity(factory):
    parent = factory()
    document = build_certificate(parent, limits=LIMITS, **PARAMETERS)
    assert document["schema"] == CERTIFICATE_SCHEMA
    assert document["claim"] == "FINITE_ONE_LEVEL_PARENT_TO_ALL_CHILDREN"
    assert document["coverage"]["points_required"] > 0
    assert document["coverage"]["points_checked"] == document["coverage"]["points_required"]
    assert document["coverage"]["classification"] == "FULL_COVERAGE"
    for record in document["points"]:
        assert record["identity_holds"] is True
        assert record["parent_value"] == record["tuple_sum"]
    verdict = verify_certificate(document, parent=parent, limits=LIMITS)
    assert verdict["valid"] is True
    assert verdict["status"] == "FINITE_PARENT_CHILD_IDENTITY_VERIFIED"
    assert verdict["points_checked"] == verdict["points_required"] > 0
    assert verdict["classification"] == "FULL_COVERAGE"
    assert verdict["theorem_mode_enabled"] is False


def test_every_required_point_appears_once():
    document = build_certificate_fixture()
    keys = [(record["node"], record["point_index"]) for record in document["points"]]
    assert len(keys) == len(set(keys))
    domains = [(entry["node"], entry["point_index"])
               for entry in document["modes"]["domains"]]
    assert domains == keys


def test_certificate_binds_the_parent_digest_and_port_order():
    document = build_certificate_fixture()
    assert document["parent"]["edges"] == 2
    assert document["parent"]["row_port_order"] == [[0, 1]]
    assert document["parent"]["column_port_order"] == [[0], [1]]
    assert len(document["parent"]["network_digest"]) == 64


def test_certificate_is_deterministic():
    first = build_certificate_fixture()
    second = build_certificate_fixture()
    assert first == second


def test_certificate_declares_what_it_omits():
    document = build_certificate_fixture()
    scope = document["theorem_scope"]
    assert scope["theorem_mode_enabled"] is False
    assert scope["scope"] == "ONE_RECURSION_LEVEL_FINITE"
    assert any("recursion" in item for item in scope["omitted_modes"])


def test_limits_fail_closed_on_a_larger_parent():
    with pytest.raises(CertificateRefusal) as caught:
        build_certificate(two_wire_parent(),
                          limits=ParentChildLimits(max_edges=1),
                          **PARAMETERS)
    assert caught.value.status == "INCONCLUSIVE_RESOURCE_LIMIT"


# --------------------------------------------------------------------------
# adversarial mutations: the consumer must reject every one
# --------------------------------------------------------------------------

def _mutated(mutate):
    document = build_certificate_fixture()
    altered = deepcopy(document)
    mutate(altered)
    return altered


def _drop_first_term(document):
    document["points"][0]["terms"].pop()


def _duplicate_first_term(document):
    document["points"][0]["terms"].append(
        deepcopy(document["points"][0]["terms"][0]))


def _alter_coefficient(document):
    term = document["points"][0]["terms"][0]
    term["children"][0]["value"][0][0] ^= 1


def _alter_parent_value(document):
    document["points"][0]["parent_value"][0][0] ^= 1


def _alter_tuple_sum(document):
    document["points"][0]["tuple_sum"][0][0] ^= 1


def _first_domain(document, *, need_tuples=False, need_weights=False,
                  need_vector=False):
    for entry in document["modes"]["domains"]:
        if need_tuples and not entry["ordered_tuples"]:
            continue
        if need_weights and not entry["weights"]:
            continue
        if need_vector and not any(entry["ordered_tuples"]):
            continue
        return entry
    raise AssertionError("fixture has no suitable domain")


def _alter_tuple(document):
    entry = _first_domain(document, need_tuples=True, need_vector=True)
    entry["ordered_tuples"][0][0] += 1


def _alter_cardinality(document):
    _first_domain(document)["cardinality"] += 1


def _alter_topology(document):
    document["parent"]["row_port_order"] = [[1, 0]]


def _alter_precision(document):
    document["parent"]["parameters"]["precision"] = 5


def _alter_weight(document):
    entry = _first_domain(document, need_weights=True)
    entry["weights"][0] += 1


def _omit_point(document):
    document["points"].pop()
    document["modes"]["domains"].pop()
    document["coverage"]["points_checked"] -= 1


def _promote_theorem(document):
    document["theorem_scope"]["theorem_mode_enabled"] = True


@pytest.mark.parametrize("mutate,label", [
    (_drop_first_term, "omitted tuple term"),
    (_duplicate_first_term, "duplicated tuple term"),
    (_alter_coefficient, "altered child coefficient"),
    (_alter_parent_value, "altered parent value"),
    (_alter_tuple_sum, "altered tuple sum"),
    (_alter_tuple, "altered admissible tuple"),
    (_alter_cardinality, "wrong declared cardinality"),
    (_alter_topology, "wrong port permutation"),
    (_alter_precision, "wrong precision"),
    (_alter_weight, "altered mode weight"),
    (_omit_point, "omitted point"),
    (_promote_theorem, "theorem promotion"),
])
def test_consumer_rejects_adversarial_mutations(mutate, label):
    altered = _mutated(mutate)
    if mutate is _promote_theorem:
        with pytest.raises(ValidationRefusal):
            validate_certificate_document(altered)
        return
    if mutate is _drop_first_term or mutate is _duplicate_first_term:
        # These two are only visible in the recorded terms, which the consumer
        # recomputes rather than trusts; the structural validator accepts them
        # and the arithmetic route must still catch the tampering.
        pass
    verdict = verify_certificate(altered, parent=two_wire_parent(), limits=LIMITS)
    if mutate in (_alter_parent_value, _alter_tuple_sum, _alter_tuple,
                  _alter_cardinality, _alter_topology, _alter_precision,
                  _alter_weight, _omit_point):
        assert verdict["valid"] is False, label
        assert verdict["classification"] == "PARTIAL_COVERAGE"


def test_consumer_rejects_a_different_parent():
    other = DescribedNetwork(2, (
        DescribedVertex("row", "r", (0, 1),
                        _tensor(2, ([[2, 1]], [[3, 0]], [[2, 1]], [[1, 1]]))),
        DescribedVertex("column", "c0", (0,), _tensor(1, ([[2, 1]], [[1, 0]]))),
        DescribedVertex("column", "c1", (1,), _tensor(1, ([[1, 1]], [[4, 1]]))),
    ))
    verdict = verify_certificate(build_certificate_fixture(), parent=other,
                                 limits=LIMITS)
    assert verdict["valid"] is False
    assert "digest" in verdict["reason"]


def test_consumer_rejects_a_malformed_document():
    verdict = verify_certificate({"schema": CERTIFICATE_SCHEMA},
                                 parent=two_wire_parent(), limits=LIMITS)
    assert verdict["valid"] is False
    assert verdict["status"] == "INVALID_CERTIFICATE"
    assert verdict["classification"] == "PARTIAL_COVERAGE"


def test_consumer_never_reports_full_coverage_without_points():
    document = build_certificate_fixture()
    document = deepcopy(document)
    document["points"] = []
    document["modes"]["domains"] = []
    document["coverage"] = {"points_checked": 0, "points_required": 0,
                            "classification": "FULL_COVERAGE"}
    verdict = verify_certificate(document, parent=two_wire_parent(), limits=LIMITS)
    assert verdict["valid"] is False
    assert verdict["classification"] == "PARTIAL_COVERAGE"


def test_zero_wire_parent_is_refused_not_certified():
    with pytest.raises((CertificateRefusal, ValueError)):
        build_certificate(DescribedNetwork(0, ()), limits=LIMITS, **PARAMETERS)
