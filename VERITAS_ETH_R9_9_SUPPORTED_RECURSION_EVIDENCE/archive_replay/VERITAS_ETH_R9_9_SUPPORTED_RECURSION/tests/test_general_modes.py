"""General singleton modes retain nonzero cross terms and complete tuples."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.independent_r82.point_mode_oracle import (
    _IndependentExtension,
    _Meter,
)
from veritas.research.parent_child_r98.general_modes import (
    build_general_modes,
    verify_general_modes,
)
from veritas.research.parent_child_r98.model import (
    Budget, ModeSet, PacketLayout, ParentCall, Policy, Refusal, canonical,
)
from veritas.research.parent_child_r98.modes import TupleChecker, weighted_tuples
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.tapered_v4.source_recipes import make_reference
from veritas.research.tapered_v4.source_state import SourceVertex


def point_fixture(*, extension_degree=2, precision=5):
    f = first_irreducible(extension_degree)
    reference = make_reference(
        kind="dense", arity=1, creation_precision=precision,
        defining_polynomial=f, jet_length=1,
        data=[[[1] + [0] * (extension_degree - 1)],
              [[2] + [0] * (extension_degree - 1)]],
    )
    parent = ParentCall(
        1024, 0, precision, f, 2,
        tuple(SourceVertex(side, i, (i,), reference)
              for side in ("row", "column") for i in range(2)),
    )
    source = {
        "schema": "VERITAS_ETH_D3_IMPLICIT_SPARSE_ACTIVE_V1",
        "claim": "FINITE_NONEMPTY_PACKET_VIEW_SPARSE_SLOTS",
        "r": 64, "a": 1, "L": 2, "D": 4096, "M": 2, "H_pad": 2,
        "edges": [[0, 0], [1, 1]],
        "row_labels": {"0": [0], "1": [0]},
        "column_labels": {"0": [0], "1": [1]},
        "packets": [
            {"symbol_pairs": [[0, 0]], "index": 0, "occupied_slots": [[0, 0]]},
            {"symbol_pairs": [[0, 1]], "index": 0, "occupied_slots": [[0, 1]]},
        ],
    }
    # Point semantics can be tested on a valid nonshrinking layout. The driver
    # separately insists that every actual generated child strictly shrinks.
    return parent, PacketLayout(parent.content_digest, 1, 1, canonical(source), "scaled_singletons")


@pytest.mark.parametrize("node,integer", ((-1, -20), (1, -84)))
def test_nonzero_singleton_has_local_and_cross_action(node, integer):
    parent, layout = point_fixture()
    modes = build_general_modes(parent, layout, node, (1, 0), budget=Budget())
    record = modes.certificate
    coefficient = (integer % (1 << 133), 0)
    assert record["local"] == [[0, 0, [list(coefficient)]]]
    assert record["cross_pairs"] == [[1, 1]]
    assert len(record["modes"]) == 1
    mode = record["modes"][0]
    assert mode == {
        "packet": 1, "tile_residue": 0, "exponent": 0, "weight": 1,
        "source_group": 1, "target_group": 0,
        "rows": [[1, [list(coefficient)]]], "column_terms": [[1, 1]],
    }
    assert record["mode_tuple_count"] == 133
    budget = Budget()
    checker = TupleChecker(modes, budget)
    tuples = list(weighted_tuples(modes, budget=budget))
    for beta in tuples:
        checker.accept(beta)
    checker.finish()
    assert [beta.values for beta in tuples] == [(i,) for i in range(133)]


def test_verifier_uses_independent_cauchy_arithmetic(monkeypatch):
    parent, layout = point_fixture()
    modes = build_general_modes(parent, layout, 1, (0, 1), budget=Budget())
    import veritas.research.parent_child_r98.general_modes as module
    monkeypatch.setattr(module, "cauchy_point_value", lambda *a, **kw: pytest.fail("production Cauchy called"))
    result = verify_general_modes(parent, layout, modes, budget=Budget())
    assert result["nonzero_cross_group_modes"] == 1
    assert result["weighted_tuple_count"] == 133


@pytest.mark.parametrize("field,value", (
    ("packet", 0), ("tile_residue", 1), ("exponent", 1), ("weight", 2),
    ("source_group", 0), ("target_group", 1),
    ("rows", [[1, [[1, 0]]]]), ("column_terms", [[1, 0]]),
))
def test_independent_verifier_rejects_changed_mode(field, value):
    parent, layout = point_fixture()
    modes = build_general_modes(parent, layout, 1, (1, 0), budget=Budget())
    record = modes.certificate
    record["modes"][0][field] = value
    with pytest.raises(ValueError, match="mode action"):
        verify_general_modes(parent, layout, ModeSet(layout.content_digest, canonical(record)), budget=Budget())


@pytest.mark.parametrize("mutation", ("drop_cross", "drop_mode", "duplicate_mode", "change_local", "bad_count", "bool_node", "changed_precision"))
def test_independent_verifier_rejects_inventory_and_metadata_mutations(mutation):
    parent, layout = point_fixture()
    modes = build_general_modes(parent, layout, 1, (1, 0), budget=Budget())
    record = deepcopy(modes.certificate)
    if mutation == "drop_cross":
        record["cross_pairs"] = []
    elif mutation == "drop_mode":
        record["modes"] = []
    elif mutation == "duplicate_mode":
        record["modes"] *= 2
    elif mutation == "change_local":
        record["local"][0][2][0][0] += 1
    elif mutation == "bad_count":
        record["mode_tuple_count"] -= 1
    elif mutation == "bool_node":
        record["node"] = True
    else:
        record["precision"] += 1
    with pytest.raises(ValueError):
        verify_general_modes(parent, layout, ModeSet(layout.content_digest, canonical(record)), budget=Budget())


def test_zero_node_point_keeps_cross_topology_but_no_zero_modes():
    parent, layout = point_fixture()
    modes = build_general_modes(parent, layout, 1, (0, 0), budget=Budget())
    assert modes.certificate["cross_pairs"] == [[1, 1]]
    assert modes.certificate["modes"] == modes.certificate["local"] == []
    assert modes.certificate["mode_tuple_count"] == 1


def test_large_connected_nonzero_point_refuses_complete_stream_before_children():
    path = Path(__file__).resolve().parents[1] / "examples/r98_shrinking_cycle484.json"
    parent = load_input(path)
    budget = Budget(DEFAULT_SHRINKING_POLICY)
    layout = construct_vertex_shrinking_layout(parent, budget=budget)
    with pytest.raises(Refusal, match="complete general weighted tuple count") as exc:
        build_general_modes(parent, layout, 1, (1, 0), budget=budget)
    assert exc.value.status == "INCONCLUSIVE_RESOURCE_LIMIT"
    assert budget.calls == budget.transitions == budget.tuples == 0


def test_generic_point_preserves_default_ring_degree_limit_and_opts_in_to_eleven():
    parent, layout = point_fixture(extension_degree=11)
    with pytest.raises(ValueError, match="degree 2..8"):
        _IndependentExtension(133, parent.defining_polynomial, _Meter(100_000, 60))
    reference = _IndependentExtension(
        133, parent.defining_polynomial, _Meter(100_000, 60), max_extension_degree=12
    )
    assert reference.e == 11
    modes = build_general_modes(parent, layout, 1, (1,) + (0,) * 10, budget=Budget())
    assert modes.certificate["extension_degree"] == 11
    assert verify_general_modes(parent, layout, modes, budget=Budget())["weighted_tuple_count"] == 133


def test_high_precision_modes_are_explicitly_opted_in():
    parent, layout = point_fixture(precision=1024)
    with pytest.raises(Refusal, match="point precision cap"):
        build_general_modes(parent, layout, 1, (1, 0), budget=Budget())
    policy = replace(Policy(), max_precision=65536)
    modes = build_general_modes(parent, layout, 1, (1, 0), budget=Budget(policy))
    assert modes.certificate["precision"] == 1152
    assert modes.certificate["local"][0][2][0][0] == (1 << 1152) - 84
