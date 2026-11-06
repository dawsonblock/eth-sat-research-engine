#!/usr/bin/env python3
"""Differential check of the Lean transcription against CPython.

This evaluates `D3PythonScore.pyCandidateScore` inside Lean and compares every
result with `streaming._candidate_score` on the same input.  It is evidence
about the CPython -> Lean-transcription boundary; it is not a proof, and it
does not touch the open `wordMatches` bridge.

Usage::

    LEAN_BIN=/path/to/lean python scripts/validate_r91_python_model.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from veritas.research.eth_packing_v26.streaming import _candidate_score  # noqa: E402

DEPENDENCIES = (
    "ConditionalExpectationAverage",
    "ConcreteD3ConditionalExpectation",
    "D3VarianceBound",
    "D3PotentialIdentity",
    "D3CollisionBridge",
    "D3InitialScore",
    "ConditionalExpectationSelection",
    "D3SelectionBridge",
    "D3CanonicalSequence",
    "D3StateInvariants",
    "D3ParentScoreIndependence",
    "D3ChildTransition",
    "D3RealizedLoads",
    "D3ClassAccounting",
    "D3VarianceAlgebra",
    "D3SymbolPorts",
    "D3PythonOrder",
    "D3PythonScoreModel",
)


class Counter:
    def __init__(self):
        self.used = 0

    def tick(self, amount=1):
        self.used += amount


def corpus(seed: int):
    rng = random.Random(seed)
    cases = []
    fixed = [
        ([(0, 0), (1, 1), (0, 1)], 2, 1, ("", -1), []),
        ([(0, 0), (1, 1), (0, 1)], 2, 1, ("R", 0), [0]),
        ([(0, 0), (1, 1), (0, 1)], 2, 1, ("R", 1), [1]),
        ([(0, 0), (1, 1), (0, 1)], 2, 1, ("C", 0), [0]),
        ([(0, 0)], 3, 2, ("R", 0), [1, 2]),
        ([(0, 0), (0, 0)], 2, 1, ("C", 0), [1]),
    ]
    for edges, r, a, vertex, label in fixed:
        cases.append({"edges": edges, "r": r, "a": a, "vertex": vertex,
                      "label": label, "partial": {}})
    for _ in range(6):
        r = rng.choice([2, 3])
        a = rng.choice([1, 2])
        m = rng.randint(1, 5)
        edges = [(rng.randrange(3), rng.randrange(3)) for _ in range(m)]
        partial = {}
        for (u, v) in edges:
            if rng.random() < 0.5:
                for d in range(a):
                    partial[("R", u, d)] = rng.randrange(r)
            if rng.random() < 0.5:
                for d in range(a):
                    partial[("C", v, d)] = rng.randrange(r)
        vertex = rng.choice([("", -1)] + [("R", u) for u, _ in edges])
        label = [rng.randrange(r) for _ in range(a)]
        cases.append({"edges": edges, "r": r, "a": a, "vertex": vertex,
                      "label": label, "partial": partial})
    return cases


def lean_vertex(vertex):
    side, ident = vertex
    if side == "":
        # A vertex that cannot occur in the corpus, so the label is never used.
        return "((PackingSide.row, 999999))", 2
    return (f"(PackingSide.{'row' if side == 'R' else 'col'}, {ident})",
            0 if side == "R" else 1)


def render(cases):
    lines = ["import D3PythonScoreModel", "", "open D3PythonScore", "",
             "def mkPartial : List (PackingVertex × Nat × Nat) → PackingPartial",
             "  | [] => fun _ _ => none",
             "  | (v, d, x) :: rest => fun u e => if u = v ∧ e = d then some x else mkPartial rest u e",
             ""]
    for index, case in enumerate(cases):
        entries = ", ".join(
            f"((PackingSide.{'row' if side == 'R' else 'col'}, {ident}), {coord}, {symbol})"
            for (side, ident, coord), symbol in sorted(case["partial"].items()))
        edges = ", ".join(f"({u}, {v})" for u, v in case["edges"])
        vertex, _ = lean_vertex(case["vertex"])
        word = "[" + ", ".join(str(x) for x in case["label"]) + "]"
        if not case["label"]:
            word = "[]"
        lines.append(f"def case{index}Partial : PackingPartial := mkPartial [{entries}]")
        lines.append(f"def case{index}Score : Nat := "
                     f"pyCandidateScore case{index}Partial {vertex} {word} "
                     f"{case['r']} {case['a']} [{edges}]")
        lines.append(f"#eval case{index}Score")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/r91_python_model.json")
    parser.add_argument("--seed", type=int, default=20261103)
    args = parser.parse_args()
    lean = os.environ.get("LEAN_BIN") or shutil.which("lean")
    if not lean:
        print("Lean executable not found; set LEAN_BIN", file=sys.stderr)
        return 2
    cases = corpus(args.seed)
    source = render(cases)
    build = Path(tempfile.mkdtemp(prefix="veritas-r91-model-"))
    env = os.environ.copy()
    env["LEAN_PATH"] = str(build)
    start = time.perf_counter()
    compiled = []
    for module in DEPENDENCIES:
        path = ROOT / "proofs" / f"{module}.lean"
        result = subprocess.run([lean, "-o", str(build / f"{module}.olean"), str(path)],
                                cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, env=env)
        if result.returncode != 0:
            print(f"failed to compile {module}:\n{result.stdout}", file=sys.stderr)
            return 1
        compiled.append(module)
    corpus_path = build / "Corpus.lean"
    corpus_path.write_text(source, encoding="utf-8")
    run = subprocess.run([lean, str(corpus_path)], cwd=ROOT, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    elapsed = time.perf_counter() - start
    if run.returncode != 0:
        print(f"corpus evaluation failed:\n{run.stdout}", file=sys.stderr)
        return 1
    values = [int(line) for line in run.stdout.splitlines() if line.strip().isdigit()]
    if len(values) != len(cases):
        print(f"expected {len(cases)} values, got {len(values)}:\n{run.stdout}",
              file=sys.stderr)
        return 1
    mismatches = []
    records = []
    for index, (case, value) in enumerate(zip(cases, values)):
        reference = _candidate_score(case["edges"], case["partial"], r=case["r"],
                                     a=case["a"], D=case["r"] ** (2 * case["a"]),
                                     vertex=case["vertex"], label=tuple(case["label"]),
                                     work=Counter())
        record = {
            "case": index,
            "edges": case["edges"],
            "r": case["r"],
            "a": case["a"],
            "vertex": list(case["vertex"]),
            "label": case["label"],
            "partial_entries": len(case["partial"]),
            "lean_score": value,
            "python_score": reference,
            "equal": value == reference,
        }
        records.append(record)
        if value != reference:
            mismatches.append(record)
    payload = {
        "schema": "VERITAS_ETH_R91_PYTHON_MODEL_DIFFERENTIAL_V1",
        "claim": "LEAN_TRANSCRIPTION_MATCHES_CPYTHON_ON_A_CORPUS",
        "qualification": (
            "Evidence about the CPython -> Lean-transcription boundary only. "
            "It does not prove the score identity with concreteD3ScoreCandidate."
        ),
        "lean_binary": Path(lean).name,
        "lean_binary_path_recorded": False,
        "lean_version_output": subprocess.run(
            [lean, "--version"], text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT).stdout.strip(),
        "compiled_modules": compiled,
        "model_sha256": hashlib.sha256(
            (ROOT / "proofs/D3PythonScoreModel.lean").read_bytes()).hexdigest(),
        "streaming_sha256": hashlib.sha256(
            (ROOT / "src/veritas/research/eth_packing_v26/streaming.py").read_bytes()
        ).hexdigest(),
        "corpus_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "elapsed_seconds": elapsed,
        "cases": len(cases),
        "mismatches": len(mismatches),
        "all_equal": not mismatches,
        "records": records,
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"{len(cases)} cases, {len(mismatches)} mismatches, {elapsed:.1f}s -> {output}",
          file=sys.stderr)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
