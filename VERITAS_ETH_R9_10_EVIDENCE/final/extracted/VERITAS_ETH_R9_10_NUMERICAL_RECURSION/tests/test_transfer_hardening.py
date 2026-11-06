"""API type, shared-call preflight, and CLI resource-status boundaries."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from test_cycle_transfer_fixture import three_crossing_matching
from veritas.research.parent_child_r98.cycle_transfer import evaluate_cycle_transfer
from veritas.research.parent_child_r98.cycle_transfer_recovery import contract_cycle_transfer
from veritas.research.parent_child_r98.model import Budget, canonical
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.transfer_io import load_transfer_layout


@pytest.mark.parametrize("groups", (True, 63, 64.0, 1025, "64"))
def test_custom_layout_rejects_noncanonical_group_count(tmp_path, groups):
    parent, layout, _ = three_crossing_matching()
    path = tmp_path / "layout.json"
    path.write_bytes(canonical({"schema": "VERITAS_R98_TRANSFER_LAYOUT_V1",
                                "parent_digest": parent.content_digest,
                                "source": layout.source}))
    with pytest.raises(ValueError, match="finite group count"):
        load_transfer_layout(parent, path, groups=groups, budget=Budget(DEFAULT_SHRINKING_POLICY))
    assert load_transfer_layout(parent, path, groups=64,
                                budget=Budget(DEFAULT_SHRINKING_POLICY)) == layout


def test_shared_call_budget_is_reserved_before_any_child_contraction():
    parent, layout, _ = three_crossing_matching()
    budget = Budget(replace(DEFAULT_SHRINKING_POLICY, max_calls=74))
    budget.call(0)  # Existing work in the same parent budget.
    report = evaluate_cycle_transfer(parent, layout, 1, (1, 0), budget=budget)
    assert report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "local-state calls" in report["reason"]
    assert budget.calls == 2 and budget.transitions == 0
    assert "result" not in report and "certificate" not in report


def test_shared_call_budget_exact_boundary_succeeds():
    parent, layout, _ = three_crossing_matching()
    budget = Budget(replace(DEFAULT_SHRINKING_POLICY, max_calls=75))
    budget.call(0)
    report = evaluate_cycle_transfer(parent, layout, 1, (1, 0), budget=budget)
    assert report["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT", report
    assert budget.calls == 75 and budget.transitions == 73


def test_producer_rejects_wrong_parent_or_layout_type_without_result():
    parent, layout, _ = three_crossing_matching()
    for bad_parent, bad_layout in ((None, layout), (parent, None)):
        point = evaluate_cycle_transfer(bad_parent, bad_layout, 1, (1, 0))
        recovery = contract_cycle_transfer(bad_parent, bad_layout)
        assert "typed parent and packet layout" in point["reason"]
        assert "typed parent and packet layout" in recovery["reason"]
        assert "result" not in point and "result" not in recovery


@pytest.mark.parametrize("module_name", ("cycle_transfer_cli", "cycle_recovery_cli"))
def test_verify_cli_marks_oversized_certificate_as_resource_refusal(tmp_path, module_name):
    from importlib import import_module

    root = Path(__file__).resolve().parents[1]
    module = import_module("veritas.research.parent_child_r98." + module_name)
    cert = tmp_path / "oversized.json"
    output = tmp_path / "report.json"
    cert.write_bytes(b"12")
    exit_code = module.main([str(root / "examples/r98_general_matching22.json"),
                             "--groups", "64", "--verify", "--certificate", str(cert),
                             "--output", str(output), "--max-certificate-bytes", "1"])
    report = json.loads(output.read_bytes())
    assert exit_code == 1 and report["status"] == "INCONCLUSIVE_RESOURCE_LIMIT", report
    assert "result" not in report
