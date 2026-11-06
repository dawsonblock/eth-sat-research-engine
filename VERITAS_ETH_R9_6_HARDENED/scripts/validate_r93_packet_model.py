#!/usr/bin/env python3
"""Compare the concrete Lean packet codec with both bounded Python builders.

Lean #eval comparisons are finite differential evidence, not kernel proofs of
Python execution. The separate proof gate checks universal Lean model lemmas.
"""
from __future__ import annotations

import argparse
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from veritas.research.eth_packing_v26 import (  # noqa: E402
    PacketAddress, audit_global_packet_index, build_global_packet_index,
    construct_implicit_packing, construct_streaming_d3_packing,
    verify_streaming_d3_certificate,
)
import validate_conditional_expectation_lean as gate  # noqa: E402

POLICY = {"seed": 9303, "random_cases": 8, "max_edges": 20,
          "max_constructor_work": 3_000_000, "max_dense_slots": 50_000,
          "max_audit_work": 5_000_000, "decode_samples_per_case": 8,
          "command_timeout_seconds": 120, "theorem_mode_enabled": False}
AUDITED_FILES = (
    "scripts/validate_r93_packet_model.py", "lean-toolchain",
    "scripts/validate_conditional_expectation_lean.py",
    "paper/quantitative-contraction.tex",
    "src/veritas/research/eth_packing_v26/global_packet_address.py",
    "src/veritas/research/eth_packing_v26/global_packet_address_check.py",
    "src/veritas/research/eth_packing_v26/packet_bijection.py",
    "src/veritas/research/eth_packing_v26/packet_bijection_check.py",
    "src/veritas/research/eth_packing_v26/implicit.py",
    "src/veritas/research/eth_packing_v26/expectation.py",
    "src/veritas/research/eth_packing_v26/streaming.py",
    "src/veritas/research/eth_packing_v26/streaming_check.py",
    "pyproject.toml",
    ".github/workflows/test.yml",
)


def source_manifest():
    # Dynamic inventory detects added/deleted package code as well as edits.
    # Generated evidence, caches, and release manifests are excluded.
    package_files = {p.relative_to(ROOT).as_posix() for p in (ROOT / "src").rglob("*.py")}
    files = sorted(set(AUDITED_FILES) | set(gate.PROOF_FILES) | package_files)
    result = {}
    for relative in files:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlinked audit input: {relative}")
        result[relative] = gate.sha256(path)
    return result


def corpus():
    cases = [([], 2, 1), ([(0, 0)], 2, 2),
             ([(0, 0), (1, 1), (0, 1)], 2, 1),
             ([(0, 0), (0, 0), (1, 2), (0, 2), (1, 1)], 2, 2),
             ([(0, i) for i in range(12)] + [(0, 0)] * 2, 2, 1),
             ([(0, 1), (1, 0), (0, 1), (2, 0)], 3, 2),
             ([(1, 1), (0, 1), (0, 0), (0, 0)], 3, 1)]
    rng = random.Random(POLICY["seed"])
    for _ in range(POLICY["random_cases"]):
        cases.append(([(rng.randrange(3), rng.randrange(3))
                       for _ in range(rng.randrange(8))],
                      rng.choice((2, 3)), rng.choice((1, 2))))
    return cases


def show_address(address):
    if address is None:
        return "R93E:none"
    pairs = ",".join(f"{x}-{y}" for x, y in address.pattern)
    return f"R93E:{address.packet}:{address.slot}:{pairs}"


def padded_samples(packing):
    if not packing.H:
        return []
    choices = [(x, y) for x in range(packing.r) for y in range(x, packing.r)]
    addresses = []
    for pattern in product(choices, repeat=packing.a):
        copies = 1 << sum(x == y for x, y in pattern)
        for packet in range(packing.H // copies):
            for slot in range(1 << packing.a):
                addresses.append(PacketAddress(pattern, packet, slot))
    count = min(len(addresses), POLICY["decode_samples_per_case"])
    if count < 2:
        return addresses[:count]
    return [addresses[i * (len(addresses) - 1) // (count - 1)] for i in range(count)]


def prepare_vectors():
    lines = ["import D3FullPacketModel", "import D3PaddedConstruction", "open D3FullPacketModel",
             "def showEncode : Option Address → String",
             '  | none => "R93E:none"',
             '  | some a => "R93E:" ++ toString a.packet ++ ":" ++ toString a.slot ++ ":" ++',
             '    String.intercalate "," (a.pattern.map (fun p => toString p.1 ++ "-" ++ toString p.2))',
             "def showDecode : Option Nat → String",
             '  | none => "R93D:none"', '  | some i => "R93D:" ++ toString i']
    expected, records = [], []
    for edges, r, a in corpus():
        for builder in ("coordinate", "whole_word"):
            certificate_valid = None
            if builder == "coordinate":
                packing = construct_implicit_packing(
                    edges, r=r, a=a, max_work=POLICY["max_constructor_work"])
            else:
                result = construct_streaming_d3_packing(
                    edges, r=r, a=a, max_work=POLICY["max_constructor_work"], score_backend="python")
                packing = result.packing
                certificate_valid = verify_streaming_d3_certificate(result.certificate)["valid"]
                if not certificate_valid:
                    raise ValueError("independent streaming certificate replay failed")
            index = build_global_packet_index(packing, max_edges=POLICY["max_edges"])
            audit = audit_global_packet_index(packing, index=index,
                                              max_edges=POLICY["max_edges"],
                                              max_dense_slots=POLICY["max_dense_slots"],
                                              max_work=POLICY["max_audit_work"])
            if not audit["valid"]:
                raise ValueError(f"independent address audit failed: {audit}")
            n = len(records)
            classes = [list(zip(packing.rows[u], packing.cols[v])) for u, v in edges]
            term = "[" + ",".join("[" + ",".join(f"({x},{y})" for x, y in cls) + "]"
                                   for cls in classes) + "]"
            lines.append(f"def classes{n} : List SymbolClass := {term}")
            lines.append(f'#eval IO.println ("R93H:" ++ toString (D3PaddedConstruction.paddedHeight classes{n} {a}))')
            expected.append(f"R93H:{packing.H}")
            for edge_id in range(len(edges) + 1):  # also the first invalid edge index
                lines.append(f"#eval IO.println (showEncode (encodeEdge classes{n} {edge_id}))")
                expected.append(show_address(index.address_of(edge_id) if edge_id < len(edges) else None))
            addresses = list(dict.fromkeys([index.address_of(i) for i in range(len(edges))]
                                           + padded_samples(packing)))
            for address in addresses:
                pattern = "[" + ",".join(f"({x},{y})" for x, y in address.pattern) + "]"
                lines.append(f"#eval IO.println (showDecode (decodeEdge classes{n} "
                             f"⟨{pattern}, {address.packet}, {address.slot}⟩))")
                found = index.edge_at(address)
                expected.append("R93D:none" if found is None else f"R93D:{found}")
            records.append({"builder": builder, "edges": edges, "radix": r, "width": a,
                            "height": packing.H, "audit": audit,
                            "streaming_certificate_valid": certificate_valid,
                            "height_checks": 1, "encode_checks": len(edges) + 1,
                            "decode_checks": len(addresses)})
    return "\n".join(lines) + "\n", expected, records


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(Path(os.environ["VERITAS_EVIDENCE_DIR"]) / "r9_3_packet_differential.json")
                        if os.environ.get("VERITAS_EVIDENCE_DIR") else "validation/r9_3_packet_differential.json")
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    report = {"schema": "VERITAS_ETH_R93_PACKET_MODEL_DIFFERENTIAL_V1",
              "status": "NOT_RUN", "policy": POLICY, "python": platform.python_version(),
              "platform": platform.platform(), "checks_executed": 0,
              "qualification": "FINITE_DIFFERENTIAL_ONLY",
              "executable_refinement_proven": False, "theorem_mode_enabled": False,
              "commands": [], "limitations": [
                  "Hash matching is not executor authentication.",
                  "Lean #eval is finite executable testing, not a proof of CPython refinement.",
                  "Dense audit shares address datatypes and the R9.2 reference decoder.",
                  "Coarse work admission and per-command timeout; no enforced process memory cap.",
                  "No full recursion, source-active packing scale, or complexity qualification."]}
    started = time.perf_counter()
    try:
        manifest = source_manifest()
        report["source_manifest"] = manifest
        report["source_manifest_sha256"] = hashlib.sha256(json.dumps(
            manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if manifest["paper/quantitative-contraction.tex"] != gate.PINNED_CONTRACTION_SHA256:
            raise ValueError("manuscript hash mismatch")
        lean = os.environ.get("LEAN_BIN") or shutil.which("lean")
        if not lean:
            raise FileNotFoundError("pinned Lean toolchain is unavailable")
        version = subprocess.run([lean, "--version"], cwd=ROOT, capture_output=True,
                                 text=True, timeout=30, check=True).stdout.strip()
        report["lean_version"] = version
        if not gate.check_lean_version((ROOT / "lean-toolchain").read_text().strip(), version):
            raise ValueError("Lean version mismatch")
        source, expected, records = prepare_vectors()
        report["cases"] = records
        report["generated_lean_sha256"] = hashlib.sha256(source.encode()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="veritas-r93-") as tmp:
            env = {**os.environ, "LEAN_PATH": tmp}
            # The full packet module imports the earlier slot and port modules.
            for relative in gate.PROOF_FILES:
                if relative == "proofs/D3FirstMinimum.lean":
                    break
                dest = gate.PROOF_OUTPUTS.get(relative)
                if not dest:
                    raise ValueError(f"missing dependency output: {relative}")
                begin = time.perf_counter()
                result = subprocess.run([lean, "-o", str(Path(tmp) / dest), relative],
                                        cwd=ROOT, env=env, text=True, capture_output=True,
                                        timeout=POLICY["command_timeout_seconds"])
                report["commands"].append({"file": relative, "exit_code": result.returncode,
                                           "elapsed_seconds": time.perf_counter() - begin})
                if result.returncode:
                    raise ValueError(f"Lean dependency failed: {relative}: {result.stdout[-2000:]}")
            vector_file = Path(tmp) / "PacketVectors.lean"
            vector_file.write_text(source, encoding="utf-8")
            result = subprocess.run([lean, str(vector_file)], cwd=ROOT, env=env,
                                    text=True, capture_output=True,
                                    timeout=POLICY["command_timeout_seconds"])
            report["vector_exit_code"] = result.returncode
            if result.returncode:
                raise ValueError("Lean vector evaluation failed: " + result.stdout[-3000:])
            actual = [line.strip() for line in result.stdout.splitlines() if line.startswith("R93")]
            report["checks_executed"] = len(actual)
            report["checks_expected"] = len(expected)
            if actual != expected:
                mismatches = [i for i, (x, y) in enumerate(zip(actual, expected)) if x != y]
                raise ValueError(f"Lean/Python address mismatch: indices {mismatches[:10]}, "
                                 f"actual length {len(actual)}, expected {len(expected)}")
        if source_manifest() != manifest:
            raise ValueError("audit inputs changed during execution")
        report["status"] = "PASS_FINITE_DIFFERENTIAL"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        report["status"] = "FAIL_OR_INCOMPLETE"
        report["error"] = str(exc).replace(str(ROOT), "<repository>")
    report["elapsed_seconds"] = time.perf_counter() - started
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in
                     ("status", "checks_executed", "elapsed_seconds")}))
    return 0 if report["status"] == "PASS_FINITE_DIFFERENTIAL" else 1


if __name__ == "__main__":
    raise SystemExit(run())
