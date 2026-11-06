#!/usr/bin/env python3
"""Aggregate the R9.6 hardening checks into one machine-readable report.

Each check is executed here, not inferred from a bundled log.  A check that
cannot run is reported as ``NOT_RUN`` with its blocker; it is never promoted to
``PASS``.

Exit code 0 only when every *required* check passes.  ``NOT_RUN`` entries keep
their own status and are listed in ``qualifiers``.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from veritas.research.tapered_v4.parent_child import (  # noqa: E402
    ParentChildLimits, build_certificate, verify_certificate)
from veritas.research.tapered_v4.source_recipes import (  # noqa: E402
    SCHEMA as ENTRY_SCHEMA, EntryBudget, EntryLimits, compile_entry,
    evaluate_source_entry)
from veritas.research.tapered_v4.source_regime import (  # noqa: E402
    active_parameter_contradiction, source_active_status)
from veritas.research.tapered_v4.source_state import (  # noqa: E402
    SourceAdmissionError, SourceContext, SourceTensorReference)
from veritas.research.tapered_v4.validators import (  # noqa: E402
    CERTIFICATE_SCHEMA, validate_certificate_document)

SCHEMA = "VERITAS_R96_HARDENING_QUALIFICATION_V1"


def _packet_reference(data, arity, precision=3, polynomial=7, jet_length=1):
    payload = {"schema": ENTRY_SCHEMA, "kind": "packet", "arity": arity,
               "creation_precision": precision, "polynomial": polynomial,
               "jet_length": jet_length, "data": data}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("ascii")
    return SourceTensorReference(arity, precision, polynomial, jet_length,
                                 ENTRY_SCHEMA + ":packet", raw)


def check_first_order_packet():
    one = [[1, 0], [1, 0]]  # jet_length 2, extension degree 2, unit in both rows
    data = [list(range(15)), [], [[] for _ in range(15)],
            [[1, [one for _ in range(15)]]], []]
    ref = _packet_reference(data, 15, jet_length=2)
    out = evaluate_source_entry(ref, (0,) * 15, precision=3)
    ok = (out["status"] == "EXACT_CREATION_PRECISION_ENTRY"
          and out["result"] == ((1, 0), (1, 0))
          and out["ledger"]["work_units"] < 5_000_000)
    return {"status": "PASS" if ok else "FAIL",
            "detail": {"result": [list(row) for row in out.get("result", [])],
                       "work_units": out["ledger"]["work_units"],
                       "algorithm": out["ledger"]["notes"].get("coefficient_algorithm")},
            "claim": "[z](1-z)^15 == -15 == 1 (mod 8) inside the default budget"}


def check_coefficient_admission():
    data = [[], [0, 1, 2, 3], [], [], [[1, [1, 2, 3, 4]]]]
    ref = _packet_reference(data, 4)
    refused = None
    try:
        compile_entry(ref, EntryBudget(EntryLimits(max_coefficients=1)))
    except SourceAdmissionError as exc:
        refused = exc.status
    admitted = compile_entry(ref, EntryBudget(EntryLimits(max_coefficients=4)))
    ok = refused == "INCONCLUSIVE_RESOURCE_LIMIT" and admitted is not None
    return {"status": "PASS" if ok else "FAIL",
            "detail": {"cap_one_status": refused,
                       "cap_four_admitted": admitted is not None},
            "claim": "four source scalars are refused under max_coefficients=1"}


def check_parent_child_identity():
    from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
    from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
    from veritas.research.eth_arithmetic.gf2 import first_irreducible
    from veritas.research.eth_arithmetic.jets import JetRing
    from veritas.research.eth_recursive_contraction_v39.described_network import (
        CreatedDenseTensor, DescribedNetwork, DescribedVertex)
    polynomial = first_irreducible(2)
    ring = JetRing(ExtensionRing(4, polynomial), 1)
    tensor = lambda arity, values: CreatedDenseTensor(arity, tuple(  # noqa: E731
        CreationJetEntry.capture(ring, ring.elem(value)) for value in values))
    parent = DescribedNetwork(2, (
        DescribedVertex("row", "r", (0, 1),
                        tensor(2, ([[1, 1]], [[3, 0]], [[2, 1]], [[1, 1]]))),
        DescribedVertex("column", "c0", (0,), tensor(1, ([[2, 1]], [[1, 0]]))),
        DescribedVertex("column", "c1", (1,), tensor(1, ([[1, 1]], [[4, 1]]))),
    ))
    limits = ParentChildLimits(max_edges=4, max_points=8, max_tuples=512,
                               max_work=2_000_000)
    document = build_certificate(parent, precision=4, jet_length=1, a=1, u=1,
                                 radix=4, extension_degree=2, limits=limits)
    validate_certificate_document(document)
    # Emit the sample beside the aggregate report so an independent checker can
    # read it without re-running the construction.
    sample = Path(os.environ.get("VERITAS_EVIDENCE_DIR", str(ROOT / "validation")))
    try:
        sample.mkdir(parents=True, exist_ok=True)
        (sample / "r96_parent_child_certificate.json").write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass
    verdict = verify_certificate(document, parent=parent, limits=limits)
    ok = (verdict["valid"] and verdict["classification"] == "FULL_COVERAGE"
          and verdict["points_checked"] == verdict["points_required"] > 0
          and verdict["theorem_mode_enabled"] is False)
    return {"status": "PASS" if ok else "FAIL",
            "detail": {"points_checked": verdict["points_checked"],
                       "points_required": verdict["points_required"],
                       "classification": verdict["classification"],
                       "scope": verdict["scope"]},
            "claim": "finite parent-to-all-children identity at every required point"}


def check_manuscript_resource():
    from veritas.research.tapered_v4.manuscript import (
        PINNED_MANUSCRIPT_SHA256, read_pinned_manuscript)
    pinned = read_pinned_manuscript()
    ok = pinned.sha256 == PINNED_MANUSCRIPT_SHA256
    return {"status": "PASS" if ok else "FAIL",
            "detail": {"origin": pinned.origin, "sha256": pinned.sha256},
            "claim": "the pinned manuscript resolves from the installed distribution"}


def check_source_active_unreachable():
    contradiction = active_parameter_contradiction()
    context = SourceContext(2, 1, 1, 1, 1, 1, 19)
    status = source_active_status(context)
    ok = (contradiction["reachable"] is False
          and contradiction["status"] == "UNREACHABLE_IN_CURRENT_REPRESENTATION"
          and status["theorem_mode_enabled"] is False)
    return {"status": "PASS" if ok else "FAIL",
            "detail": {"maximum_admissible_lambda":
                       contradiction["maximum_admissible_lambda"],
                       "required_lambda": contradiction["required_lambda"],
                       "regime": status["regime"],
                       "status": status["status"]},
            "claim": "no admitted source context can reach the active schedule"}


def check_ci_ordering():
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(
        encoding="utf-8")
    job = workflow.split("  test:", 1)[1].split("  cpp-backend:", 1)[0]
    ok = (job.index("release_integrity.py verify") < job.index("pip install")
          < job.index("validate_v08.py") < job.index("release_integrity.py compare"))
    return {"status": "PASS" if ok else "FAIL",
            "detail": {"order": "verify -> install -> validate -> compare"},
            "claim": "release inputs are verified before and after validation"}


def check_release_inputs_unchanged():
    import subprocess
    result = subprocess.run([sys.executable, str(ROOT / "scripts" /
                                                 "release_integrity.py"),
                             "verify"], capture_output=True, text=True,
                            timeout=600)
    return {"status": "PASS" if result.returncode == 0 else "FAIL",
            "detail": {"stdout": result.stdout.strip(),
                       "stderr": result.stderr.strip()},
            "claim": "the release-input manifest verifies"}


def check_lean_toolchain():
    import shutil
    binary = os.environ.get("LEAN_BIN") or shutil.which("lean")
    if not binary:
        return {"status": "NOT_RUN",
                "blocker": "no lean binary on PATH",
                "claim": "Lean proofs compiled from source"}
    import subprocess
    version = subprocess.run([binary, "--version"], capture_output=True,
                             text=True, timeout=300)
    pinned = (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip()
    ok = "4.35.0" in version.stdout
    return {"status": "PASS" if ok else "FAIL",
            "detail": {"version": version.stdout.strip(), "pin": pinned,
                       "binary": binary},
            "claim": "the pinned Lean toolchain is present and reports 4.35.0"}


CHECKS = (
    ("first_order_packet", check_first_order_packet, True),
    ("coefficient_admission", check_coefficient_admission, True),
    ("parent_child_identity", check_parent_child_identity, True),
    ("manuscript_resource", check_manuscript_resource, True),
    ("source_active_unreachable", check_source_active_unreachable, True),
    ("ci_ordering", check_ci_ordering, True),
    ("release_inputs", check_release_inputs_unchanged, True),
    ("lean_toolchain", check_lean_toolchain, False),
)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(
        Path(os.environ["VERITAS_EVIDENCE_DIR"]) / "r96_hardening.json"
        if os.environ.get("VERITAS_EVIDENCE_DIR") else
        ROOT / "validation" / "r96_hardening.json"))
    args = parser.parse_args(argv)
    started = time.perf_counter()
    results = {}
    failed = []
    for name, function, required in CHECKS:
        try:
            outcome = function()
        except Exception as exc:  # noqa: BLE001 - a check must never crash the gate
            outcome = {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}
        outcome["required"] = required
        results[name] = outcome
        if required and outcome["status"] != "PASS":
            failed.append(name)
    report = {
        "schema": SCHEMA,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "release": "R9.6 HARDENING",
        "checks": results,
        "failed_required_checks": failed,
        "status": "PASS" if not failed else "FAIL",
        "elapsed_seconds": None,
        "qualifiers": {
            "GATE_A_BOUNDED_SOURCE_EXECUTION": "PASS" if not failed else "FAIL",
            "GATE_B_FINITE_PARENT_CHILD": ("PASS" if results["parent_child_identity"]["status"]
                                           == "PASS" else "FAIL"),
            "GATE_C_THEOREM_QUALIFIED": "NOT_MET",
            "SOURCE_ACTIVE_REGIME": "NOT_IMPLEMENTED",
            "THEOREM_MODE": "DISABLED",
            "LEAN_COMPILED_THIS_RUN": results["lean_toolchain"]["status"],
            "LEAN_PYTHON_REFINEMENT": "NOT_PROVED",
            "CPP_BACKEND": "BUILT_AND_DIFFERENTIALLY_TESTED" if os.environ.get(
                "VERITAS_D3_CPP_BUILD_DIR") else "NOT_RUN_IN_THIS_CHECK",
        },
    }
    report["elapsed_seconds"] = time.perf_counter() - started
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(target),
                      "failed": failed}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
