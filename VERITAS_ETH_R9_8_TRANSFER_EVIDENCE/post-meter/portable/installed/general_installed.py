"""Run the installed general driver with complete nonconstant recovery."""
import json
import platform
from pathlib import Path

from veritas.research.parent_child_r98.general_engine import contract_general_shrinking
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.tapered_v4.provenance import source_binding

binding = source_binding()["digest"]
parent = load_input(Path(__file__).with_name("general_matching22.json"))
result = contract_general_shrinking(parent)
assert result["status"] == "PASS_FINITE_SCALED_GENERAL_SHRINKING_RECURSION", (
    result["status"], result.get("reason")
)
assert result["result"] == ((31**22, 0, 0, 0, 0, 0, 0),)
assert result["edge_layers"] == {"0": [22], "1": [0, 2]}
assert result["ledger"]["actual_calls"] == 8577
assert result["ledger"]["point_evaluations"] == 134
assert result["ledger"]["nonshrinking_children"] == 0
assert len(result["transitions"]) == 134
assert len({point["term_sha256"] for point in result["transitions"]}) > 1
for point in result["transitions"]:
    assert point["child_count"] == len(point["child_edges"]) == 64
    assert sum(point["child_edges"]) == 44
    assert all(64 * count <= 132 and count < 22 for count in point["child_edges"])
assert result["source_qualified"] is False
assert result["theorem_mode_enabled"] is False
assert result["implementation_source_sha256"] == binding == source_binding()["digest"]
print(json.dumps({
    "status": "PASS_INSTALLED_GENERAL_SHRINKING_RECURSION",
    "source_binding": binding,
    "python": platform.python_version(),
    "edge_layers": result["edge_layers"],
    "result": result["result"],
    "independent_expected_result": "31^22",
    "actual_calls": result["ledger"]["actual_calls"],
    "point_evaluations": result["ledger"]["point_evaluations"],
    "nonshrinking_children": result["ledger"]["nonshrinking_children"],
    "maximal_precision_used": result["maximal_precision_used"],
    "source_qualified": False,
    "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
    "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
}))
