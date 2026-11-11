"""R9.10 recursive contract emits DecompositionWorkLedger rows (E3)."""
from dataclasses import replace
from pathlib import Path

import pytest

from veritas.research.parent_child_r98.model import Budget
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r99.cli import load_layout
from veritas.research.parent_child_r910.engine import contract

ROOT = Path(__file__).resolve().parents[1]
POLICY = replace(
    DEFAULT_SHRINKING_POLICY,
    max_work=1_000_000_000,
    max_seconds=600,
    max_certificate_bytes=100_000_000,
)


@pytest.mark.slow
def test_contract_records_decomposition_work_ledger():
    parent = load_input(ROOT / "examples/r910_matching235.json")
    layout = load_layout(parent, ROOT / "examples/r910_matching235_layout.json", Budget(POLICY))

    def factory(call, a, u, budget):
        return layout if call.depth == parent.depth else construct_vertex_shrinking_layout(call, budget=budget)

    events = []
    report = contract(
        parent,
        schedule=((1, 1), (1, 1)),
        layout_factory=factory,
        policy=POLICY,
        evidence_sink=events.append,
    )
    assert report["status"] == "PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION"
    decomp = report["decomposition_work"]
    assert decomp["schema"] == "VERITAS_SAT_WORK_AGGREGATE_V1"
    assert decomp["theorem_backed"] is False
    assert len(decomp["steps"]) > 0
    first = decomp["steps"][0]
    assert first["q"] == 64
    assert len(first["child_works"]) == 64
    assert first["w_transform"] >= 0
    assert first["w_new"] == (
        first["w_transform"]
        + sum(first["child_works"])
        + first["w_reconstruct"]
        + first["w_check"]
    )
    assert report["evidence_bytes"] > 0
    assert len(events) > 0
