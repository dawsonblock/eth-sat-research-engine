#!/usr/bin/env python3
"""Aggregate the R9.1 evidence into one machine-readable record.

This script never promotes a result: every qualification flag is derived from
an artifact that already exists on disk, and a missing artifact clears the
corresponding flag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_conditional_expectation_lean import (  # noqa: E402
    ALLOWED_LEAN_AXIOMS,
    CENTRAL_THEOREMS_BY_FILE,
    PINNED_CONTRACTION_SHA256,
    PROOF_FILES,
    check_lean_version,
    check_axiom_reports,
    apply_module_qualifications,
    proof_manifest_sha256,
)

from veritas.research.eth_packing_v26 import cpp_backend  # noqa: E402
from veritas.research.eth_packing_v26.streaming import (  # noqa: E402
    construct_streaming_d3_packing,
)
from veritas.research.eth_packing_v26.streaming_check import (  # noqa: E402
    verify_streaming_d3_certificate,
)

FIXTURE_EDGES = [(0, 0), (1, 1), (0, 1)]
FIXTURE_EXPECTED = {
    "vertices": [["R", 0], ["R", 1], ["C", 0], ["C", 1]],
    "labels": [[0], [1], [0], [1]],
    "scores": [22, 16, 16, 12],
    "final": 12,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def check_lean_evidence_freshness(lean, root: Path = ROOT) -> dict:
    """Require Lean evidence to match the current proof inputs and checker.

    This rejects stale or structurally incomplete reports. SHA-256 matching
    does not authenticate who ran Lean or sign the report; the local proof
    binary remains an explicit trust input.
    """
    reasons = []
    if not isinstance(lean, dict):
        return {"fresh": False, "reasons": ["evidence is missing or malformed"]}

    manuscript = root / "paper/quantitative-contraction.tex"
    toolchain_file = root / "lean-toolchain"
    validator = root / "scripts/validate_conditional_expectation_lean.py"
    if lean.get("status") != "PASS":
        reasons.append("Lean status is not PASS")
    if not manuscript.is_file() or sha256(manuscript) != PINNED_CONTRACTION_SHA256:
        reasons.append("current manuscript does not match the pinned digest")
    if lean.get("manuscript_sha256") != PINNED_CONTRACTION_SHA256:
        reasons.append("evidence manuscript digest is missing or stale")
    if lean.get("manuscript_pin_matches") is not True:
        reasons.append("evidence does not confirm the manuscript pin")
    if lean.get("manuscript_source") != "paper/quantitative-contraction.tex":
        reasons.append("evidence manuscript path is missing or unexpected")

    expected_toolchain = (toolchain_file.read_text(encoding="utf-8").strip()
                          if toolchain_file.is_file() else None)
    if not expected_toolchain or lean.get("lean_toolchain") != expected_toolchain:
        reasons.append("Lean toolchain pin is missing or stale")
    if lean.get("pinned_lean_version_matches") is not True:
        reasons.append("evidence does not confirm the pinned Lean version")
    version_output = lean.get("lean_version_output")
    if (not isinstance(version_output, str) or not expected_toolchain or
            not check_lean_version(expected_toolchain, version_output)):
        reasons.append("recorded Lean version output does not match the current pin")

    current_validator_hash = sha256(validator) if validator.is_file() else None
    if (not current_validator_hash or
            lean.get("validator_sha256") != current_validator_hash):
        reasons.append("Lean validator source changed since evidence generation")
    current_manifest_hash = proof_manifest_sha256(root)
    if lean.get("proof_manifest_sha256") != current_manifest_hash:
        reasons.append("proof source manifest changed or is absent")

    results = lean.get("results")
    expected_order = list(PROOF_FILES)
    if not isinstance(results, list):
        reasons.append("per-module proof results are absent")
        results = []
    observed_order = [entry.get("file") if isinstance(entry, dict) else None
                      for entry in results]
    if observed_order != expected_order:
        reasons.append("per-module proof result inventory is missing, duplicated, or reordered")
    by_file = {entry.get("file"): entry for entry in results
               if isinstance(entry, dict) and isinstance(entry.get("file"), str)}
    if len(by_file) != len(results):
        reasons.append("per-module proof result entries are malformed or duplicated")

    derived_flags = {}
    derived_reports = {}
    for relative in expected_order:
        path = root / relative
        entry = by_file.get(relative)
        if not path.is_file() or path.is_symlink():
            reasons.append(f"proof source is missing or symlinked: {relative}")
            continue
        if entry is None:
            continue
        if entry.get("sha256") != sha256(path):
            reasons.append(f"proof source changed since Lean compilation: {relative}")
        if type(entry.get("return_code")) is not int or entry.get("return_code") != 0:
            reasons.append(f"Lean did not successfully compile: {relative}")
        if entry.get("sorryAx_absent") is not True:
            reasons.append(f"sorryAx check missing or failed: {relative}")
        required = CENTRAL_THEOREMS_BY_FILE.get(relative, ())
        output = entry.get("output")
        if not isinstance(output, str) or not output.strip() or "sorryAx" in output:
            reasons.append(f"missing or disallowed compiler output: {relative}")
            continue
        audit = check_axiom_reports(output, required)
        printed = {name: name in audit["reports"] for name in required}
        lines = [line for line in output.splitlines() if "depends on axioms:" in line]
        if (not audit["passed"] or audit != entry.get("axiom_audit") or
                printed != entry.get("central_theorems_printed") or
                entry.get("axiom_lines") != lines or
                entry.get("central_theorems_present") is not True or
                entry.get("central_theorems_qualified") is not True):
            reasons.append(f"compiler details disagree with theorem inventory: {relative}")
            continue
        derived_reports[relative] = list(audit["reports"])
        apply_module_qualifications(derived_flags, relative, {
            "return_code": entry.get("return_code"), "sorryAx_absent": True,
            "central_theorems_qualified": True})
    for name, derived in derived_flags.items():
        if name in lean and lean[name] is not derived:
            reasons.append(f"stored qualification disagrees with compiler record: {name}")

    if lean.get("allowed_lean_axioms") != sorted(ALLOWED_LEAN_AXIOMS):
        reasons.append("allowed Lean axiom set is missing or unexpected")
    if lean.get("theorem_mode_enabled") is not False:
        reasons.append("theorem-mode status is missing or inconsistent")
    return {"fresh": not reasons, "reasons": reasons,
            "derived_flags": {} if reasons else derived_flags,
            "derived_reports": {} if reasons else derived_reports,
            "expected_modules": len(expected_order),
            "observed_modules": len(results),
            "freshness_is_authentication": False}


def lean_flag(lean, freshness, name: str) -> bool:
    return bool(freshness.get("fresh") and isinstance(lean, dict) and
                freshness.get("derived_flags", {}).get(name) is True)


def lean_theorem_reported(lean, freshness, file: str, theorem: str) -> bool:
    if not freshness.get("fresh") or not isinstance(lean, dict):
        return False
    return theorem in freshness.get("derived_reports", {}).get(file, ())


def fixture_record(backend: str):
    try:
        built = construct_streaming_d3_packing(
            FIXTURE_EDGES, r=2, a=1, max_work=None,
            max_candidate_evaluations=10 ** 6, score_backend=backend)
    except (cpp_backend.CppBackendUnavailable, OSError) as exc:
        return {"backend": backend, "status": "UNAVAILABLE", "reason": str(exc)}
    certificate = built.certificate
    replay = verify_streaming_d3_certificate(certificate)
    observed = {
        "vertices": [[side, ident] for side, ident in
                     (("R", 0), ("R", 1), ("C", 0), ("C", 1))],
        "labels": [step["label"] for step in certificate["steps"]],
        "scores": [step["expected_square_scaled"] for step in certificate["steps"]],
        "final": certificate["final_square_scaled"],
    }
    return {
        "backend": backend,
        "status": "PASS" if observed == FIXTURE_EXPECTED and replay.get("valid") else "FAIL",
        "observed": observed,
        "expected": FIXTURE_EXPECTED,
        "initial": certificate["initial_expected_square_scaled"],
        "work_units": certificate["work_units"],
        "work_metric_version": replay.get("work_metric_version"),
        "independent_replay": replay,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/r91_release_evidence.json")
    args = parser.parse_args()

    lean = load(ROOT / "validation/r9_conditional_expectation_proof.json")
    model = load(ROOT / "validation/r91_python_model.json")
    benches = load(ROOT / "validation/r91_benchmarks.json")
    differential = load(ROOT / "validation/r9_1_differential.json")
    packing = load(ROOT / "validation/r9_streaming_packing.json")

    self_test = None
    binary = ROOT / "build" / "cpp" / "veritas_d3_selftest"
    if binary.is_file():
        run = subprocess.run([str(binary)], text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        self_test = {"return_code": run.returncode, "output": run.stdout.strip(),
                     "status": "PASS" if run.returncode == 0 else "FAIL"}
    else:
        self_test = {"status": "NOT_BUILT"}

    lean_freshness = check_lean_evidence_freshness(lean)
    lean_pass = lean_freshness["fresh"]
    model_pass = bool(model and model.get("all_equal"))
    bench_pass = bool(benches and benches.get("all_scores_exact") is True and
                      benches.get("all_direct_work_metrics_match") is True)
    differential_pass = bool(
        differential and differential.get("status") == "PASS_FINITE_CPP_DIFFERENTIAL" and
        differential.get("candidate_score_cases", 0) >= 1 and
        differential.get("independent_certificate_replays", 0) ==
        len(differential.get("fixtures", [])) and differential.get("large_integer_exact") is True)
    cpp_available = bool(bench_pass and differential_pass and
                         benches.get("environment", {}).get("native_backend"))

    fixtures = [fixture_record("python")]
    for backend in ("cpp", "auto"):
        fixtures.append(fixture_record(backend))
    fixture_pass = all(item["status"] == "PASS" for item in fixtures)

    evidence = {
        "schema": "VERITAS_ETH_R91_RELEASE_EVIDENCE_V2",
        "release": "R9.1",
        "theorem_mode_enabled": False,
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "manuscript_sha256": sha256(ROOT / "paper/quantitative-contraction.tex"),
        "lean_toolchain": (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip(),
        "source_hashes": {
            name: sha256(ROOT / name)
            for name in (
                "proofs/D3PythonOrder.lean",
                "proofs/D3PythonScoreModel.lean",
                "proofs/D3PacketBijection.lean",
                "src/veritas/research/eth_packing_v26/streaming.py",
                "src/veritas/research/eth_packing_v26/cpp_backend.py",
                "cpp/src/score.cpp",
                "cpp/src/bindings.cpp",
                "cpp/include/veritas_d3_score.h",
            )
        },
        "gates": {
            "lean_proof_gate": {
                "status": ("PASS_HASH_MATCH_UNAUTHENTICATED" if lean_pass else
                           "STALE_OR_MISMATCH" if lean and lean.get("status") == "PASS" else
                           "FAIL_OR_MISSING"),
                "modules": len(lean.get("results", [])) if lean else 0,
                "source": "validation/r9_conditional_expectation_proof.json",
                "freshness": lean_freshness,
            },
            "lean_python_model_differential": {
                "status": "PASS" if model_pass else "FAIL_OR_MISSING",
                "cases": model.get("cases") if model else 0,
                "mismatches": model.get("mismatches") if model else None,
                "source": "validation/r91_python_model.json",
            },
            "cpp_selftest": self_test,
            "cpp_benchmarks": {
                "status": "PASS" if bench_pass else "FAIL_OR_MISSING",
                "instances": len(benches.get("records", [])) if benches else 0,
                "all_direct_work_metrics_match": (
                    benches.get("all_direct_work_metrics_match") is True if benches else False),
                "source": "validation/r91_benchmarks.json",
            },
            "cpp_differential_and_independent_replay": {
                "status": "PASS" if differential_pass else "FAIL_OR_MISSING",
                "candidate_score_cases": differential.get("candidate_score_cases", 0)
                if differential else 0,
                "certificate_replays": differential.get("independent_certificate_replays", 0)
                if differential else 0,
                "large_integer_exact": differential.get("large_integer_exact", False)
                if differential else False,
                "source": "validation/r9_1_differential.json",
            },
            "ordering_fixture": {
                "status": "PASS" if fixture_pass else "FAIL",
                "records": fixtures,
            },
            "finite_packing_replay": {
                "status": "PRESENT" if packing else "MISSING",
                "source": "validation/r9_streaming_packing.json",
            },
        },
        # Theorems about Lean definitions. These do not establish correspondence
        # between those definitions and arbitrary Python/C++ executables.
        "formal": {
            "lean_model_sorted_vertex_order_proven": lean_flag(
                lean, lean_freshness, "lean_python_sorted_vertex_order_model_proven"),
            "lean_model_sorted_order_port_bound_proven": lean_flag(
                lean, lean_freshness, "lean_python_sorted_order_port_bound_proven"),
            "lean_model_ordering_fixture_kernel_checked": lean_flag(
                lean, lean_freshness, "lean_python_sorted_trace_fixture_proven"),
            "lean_candidate_score_transcription_compiles": lean_flag(
                lean, lean_freshness, "lean_python_score_transcription_compiles"),
            "lean_model_per_comparison_equivalence_proven": lean_theorem_reported(
                lean, lean_freshness, "proofs/D3PythonScoreModel.lean",
                "D3PythonScore.pyPairTerm_eq"),
            "lean_model_pair_aggregation_proven": lean_flag(
                lean, lean_freshness, "lean_python_pair_aggregation_proven"),
            "lean_model_word_matches_bridge_proven": lean_flag(
                lean, lean_freshness, "lean_python_word_matches_bridge_proven"),
            "lean_model_candidate_score_identity_proven": lean_flag(
                lean, lean_freshness, "lean_python_score_equality_proven"),
            "lean_model_full_run_correspondence_proven": all(lean_flag(
                lean, lean_freshness, name) for name in (
                    "lean_candidate_product_and_lex_order_model_proven",
                    "lean_keyed_full_run_and_trace_model_proven", "lean_r94_contracts_checked")),
            "lean_finite_packet_domain_cardinality_model_proven": all(lean_flag(
                lean, lean_freshness, name) for name in (
                    "lean_finite_packet_domain_cardinality_model_proven", "lean_r94_contracts_checked")),
            "python_to_lean_source_refinement_proven": False,
            "cpp_to_lean_source_refinement_proven": False,
            "lean_packet_slot_bijection_proven": lean_flag(
                lean, lean_freshness, "lean_packet_slot_bijection_proven"),
            "lean_occurrence_rank_model_bijection_proven": lean_flag(
                lean, lean_freshness, "lean_occurrence_rank_model_bijection_proven"),
            "lean_binary_slot_model_proven": lean_flag(
                lean, lean_freshness, "lean_binary_slot_model_proven"),
            "lean_numeric_slot_model_bijection_proven": lean_flag(
                lean, lean_freshness, "lean_numeric_slot_model_bijection_proven"),
            "lean_global_edge_occurrence_model_bijection_proven": lean_flag(
                lean, lean_freshness, "lean_global_edge_occurrence_model_bijection_proven"),
            "lean_padded_packet_model_bounds_proven": lean_flag(
                lean, lean_freshness, "lean_padded_packet_model_bounds_proven"),
            "lean_first_minimum_model_proven": lean_flag(
                lean, lean_freshness, "lean_first_minimum_model_proven"),
            "lean_computed_padding_model_proven": lean_flag(
                lean, lean_freshness, "lean_computed_padding_model_proven"),
            "lean_r93_contracts_checked": lean_flag(
                lean, lean_freshness, "lean_r93_contracts_checked"),
            "lean_full_padded_offset_to_global_address_proven": lean_flag(
                lean, lean_freshness, "lean_full_padded_offset_to_global_address_proven"),
            "recursive_child_correctness_proven": False,
            "complexity_bound_proven": False,
        },
        # Executable facts.  These are tested, not proved.
        "executable": {
            "cpp_backend_available": cpp_available,
            "cpp_matches_python_on_benchmark_corpus": bench_pass,
            "lean_transcription_matches_cpython_on_corpus": model_pass,
            "cpp_is_formally_verified": False,
        },
        "open_obligations": [
            "Python source correspondence, candidate enumeration equality, and full-run simulation (Lean first-minimum model proved)",
            "C++ source/ABI to Lean model correspondence or verified extraction",
            "Source-to-model correspondence for executable edge-to-class assignment and packet mapping",
            "Stage 2B recursive child correctness",
            "Stage 2C complexity bound",
        ],
        "status": ("PASS_R91_FINITE_AND_FORMAL_MODEL_GATES" if
                   (lean_pass and model_pass and bench_pass and fixture_pass and
                    differential_pass and self_test.get("status") == "PASS")
                   else "FAIL_OR_INCOMPLETE"),
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}", file=sys.stderr)
    return 0 if (lean_pass and model_pass and bench_pass and differential_pass and fixture_pass and
                 self_test.get("status") == "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
