#!/usr/bin/env python3
"""E2 pinned SAT baseline matrix for DIMACS inputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.sat_external_baselines import run_baseline_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VERITAS SAT baseline matrix (E2)")
    parser.add_argument("cnf", type=Path)
    parser.add_argument("--task", choices=("decision", "count"), default="decision")
    parser.add_argument("--no-external", action="store_true")
    parser.add_argument("--external-timeout-s", type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        cnf = CNF.from_dimacs(args.cnf.read_text(encoding="utf-8", errors="replace"))
        report = run_baseline_matrix(
            cnf,
            task=args.task,
            include_external=not args.no_external,
            external_timeout_s=args.external_timeout_s,
        )
    except (ValueError, OSError) as exc:
        print(json.dumps({"schema": "VERITAS_SAT_BASELINE_MATRIX_V1", "status": "REFUSED", "reason": str(exc)}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
