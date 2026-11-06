from copy import deepcopy
from pathlib import Path
import json
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_r82 as points
import validate_r91 as aggregate


@pytest.fixture(scope="module")
def selected():
    old = json.loads((ROOT / "validation/r95_selected_points.json").read_text())
    old.pop("evidence_sha256")
    old["schema"] = points.SCHEMA
    return points.seal(old)


@pytest.mark.parametrize("mutation", ["result", "source", "schema", "coverage", "policy", "extra"])
@pytest.mark.parametrize("reseal", [False, True])
def test_point_artifact_and_semantics(selected, mutation, reseal):
    bad = deepcopy(selected)
    if mutation == "result":
        bad["cases"][0]["child_expansion"]["result"] = [[999999]]
    elif mutation == "source":
        bad["source_binding"] = {}
    elif mutation == "schema":
        bad["schema"] = "AUDIT_FALSE_SCHEMA"
    elif mutation == "coverage":
        bad["points_checked"] = 0
    elif mutation == "policy":
        bad["limits"]["parent_edges"] = 100
    else:
        bad["unexpected_claim"] = True
    if reseal:
        bad.pop("evidence_sha256")
        bad = points.seal(bad)
    assert not points.check_saved(bad, selected)


def test_portable_semantics_preserve_artifact_integrity_and_v1(selected):
    new = deepcopy(selected)
    new.pop("evidence_sha256")
    new["python"] = "another interpreter build"
    new["peak_rss_unit"] = "different platform"
    new["cases"][0]["elapsed_seconds"] += 3
    new = points.seal(new)
    assert new["semantic_sha256"] == selected["semantic_sha256"]
    assert new["evidence_sha256"] != selected["evidence_sha256"]
    assert points.check_saved(new, selected)
    old = json.loads((ROOT / "validation/r95_selected_points.json").read_text())
    assert points.check_saved(old, new)
    old["cases"][0]["child_expansion"]["result"] = [[999999]]
    assert not points.check_saved(old, new)


@pytest.mark.parametrize("mutation", ["missing_reports", "forged_axiom", "missing_output",
    "missing_lines", "hidden_axiom", "wrong_positive", "lost_theorem"])
def test_aggregate_derives_claims_from_raw_output(mutation):
    record = json.loads((ROOT / "validation/r9_conditional_expectation_proof.json").read_text())
    entry = next(e for e in record["results"] if e["axiom_lines"])
    name = next(iter(entry["axiom_audit"]["reports"]))
    if mutation == "missing_reports":
        entry["axiom_audit"]["reports"] = {}
    elif mutation == "forged_axiom":
        entry["axiom_audit"]["reports"][name] = ["sorryAx"]
    elif mutation == "missing_output":
        del entry["output"]
    elif mutation == "missing_lines":
        del entry["axiom_lines"]
    elif mutation == "hidden_axiom":
        entry["output"] += "\n'unauthorized' depends on axioms: [Injected.axiom]"
    elif mutation == "lost_theorem":
        entry["output"] = entry["output"].replace(name, name + "_substitute")
    else:
        record["lean_creation_contracts_checked"] = False
    checked = aggregate.check_lean_evidence_freshness(record)
    assert not checked["fresh"] and not checked["derived_flags"]
    assert not aggregate.lean_flag(record, checked, "lean_packet_slot_bijection_proven")
