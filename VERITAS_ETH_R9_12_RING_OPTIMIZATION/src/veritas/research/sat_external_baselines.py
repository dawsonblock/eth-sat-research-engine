"""Pinned external SAT baseline harness (E2).

Runs optional Kissat / CaDiCaL when binaries are on PATH; always includes
internal VERITAS reference lanes. No ``theorem_backed`` on timings.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Literal, Optional

from veritas.core.cnf import CNF
from veritas.research.adaptive_contract import adaptive_count
from veritas.solvers.reference import solve


@dataclass(frozen=True)
class PinnedBaselineSpec:
    id: str
    binary: str
    pinned_release: str
    mode: Literal["decision", "count"]

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "binary": self.binary,
            "pinned_release": self.pinned_release,
            "mode": self.mode,
        }


# Document pins; version probe is best-effort at runtime.
PINNED_DECISION_BASELINES: tuple[PinnedBaselineSpec, ...] = (
    PinnedBaselineSpec("kissat", "kissat", "sc-2024 / 3.1.1 family", "decision"),
    PinnedBaselineSpec("cadical", "cadical", "Rel-2.1.0 family", "decision"),
)


def _probe_version(binary: str) -> Optional[str]:
    path = shutil.which(binary)
    if not path:
        return None
    for args in (["--version"], ["-h"], []):
        try:
            proc = subprocess.run(
                [path, *args],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            blob = (proc.stdout or "") + (proc.stderr or "")
            if blob.strip():
                line = blob.strip().splitlines()[0][:200]
                return line
        except (OSError, subprocess.TimeoutExpired):
            continue
    return "unknown"


def _run_external_decision(
    cnf: CNF,
    spec: PinnedBaselineSpec,
    *,
    timeout_s: float,
) -> dict[str, Any]:
    path = shutil.which(spec.binary)
    if not path:
        return {
            "baseline_id": spec.id,
            "status": "SKIPPED",
            "reason": f"binary {spec.binary!r} not on PATH",
            "pinned_release": spec.pinned_release,
            "theorem_backed": False,
        }
    version = _probe_version(spec.binary)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cnf", delete=False) as fh:
        fh.write(cnf.to_dimacs())
        dimacs_path = fh.name
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [path, dimacs_path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        elapsed = time.perf_counter() - t0
        combined = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 10:
            sat_status = "SAT"
        elif proc.returncode == 20:
            sat_status = "UNSAT"
        elif proc.returncode == 0 and re.search(r"\bSATISFIABLE\b", combined, re.I):
            sat_status = "SAT"
        elif proc.returncode == 0 and re.search(r"\bUNSATISFIABLE\b", combined, re.I):
            sat_status = "UNSAT"
        else:
            sat_status = "UNKNOWN"
        return {
            "baseline_id": spec.id,
            "status": sat_status if sat_status != "UNKNOWN" else "UNKNOWN",
            "exit_code": proc.returncode,
            "seconds": elapsed,
            "version_probe": version,
            "pinned_release": spec.pinned_release,
            "binary_path": path,
            "theorem_backed": False,
            "qualification": "external_timing_not_proof",
        }
    except subprocess.TimeoutExpired:
        return {
            "baseline_id": spec.id,
            "status": "TIMEOUT",
            "seconds": timeout_s,
            "version_probe": version,
            "pinned_release": spec.pinned_release,
            "theorem_backed": False,
        }
    finally:
        try:
            os.unlink(dimacs_path)
        except OSError:
            pass


def run_veritas_reference_decision(
    cnf: CNF, *, timeout_s: float = 4.0, max_nodes: int = 150_000
) -> dict[str, Any]:
    t0 = time.perf_counter()
    result = solve(cnf, count=False, timeout_s=timeout_s, max_nodes=max_nodes)
    return {
        "baseline_id": "veritas_reference",
        "status": result.status,
        "nodes": result.nodes,
        "seconds": time.perf_counter() - t0,
        "pinned_release": "in-repo reference.py",
        "theorem_backed": False,
    }


def run_veritas_adaptive_count(cnf: CNF, *, timeout_s: float = 15.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    out = adaptive_count(cnf, timeout_s=timeout_s)
    return {
        "baseline_id": "veritas_adaptive_count",
        "status": out.get("status"),
        "count": out.get("count"),
        "engine": out.get("engine"),
        "seconds": time.perf_counter() - t0,
        "pinned_release": "in-repo adaptive_contract.py",
        "theorem_backed": False,
        "warning": out.get("warning"),
    }


def run_baseline_matrix(
    cnf: CNF,
    *,
    task: Literal["decision", "count"] = "decision",
    external_timeout_s: float = 10.0,
    include_external: bool = True,
) -> dict[str, Any]:
    """Compare VERITAS internal baselines and optional external solvers."""
    rows: list[dict[str, Any]] = []
    if task == "decision":
        rows.append(run_veritas_reference_decision(cnf))
        if include_external:
            for spec in PINNED_DECISION_BASELINES:
                rows.append(_run_external_decision(cnf, spec, timeout_s=external_timeout_s))
    else:
        rows.append(run_veritas_adaptive_count(cnf))

    veritas = next(r for r in rows if r["baseline_id"] == rows[0]["baseline_id"])
    agreements = []
    if task == "decision" and veritas.get("status") in ("SAT", "UNSAT"):
        for row in rows:
            if row.get("status") in ("SAT", "UNSAT"):
                agreements.append(
                    {
                        "baseline_id": row["baseline_id"],
                        "agrees_with_veritas_reference": row["status"] == veritas["status"],
                    }
                )

    return {
        "schema": "VERITAS_SAT_BASELINE_MATRIX_V1",
        "task": task,
        "formula_sha256": cnf.digest(),
        "pinned_specs": [s.to_dict() for s in PINNED_DECISION_BASELINES],
        "runs": rows,
        "agreements": agreements,
        "source_qualified": False,
        "subexponential_bound_evidence": False,
        "theorem_backed": False,
        "qualification": "benchmark_harness_only",
    }
