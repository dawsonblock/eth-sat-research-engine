#!/usr/bin/env python3
"""Independent adversarial checker for the R9.6 evidence bundle.

Deliberately shares **no arithmetic** with the production package: it
re-implements the packet coefficient extraction with plain Python integers and
a hand-written polynomial expansion, then compares against the values recorded
in the delivered evidence and recomputes them from scratch.

Run::

    python adversarial/check_r96_independently.py --evidence <dir>

Exit 0 only when every independently recomputed value matches and every
tampered fixture is rejected.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FAILURES: list[str] = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILURES.append(name)


# ---------------------------------------------------------------------------
# Independent polynomial arithmetic: no import from veritas.
# ---------------------------------------------------------------------------

def poly_mul(left, right, modulus):
    """Multiply two integer coefficient lists modulo ``modulus``."""
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        if not a:
            continue
        for j, b in enumerate(right):
            out[i + j] = (out[i + j] + a * b) % modulus
    return out


def first_order_coefficient(rows, modulus):
    """Coefficient of z in prod_i (1 - z) with ``rows`` factors, mod 2^p.

    Computed by expanding the polynomial one factor at a time, which is a
    completely different algorithm from the production product rule.
    """
    polynomial = [1]
    for _ in range(rows):
        polynomial = poly_mul(polynomial, [1, modulus - 1], modulus)
    return polynomial[1] if len(polynomial) > 1 else 0


def binomial_expansion(rows, modulus):
    """Independent closed form: coefficient of z in (1-z)^n is -n."""
    return (-rows) % modulus


def check_first_order_series():
    for rows in (0, 1, 2, 3, 5, 8, 15, 16, 31):
        modulus = 8
        expanded = first_order_coefficient(rows, modulus)
        closed = binomial_expansion(rows, modulus)
        check(f"first-order rows={rows} mod 8", expanded == closed,
              f"expanded={expanded} closed={closed}")


def check_evidence(path):
    if not path.is_file():
        check("evidence file present", False, str(path))
        return
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = report["packet_coefficients"]["rows"]
    for row in rows:
        value = row["result"][0][0]
        expected = binomial_expansion(row["rows"], 8)
        check(f"recorded result rows={row['rows']}", value == expected,
              f"recorded={value} independent={expected}")
        check(f"results agree rows={row['rows']}",
              row["results_agree"] is True)
    sat = report["sharp_sat"]
    for family in sat["families"]:
        for case in family["cases"]:
            if case["brute_force_count"] is None:
                continue
            check(f"sat {family['family']} n={case['variables']}",
                  case["count"] == case["brute_force_count"],
                  f"{case['count']} != {case['brute_force_count']}")
    identity = report["parent_child_identity"]
    check("parent-child full coverage",
          identity["points_checked"] == identity["points_required"] > 0)
    check("parent-child theorem mode disabled",
          identity["theorem_mode_enabled"] is False)


def check_certificate(certificate_path):
    if not certificate_path.is_file():
        check("certificate sample present", False, str(certificate_path))
        return
    document = json.loads(certificate_path.read_text(encoding="utf-8"))
    check("certificate schema", document["schema"] ==
          "VERITAS_PARENT_CHILD_CERTIFICATE_V1")
    coverage = document["coverage"]
    check("certificate coverage complete",
          coverage["points_checked"] == coverage["points_required"] > 0)
    for record in document["points"]:
        check(f"point identity node={record['node']} idx={record['point_index']}",
              record["parent_value"] == record["tuple_sum"])
    for entry in document["modes"]["domains"]:
        check(f"domain cardinality node={entry['node']} idx={entry['point_index']}",
              len(entry["ordered_tuples"]) == entry["cardinality"])
    check("certificate theorem mode disabled",
          document["theorem_scope"]["theorem_mode_enabled"] is False)


def check_refusals():
    """A fabricated success must be rejected by the delivered validator."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from veritas.research.tapered_v4.validators import (
        ValidationRefusal, validate_entry_document)
    fabricated = {"schema": "VERITAS_SOURCE_ENTRY_RESULT_V1",
                  "status": "INCONCLUSIVE_RESOURCE_LIMIT",
                  "result": [[1, 0]],
                  "creation_precision": 3, "evaluation_precision": 7,
                  "recipe_sha256": "a" * 64,
                  "ledger": {"work_units": 1, "counters": {}}}
    try:
        validate_entry_document(fabricated)
    except ValidationRefusal as exc:
        check("inconclusive-with-result is refused",
              exc.status.startswith("INVALID_"))
    else:
        check("inconclusive-with-result is refused", False, "accepted")
    promoted = dict(fabricated, status="EXACT_CREATION_PRECISION_ENTRY",
                    theorem_qualified=True)
    try:
        validate_entry_document(promoted)
    except ValidationRefusal:
        check("theorem promotion is refused", True)
    else:
        check("theorem promotion is refused", False, "accepted")


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args(argv)
    evidence = Path(args.evidence)
    print("== independent first-order series ==")
    check_first_order_series()
    print("== delivered benchmark evidence ==")
    check_evidence(evidence / "r96_benchmarks.json")
    print("== delivered certificate sample ==")
    check_certificate(evidence / "r96_parent_child_certificate.json")
    print("== fail-closed validators ==")
    check_refusals()
    print()
    if FAILURES:
        print(f"RESULT: FAIL ({len(FAILURES)} independent checks failed)")
        return 1
    print("RESULT: PASS (all independent checks agree)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
