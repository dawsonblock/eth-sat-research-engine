"""R9.6 regression tests: one coefficient-admission counter, every path.

Red test (R9.5): a packet carrying four source-mode scalar coefficients was
accepted under ``EntryLimits(max_coefficients=1)`` and returned a numerical
result, because ``compile_entry`` counted only creation-ring jets.

Green test (R9.6): the shared counter admits dense tables, packet local
matrices, target coefficients, source scalars and clause polarities, and
refuses before any ring arithmetic.
"""
from dataclasses import replace
import json
import os
import subprocess
import sys

import pytest

from veritas.research.tapered_v4.coefficient_budget import (
    CoefficientAdmission, jet_coordinates, packet_coordinate_counts)
from veritas.research.tapered_v4.source_recipes import (
    SCHEMA, EntryBudget, EntryLimits, compile_entry, evaluate_compiled,
    evaluate_source_entry, make_reference)
from veritas.research.tapered_v4.source_recipe_bridge import source_reference_from_created
from veritas.research.tapered_v4.source_state import (
    SourceAdmissionError, SourceTensorReference)
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
from veritas.research.eth_recursive_contraction_v39.described_network import (
    CreatedDenseTensor, CreatedPacketTensor)
from veritas.research.eth_recursive_contraction_v39.lazy_children import (
    PacketTensorEntry)


def reference(data, *, kind="packet", arity=4, precision=3, polynomial=7,
              jet_length=1):
    payload = {"schema": SCHEMA, "kind": kind, "arity": arity,
               "creation_precision": precision, "polynomial": polynomial,
               "jet_length": jet_length, "data": data}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    return SourceTensorReference(arity, precision, polynomial, jet_length,
                                 SCHEMA + ":" + kind, raw)


ZERO_JET = [[0, 0]]

# rows = [], cols = [0, 1, 2, 3], no local matrix, no targets, one source with
# four scalar coefficients.  No creation-ring jet is stored, so this payload
# exercises the source-scalar coordinate class in isolation.
FOUR_SOURCE_SCALARS = [[], [0, 1, 2, 3], [], [], [[1, [1, 2, 3, 4]]]]


def admit(limits, data=None, *, arity=4):
    budget = EntryBudget(limits)
    compiled = compile_entry(
        reference(FOUR_SOURCE_SCALARS if data is None else data, arity=arity),
        budget)
    return budget, compiled


def test_four_source_scalars_refused_under_cap_one():
    """The exact defect: four scalar coordinates must not pass cap one."""
    with pytest.raises(SourceAdmissionError) as caught:
        admit(EntryLimits(max_coefficients=1))
    assert caught.value.status == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert "packet_source_coefficients" in str(caught.value)


@pytest.mark.parametrize("cap,admitted", [(1, False), (2, False), (3, False),
                                          (4, True), (5, True)])
def test_source_scalar_cap_boundary_is_exact(cap, admitted):
    if admitted:
        budget, _ = admit(EntryLimits(max_coefficients=cap))
        assert budget.coefficients.total == 4
    else:
        with pytest.raises(SourceAdmissionError):
            admit(EntryLimits(max_coefficients=cap))


def test_refusal_carries_no_accepted_numerical_result():
    limits = EntryLimits(max_coefficients=3)
    with pytest.raises(SourceAdmissionError):
        evaluate_source_entry(reference(FOUR_SOURCE_SCALARS), (1, 1, 1, 1),
                              precision=3, limits=limits)


def test_mixed_jets_and_scalars_share_one_counter():
    one = [[1, 0]]
    data = [[0], [1, 2], [[one, one]], [], [[2, [1, 1]]]]
    # 1 row * 2 cols * 1 jet * 2 coordinates = 4 local coordinates,
    # 0 target coordinates, 2 source scalars -> 6 total.
    budget, _ = admit(EntryLimits(max_coefficients=6), data, arity=3)
    assert budget.coefficients.total == 6
    assert budget.coefficients.by_kind == {
        "packet_local_matrix": 4, "packet_source_coefficients": 2}
    for cap in (5, 1):
        with pytest.raises(SourceAdmissionError):
            admit(EntryLimits(max_coefficients=cap), data, arity=3)


def test_zero_coefficient_packet_still_admits():
    """A packet storing no coefficients is admissible at the smallest cap."""
    limits = EntryLimits(max_coefficients=1)
    budget = EntryBudget(limits)
    compile_entry(reference([[], [], [], [], []], arity=0), budget)
    assert budget.coefficients.total == 0
    assert budget.coefficients.by_kind == {}


def test_clause_polarities_count_as_coordinates():
    data = [0, 1, 0]
    for cap, ok in ((2, False), (3, True)):
        limits = EntryLimits(max_coefficients=cap)
        budget = EntryBudget(limits)
        if ok:
            compile_entry(reference(data, kind="clause", arity=3), budget)
            assert budget.coefficients.by_kind == {"clause_polarities": 3}
        else:
            with pytest.raises(SourceAdmissionError):
                compile_entry(reference(data, kind="clause", arity=3), budget)


def test_dense_table_counts_every_entry_coordinate():
    entry = [[1, 0]]
    data = [entry] * 4
    limits = EntryLimits(max_coefficients=8)
    budget = EntryBudget(limits)
    compile_entry(reference(data, kind="dense", arity=2), budget)
    assert budget.coefficients.by_kind == {"dense_entries": 8}
    with pytest.raises(SourceAdmissionError):
        compile_entry(reference(data, kind="dense", arity=2),
                      EntryBudget(EntryLimits(max_coefficients=7)))


@pytest.mark.parametrize("mutation", [
    "bool_coefficient", "float_coefficient", "negative_coefficient",
    "oversized_exponent", "wrong_support_length", "duplicate_port",
    "non_int_port", "unhashable", "nested_dict"])
def test_malformed_payloads_rejected_not_coerced(mutation):
    data = [[], [0, 1], [], [], [[1, [1, 2]]]]
    payload = {"schema": SCHEMA, "kind": "packet", "arity": 2,
               "creation_precision": 3, "polynomial": 7, "jet_length": 1,
               "data": json.loads(json.dumps(data))}
    if mutation == "bool_coefficient":
        payload["data"][4][0][1][0] = True
    elif mutation == "float_coefficient":
        payload["data"][4][0][1][0] = 1.0
    elif mutation == "negative_coefficient":
        payload["data"][4][0][1][0] = -1
    elif mutation == "oversized_exponent":
        payload["data"][4][0][0] = EntryLimits().max_exponent + 1
    elif mutation == "wrong_support_length":
        payload["data"][4][0][1] = [1]
    elif mutation == "duplicate_port":
        payload["data"][1] = [0, 0]
    elif mutation == "non_int_port":
        payload["data"][1] = [0, "1"]
    elif mutation == "unhashable":
        payload["data"][4][0][1] = [[1, 2]]
    elif mutation == "nested_dict":
        payload["data"][4][0][1] = [{"a": 1}, 2]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    ref = SourceTensorReference(2, 3, 7, 1, SCHEMA + ":packet", raw)
    with pytest.raises(ValueError):
        compile_entry(ref, EntryBudget(EntryLimits()))


@pytest.mark.parametrize("field,value_", [
    ("max_coefficients", 0), ("max_coefficients", -1),
    ("max_coefficients", True), ("max_coefficients", 1.0),
    ("max_coefficients", 1_000_001)])
def test_invalid_coefficient_limits_rejected(field, value_):
    with pytest.raises(ValueError):
        EntryLimits(**{field: value_})


def test_admission_counter_is_atomic_on_refusal():
    counter = CoefficientAdmission(4)
    counter.admit(3, "a")
    with pytest.raises(SourceAdmissionError):
        counter.admit(2, "b")
    assert counter.total == 3
    assert counter.by_kind == {"a": 3}


def test_jet_and_packet_census_helpers_agree_with_the_compiler():
    assert jet_coordinates(2, 4) == 8
    census = packet_coordinate_counts([0], [1, 2], [[[ZERO_JET, ZERO_JET]]],
                                      [], [[2, [1, 1]]], 1, 2)
    assert census == {"packet_local_matrix": 4,
                      "packet_target_coefficients": 0,
                      "packet_source_coefficients": 2}


def test_bridge_and_compiler_admit_the_same_packet():
    """Bridge parity: both paths must refuse or admit the same payload."""
    ring = JetRing(ExtensionRing(3, 7), 1)
    created = CreatedDenseTensor(
        2, tuple(CreationJetEntry.capture(ring, ring.one) for _ in range(4)))
    ref = source_reference_from_created(created)
    budget = EntryBudget(EntryLimits())
    compile_entry(ref, budget)
    assert budget.coefficients.total == 8
    # Under a cap of seven both the bridge pre-scan and the compiler refuse.
    with pytest.raises(SourceAdmissionError):
        source_reference_from_created(created, limits=EntryLimits(max_coefficients=7))
    with pytest.raises(SourceAdmissionError):
        compile_entry(ref, EntryBudget(EntryLimits(max_coefficients=7)))


def test_source_leaf_propagates_the_refusal():
    from veritas.research.tapered_v4.source_leaf import (
        SourceLeafPolicy, contract_source_leaf)
    from veritas.research.tapered_v4.source_state import (
        SourceContext, SourceNode, SourceVertex)

    context = SourceContext(2, 1, 1, 1, 1, 1, 19)
    # Root tensors must live in the base V-ring, so use dense entries whose
    # jets carry only a constant coordinate.  4 entries * 1 jet * 4
    # coordinates = 16 admitted coordinates.
    tensor = reference([[[1, 0, 0, 0]]] * 4, kind="dense", arity=2,
                       precision=1, polynomial=19, jet_length=1)
    node = SourceNode(context, 2, (
        SourceVertex("row", 0, (0, 1), tensor),
        SourceVertex("column", 1, (0, 1), tensor),
    ), 0, 1)
    refused = contract_source_leaf(
        node, SourceLeafPolicy(entry_limits=EntryLimits(max_coefficients=1)))
    assert refused["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert "result" not in refused
    assert refused["theorem_mode_enabled"] is False
    admitted = contract_source_leaf(
        node, SourceLeafPolicy(entry_limits=EntryLimits(max_coefficients=32)))
    assert admitted["status"] == "EXACT_SOURCE_LEAF_MODULAR_CONTRACTION"
    assert admitted["ledger"]["coefficients"]["total"] == 32


def test_optimized_python_keeps_the_same_refusal():
    """python -O must not change admission or the refusal status."""
    script = (
        "import json,sys\n"
        "from veritas.research.tapered_v4.source_recipes import "
        "EntryLimits,EntryBudget,compile_entry\n"
        "from veritas.research.tapered_v4.source_state import "
        "SourceTensorReference,SourceAdmissionError\n"
        "raw=sys.argv[1].encode()\n"
        "ref=SourceTensorReference(4,3,7,1,'VERITAS_SOURCE_ENTRY_V1:packet',raw)\n"
        "try:\n"
        "    compile_entry(ref,EntryBudget(EntryLimits(max_coefficients=1)))\n"
        "    print('ADMITTED')\n"
        "except SourceAdmissionError as exc:\n"
        "    print('REFUSED',exc.status)\n")
    payload = json.dumps({"schema": SCHEMA, "kind": "packet", "arity": 4,
                          "creation_precision": 3, "polynomial": 7,
                          "jet_length": 1, "data": FOUR_SOURCE_SCALARS},
                         sort_keys=True, separators=(",", ":"))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    outputs = []
    for flags in ([], ["-O"]):
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(root, "src")
        result = subprocess.run(
            [sys.executable] + flags + ["-c", script, payload],
            capture_output=True, text=True, env=env, timeout=120)
        assert result.returncode == 0, result.stderr
        outputs.append(result.stdout.strip())
    assert outputs[0] == outputs[1] == "REFUSED INCONCLUSIVE_RESOURCE_LIMIT"


def test_constructor_prescan_does_not_reject_a_fitting_payload():
    """A small coefficient cap must not reject a payload that fits it."""
    ref = make_reference(kind="dense", arity=0, creation_precision=3,
                         defining_polynomial=7, jet_length=1,
                         data=[[[1, 0]]],
                         limits=EntryLimits(max_coefficients=2))
    assert evaluate_source_entry(ref, (), precision=3,
                                 limits=EntryLimits(max_coefficients=2))["result"] == ((1, 0),)
