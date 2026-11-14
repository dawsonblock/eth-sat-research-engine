"""Smoke tests for scripts/bench_sat_methods.py (fast cases only)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run_bench(*extra_args: str) -> list[dict]:
    env = {**dict(__import__("os").environ), "PYTHONPATH": "src", "VERITAS_R912_ROOT": str(ROOT)}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/bench_sat_methods.py"), *extra_args, "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


@pytest.mark.parametrize("key", ("source_qualified", "subexponential_bound_evidence", "theorem_backed"))
def test_bench_smoke_qualification_flags_false(key):
    records = _run_bench("--smoke")
    assert records
    for record in records:
        assert record[key] is False


def test_bench_smoke_toy_packet_agrees():
    records = _run_bench("--smoke")
    toy = next(r for r in records if r["case"] == "toy_packet_resummation")
    assert toy["agree"] is True


def test_bench_elimination_budget_refusal_case():
    records = _run_bench("--cases", "elimination_budget_refusal")
    record = records[0]
    assert record["case"] == "elimination_budget_refusal"
    assert record["tight_refused"] is True
    assert record["admitted_status"] == "PASS_EXACT_BOUNDED_WIDTH_ELIMINATION"
    assert record["planned_elimination_width"] == 17


def test_bench_coefficient_extract_192():
    records = _run_bench("--cases", "coefficient_extract_192")
    record = records[0]
    assert record["mode_count"] == 192
    assert record["separator_join_count"] == 192
    assert record["separator_max_monomial_table"] == 2
