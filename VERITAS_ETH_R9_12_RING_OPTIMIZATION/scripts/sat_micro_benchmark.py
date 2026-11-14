#!/usr/bin/env python3
"""Emit JSON micro-benchmark for universal count mode + ledgers."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from veritas.research.sat_micro_benchmark import run_micro_benchmark_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write JSON artifact (default stdout)",
    )
    parser.add_argument(
        "--baseline-matrix",
        action="store_true",
        help="Include E2 baseline matrix per case (slower)",
    )
    args = parser.parse_args(argv)
    report = run_micro_benchmark_suite(include_baseline_matrix=args.baseline_matrix)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if not report.get("all_cross_checks_agree"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
