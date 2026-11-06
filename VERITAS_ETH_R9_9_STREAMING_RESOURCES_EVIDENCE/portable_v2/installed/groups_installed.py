"""Installed finite group parameter, actual shrinking and refusal checks."""
import json
import platform
from dataclasses import replace
from pathlib import Path
from veritas.research.parent_child_r98 import contract_shrinking, contract_general_shrinking
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.tapered_v4.provenance import source_binding

binding = source_binding()["digest"]
parent = load_input(Path(__file__).with_name("groups_cycle484.json"))
policy = replace(DEFAULT_SHRINKING_POLICY, max_calls=1025, max_depth=1, max_precision=31488)
result = contract_shrinking(parent, groups=512, policy=policy)
assert result["status"] == "PASS_FINITE_SCALED_SHRINKING_RECURSION", (result["status"], result.get("reason"))
assert result["result"] == ((1 << 484, 0),)
assert result["edge_layers"] == {"0": [484], "1": [0, 4]}
assert result["ledger"]["actual_calls"] == 1025
assert result["ledger"]["point_evaluations"] == 2
assert result["ledger"]["nonshrinking_children"] == 0
assert result["maximal_precision_used"] == 31488
assert result["child_count_per_tuple"] == result["finite_group_count"] == 512
assert result["source_group_count"] == 64 and not result["source_qualified"]
assert not result["theorem_mode_enabled"]
assert result["implementation_source_sha256"] == binding == source_binding()["digest"]
for point in result["transitions"]:
    assert point["child_count"] == len(point["child_edges"]) == 512
    assert sum(point["child_edges"]) == 968
    assert all(512 * edges <= 6 * 484 and edges <= 4 for edges in point["child_edges"])
    assert point["cross_group_pairs"] == 242
    assert point["retained_modes"] == 0 and point["complete_tuple_count"] == 1
refusals = []
for groups in (128, 256):
    refused = contract_shrinking(parent, groups=groups)
    assert refused["status"].startswith("INCONCLUSIVE_")
    assert "result" not in refused and refused["ledger"]["actual_calls"] == 0
    refusals.append({"groups": groups, "status": refused["status"], "reason": refused["reason"]})
refused = contract_general_shrinking(parent, groups=512)
assert refused["status"] == "INCONCLUSIVE_RESOURCE_LIMIT"
assert "tuple" in refused["reason"].lower()
assert "result" not in refused and refused["ledger"]["actual_calls"] == 0
refusals.append({"groups": 512, "family": "GENERAL", "status": refused["status"], "reason": refused["reason"]})
print(json.dumps({"status": "PASS_INSTALLED_FINITE_GROUPS", "source_binding": binding,
                  "python": platform.python_version(), "edge_layers": result["edge_layers"],
                  "result": result["result"], "actual_calls": 1025, "point_evaluations": 2,
                  "maximal_precision_used": 31488, "nonshrinking_children": 0,
                  "finite_group_count": 512, "source_group_count": 64,
                  "refusals": refusals, "source_qualified": False,
                  "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
                  "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED"}))
