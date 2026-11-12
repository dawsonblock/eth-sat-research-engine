#!/usr/bin/env python3
"""CLI for reduction-first universal SAT research (E1).

Example::

    PYTHONPATH=src python scripts/sat_universal_cli.py --mode decision /tmp/tiny.cnf
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.sat_phase_c_reduction import PhaseCBounds
from veritas.research.sat_micro_benchmark import run_micro_benchmark_suite
from veritas.research.sat_universal import (
    INTERACTION_96_CERT,
    BoundedInteractionCertificate,
    run_universal_sat,
)


def _load_cnf(path: Path) -> CNF:
    text = path.read_text(encoding="utf-8", errors="replace")
    return CNF.from_dimacs(text)


def _parse_cert(name: str | None) -> BoundedInteractionCertificate | None:
    if not name:
        return None
    if name in ("interaction_96", INTERACTION_96_CERT.fixture_id):
        return INTERACTION_96_CERT
    raise ValueError(f"unknown interaction certificate id: {name!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VERITAS universal SAT (reduction first, jet fast path last)"
    )
    parser.add_argument(
        "cnf",
        type=Path,
        nargs="?",
        help="DIMACS CNF path (omit with --micro-suite)",
    )
    parser.add_argument(
        "--micro-suite",
        action="store_true",
        help="Run pinned count-mode micro-benchmark suite (ledger_totals per case)",
    )
    parser.add_argument(
        "--mode",
        choices=("decision", "count"),
        default="decision",
        help="decision = SAT/UNSAT; count = exact #SAT when budget allows",
    )
    parser.add_argument("--max-wires", type=int, default=50_000)
    parser.add_argument("--max-factors", type=int, default=100_000)
    parser.add_argument("--timeout-s", type=float, default=8.0)
    parser.add_argument("--adaptive-timeout-s", type=float, default=15.0)
    parser.add_argument(
        "--interaction-cert",
        metavar="ID",
        help="Optional E4 certificate (e.g. interaction_96); diagnostic only today",
    )
    parser.add_argument(
        "--fail-on-reduction",
        action="store_true",
        help="Exit 2 if fixed-density encode or structural check fails",
    )
    parser.add_argument(
        "--baseline-matrix",
        action="store_true",
        help="Attach E2 baseline matrix (reference + optional Kissat/CaDiCaL)",
    )
    parser.add_argument(
        "--max-vars",
        type=int,
        default=64,
        help="Phase C scaffold max variables",
    )
    parser.add_argument(
        "--max-clauses",
        type=int,
        default=256,
        help="Phase C scaffold max clauses",
    )
    args = parser.parse_args(argv)

    if args.micro_suite:
        report = run_micro_benchmark_suite(
            include_baseline_matrix=args.baseline_matrix,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report.get("all_cross_checks_agree") else 2

    if args.cnf is None:
        print(
            json.dumps(
                {
                    "schema": "VERITAS_SAT_UNIVERSAL_RUN_V1",
                    "status": "REFUSED",
                    "reason": "cnf path required unless --micro-suite",
                }
            ),
            file=sys.stderr,
        )
        return 1

    try:
        cnf = _load_cnf(args.cnf)
        cert = _parse_cert(args.interaction_cert)
        report = run_universal_sat(
            cnf,
            args.mode,
            max_wires=args.max_wires,
            max_factors=args.max_factors,
            timeout_s=args.timeout_s,
            adaptive_timeout_s=args.adaptive_timeout_s,
            interaction_cert=cert,
            phase_c_bounds=PhaseCBounds(
                max_vars=args.max_vars,
                max_clauses=args.max_clauses,
            ),
            include_baseline_matrix=args.baseline_matrix,
        )
    except (ValueError, OSError) as exc:
        print(json.dumps({"schema": "VERITAS_SAT_UNIVERSAL_RUN_V1", "status": "REFUSED", "reason": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_on_reduction:
        red = report.get("reduction") or {}
        enc = red.get("encode") or {}
        chk = red.get("structural_check") or {}
        if enc.get("status") in ("REFUSED_ENCODE", "STRUCTURE_CHECK_FAILED"):
            return 2
        if chk and not chk.get("valid"):
            return 2
    res = report.get("result") or {}
    if res.get("status") in ("UNKNOWN",) or (
        args.mode == "decision" and res.get("status") not in ("SAT", "UNSAT")
    ):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
