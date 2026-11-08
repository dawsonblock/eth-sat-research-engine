"""External input adaptation, including asymmetric shuffled port tables."""

import json
import subprocess
import sys
from itertools import product
from pathlib import Path

import pytest

from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.tapered_v4.source_recipes import evaluate_source_entry


def shuffled_input():
    return {
        "root_s": 16,
        "precision": 5,
        "extension_degree": 2,
        "edges": 4,
        "vertices": [
            {"side": "column", "ports": [i], "table": [i + 2, 5 - i]} for i in range(4)
        ]
        + [{"side": "row", "ports": [3, 0, 2, 1], "table": list(range(-7, 9))}],
    }


def write_input(tmp_path, data):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(data))
    return path


def test_direct_adapter_preserves_little_endian_shuffled_port_entries(tmp_path):
    data = shuffled_input()
    parent = load_input(write_input(tmp_path, data))
    row = parent.vertices[0]
    assert row.ports == (3, 0, 2, 1)
    table = data["vertices"][-1]["table"]
    for bits in product((0, 1), repeat=4):
        value = evaluate_source_entry(row.tensor, bits, precision=5)
        expected = table[sum(bit << i for i, bit in enumerate(bits))] % 32
        assert value["result"] == ((expected, 0),)


def test_external_cli_leaf_matches_independent_original_assignment_sum(tmp_path):
    data = shuffled_input()
    input_path = write_input(tmp_path, data)
    output = tmp_path / "result.json"
    expected = 0
    for bits in product((0, 1), repeat=4):
        term = data["vertices"][-1]["table"][
            sum(bits[e] << i for i, e in enumerate((3, 0, 2, 1)))
        ]
        for edge, vertex in enumerate(data["vertices"][:4]):
            term *= vertex["table"][bits[edge]]
        expected += term
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "veritas.research.parent_child_r98.shrinking_cli",
            str(input_path),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr + run.stdout
    report = json.loads(output.read_text())
    assert report["status"] == "PASS_FINITE_SCALED_LEAF"
    assert report["result"] == [[expected % 32, 0]]
    assert not report["source_qualified"]


@pytest.mark.parametrize(
    "field,value", (("precision", True), ("edges", 1025), ("extension_degree", 1))
)
def test_loader_rejects_invalid_dimensions(tmp_path, field, value):
    data = shuffled_input()
    data[field] = value
    with pytest.raises(ValueError):
        load_input(write_input(tmp_path, data))


def test_checked_in_large_fixture_uses_direct_recipe_adapter():
    root = Path(__file__).resolve().parents[1]
    parent = load_input(root / "examples/r98_shrinking_484.json")
    assert parent.edge_count == 484 and parent.precision == 512
    assert len(parent.vertices) == 968 and parent.maximum_degree == 1


def test_checked_in_cycle_fixture_is_connected_and_has_only_degree_two_vertices():
    root = Path(__file__).resolve().parents[1]
    parent = load_input(root / "examples/r98_shrinking_cycle484.json")
    assert parent.edge_count == 484 and len(parent.vertices) == 484
    assert all(len(vertex.ports) == 2 for vertex in parent.vertices)
    seen = {0}
    while True:
        before = len(seen)
        for vertex in parent.vertices:
            if any(edge in seen for edge in vertex.ports):
                seen.update(vertex.ports)
        if len(seen) == before:
            break
    assert seen == set(range(484))


def test_external_cli_refuses_nonconstant_active_family_without_result(tmp_path):
    data = {
        "root_s": 64,
        "precision": 32,
        "extension_degree": 2,
        "edges": 22,
        "vertices": [
            {"side": side, "ports": [edge], "table": [1, 1]}
            for side in ("row", "column")
            for edge in range(22)
        ],
    }
    data["vertices"][0]["table"] = [1, 2]
    input_path = write_input(tmp_path, data)
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "veritas.research.parent_child_r98.shrinking_cli",
            str(input_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 1, run.stderr + run.stdout
    report = json.loads(run.stdout)
    assert not report["status"].startswith("PASS_") and "result" not in report
    assert not report["source_qualified"]
