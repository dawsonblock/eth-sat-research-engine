"""External cycle-transfer point computation and standalone replay."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_cycle_transfer_fixture import scalar_cycle_oracle, extension_cycle_oracle
from veritas.research.bounded_integer_encoding import decode_integer_object

ROOT = Path(__file__).resolve().parents[1]


def write_input(path):
    M, count = 44, 22
    # Input tables are little-endian by port. The corresponding immutable
    # source references use lexicographic tables [1,2,3,4] and [1,2,3,5].
    graph = {"root_s": 1024, "precision": 128, "extension_degree": 2, "edges": M,
             "vertices": [
                 {"side": "row", "ports": [2*i, 2*i+1], "table": [1, 3, 2, 4]}
                 for i in range(count)
             ] + [
                 {"side": "column", "ports": [2*i+1, 2*((i+1) % count)],
                  "table": [1, 3, 2, 5]}
                 for i in range(count)
             ]}
    path.write_text(json.dumps(graph))


def execute(input_path, output, certificate, *args):
    command = [sys.executable, "-m", "veritas.research.parent_child_r98.cycle_transfer_cli",
               str(input_path), "--groups", "64", "--output", str(output),
               "--certificate", str(certificate), *args]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120,
                          env=dict(os.environ, PYTHONPATH=str(ROOT / "src"),
                                   PYTHONDONTWRITEBYTECODE="1"))


def read_report(path):
    # Unlike immutable records, whole CLI reports contain elapsed-time floats.
    return json.loads(path.read_bytes(), object_hook=decode_integer_object)


@pytest.mark.parametrize("zeta,expected", (
    ("[1,0]", lambda: (scalar_cycle_oracle(44, 2944, -84), 0)),
    ("[0,1]", lambda: extension_cycle_oracle(44, 2944, (8, 28))),
))
def test_external_cli_computes_and_replays_full_point(tmp_path, zeta, expected):
    input_path, certificate = tmp_path / "cycle.json", tmp_path / "point.cert"
    output, replay = tmp_path / "point.json", tmp_path / "replay.json"
    write_input(input_path)
    produced = execute(input_path, output, certificate, "--node", "1", "--zeta", zeta)
    assert produced.returncode == 0, produced.stdout + produced.stderr
    report = read_report(output)
    assert report["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT"
    assert report["result"] == [list(expected())]
    assert report["ledger"]["actual_calls"] == 131
    assert report["retained_modes"] == 22 and not report["source_qualified"]
    assert certificate.is_file()

    verified = execute(input_path, replay, certificate, "--verify", "--node", "1", "--zeta", zeta)
    assert verified.returncode == 0, verified.stdout + verified.stderr
    consumed = read_report(replay)
    assert consumed["status"] == "PASS_FINITE_SCALED_CYCLE_TRANSFER_POINT"
    assert consumed["result"] == report["result"]
    assert consumed["certificate_sha256"] == report["certificate_sha256"]

    # An expected-point mismatch is invalid even if a different point could
    # happen to have the same value.
    wrong_node_output = tmp_path / "wrong-node.json"
    bad = execute(input_path, wrong_node_output, certificate, "--verify", "--node", "-1", "--zeta", zeta)
    assert bad.returncode == 1
    failure = read_report(wrong_node_output)
    assert not failure["status"].startswith("PASS_") and "result" not in failure
    assert "expected interpolation point" in failure["reason"]

    # Certificate paths are immutable on production invocation.
    again = execute(input_path, tmp_path / "overwrite.json", certificate, "--node", "1", "--zeta", zeta)
    assert again.returncode == 1
    assert "overwrite" in again.stdout
