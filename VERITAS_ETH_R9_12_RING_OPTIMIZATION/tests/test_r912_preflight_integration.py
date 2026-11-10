"""Wire and packet preflight before exact R9.12 elimination."""
from dataclasses import replace
import importlib.util
from pathlib import Path

import pytest

from veritas.research.parent_child_r912.elimination import EliminationBudget
from veritas.research.parent_child_r912.fixture_bridge import compiled_child_packet_at_jet_point
from veritas.research.parent_child_r912.preflight import wire_elimination_preflight
from veritas.research.parent_child_r912.routes import Route, contract_routed, select_route
from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r99.cli import load_layout
from veritas.research.parent_child_r913.support_resummation import compare_support_aware_resummation
from veritas.research.tapered_v4.source_recipes import EntryLimits

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(DEFAULT_SHRINKING_POLICY, max_work=2_000_000, max_seconds=600)

spec = importlib.util.spec_from_file_location(
    "interaction_probe", ROOT / "scripts/experiment_r912_interaction.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def _interaction_parent(tmp_path, n=8, offset=3):
    data = probe.graph(n, offset)
    source = tmp_path / "input.json"
    from veritas.research.parent_child_r98.model import canonical

    source.write_bytes(canonical(data))
    return data, load_input(source, max_extension_degree=12)


def test_wire_preflight_matches_plan_without_table_allocation(tmp_path, monkeypatch):
    import veritas.research.parent_child_r912.elimination as elimination

    _, parent = _interaction_parent(tmp_path, n=8, offset=3)
    budget = EliminationBudget()

    def forbidden(*_args, **_kwargs):
        pytest.fail("preflight must not evaluate factor tables")

    monkeypatch.setattr(elimination, "evaluate_compiled", forbidden)
    sketch = wire_elimination_preflight(parent, budget)
    assert sketch["status"] == "COMPLETE"
    assert sketch["wire_count"] == parent.edge_count
    from veritas.research.parent_child_r912.elimination import plan

    assert sketch["ordering"] == plan(parent, budget)
    selection = select_route(parent, Route.ELIMINATION, budget)
    assert selection["preflight"]["wire"]["ordering"]["predicted_work"] == sketch["ordering"]["predicted_work"]


def test_matching22_carries_wire_and_mode_preflight_on_elimination_route():
    parent = load_input(ROOT / "examples/r98_general_matching22.json")
    layout = construct_vertex_shrinking_layout(parent, budget=Budget(POLICY))
    report = contract_routed(
        parent,
        route=Route.ELIMINATION,
        preflight_layout=layout,
        shrink_budget=Budget(POLICY),
    )
    assert report["status"].startswith("PASS"), report
    pre = report["route_selection"]["preflight"]
    assert pre["wire"]["status"] == "COMPLETE"
    assert pre["mode_dependency"]["status"] == "COMPLETE"
    assert "elimination_width" in pre["mode_dependency"]


def test_multislot_carries_nonempty_mode_preflight():
    parent = load_input(ROOT / "examples/r99_multislot_crossing2.json")
    layout = load_layout(
        parent,
        ROOT / "examples/r99_multislot_crossing2_layout.json",
        Budget(POLICY),
    )
    from veritas.research.parent_child_r912.preflight import packet_mode_preflight

    summary = packet_mode_preflight(parent, layout, budget=Budget(POLICY))
    assert summary["mode_count"] >= 1


def test_interaction_fixture_wire_preflight_only(tmp_path):
    _, parent = _interaction_parent(tmp_path, n=8, offset=3)
    selection = select_route(parent, Route.AUTO, EliminationBudget())
    assert selection["preflight"]["wire"]["status"] == "COMPLETE"
    assert selection["preflight"]["mode_dependency"] is None


def test_multislot_packet_support_resummation_via_fixture_bridge():
    parent = load_input(ROOT / "examples/r99_multislot_crossing2.json")
    layout = load_layout(
        parent,
        ROOT / "examples/r99_multislot_crossing2_layout.json",
        Budget(POLICY),
    )
    compiled, row_certificate = compiled_child_packet_at_jet_point(
        parent, layout, budget=Budget(POLICY), point_index=0
    )
    assert compiled.kind == "packet"
    bits = (0,) * compiled.reference.arity
    targets = [beta for beta, _ in compiled.data[3] if beta]
    weights = tuple(3 for _ in targets)
    aware = compare_support_aware_resummation(
        compiled,
        bits,
        weights,
        precision=parent.precision,
        limits=EntryLimits(max_work=2_000_000),
        row_certificate=row_certificate,
    )
    assert aware.enumerate_agrees_with_hybrid or aware.supported_monomial_count <= 16
    if aware.supported_monomial_count == aware.total_monomial_count:
        assert aware.full_agrees_with_enumerated
