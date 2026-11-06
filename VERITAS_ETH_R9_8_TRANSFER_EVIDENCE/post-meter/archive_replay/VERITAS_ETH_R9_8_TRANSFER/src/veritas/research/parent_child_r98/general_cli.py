"""Run complete-grid finite shrinking recursion, with external evidence output."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .general_engine import contract_general_shrinking
from .model import canonical
from .shrinking_cli import load_input, _check_output
from .shrinking_engine import DEFAULT_SHRINKING_POLICY


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-points", type=int, default=256)
    parser.add_argument("--groups", type=int, default=64,
                        help="fixed finite group count, 64..1024; source schedule remains 64")
    for name in ("work", "seconds", "calls", "edges", "precision"):
        parser.add_argument("--max-" + name, type=int,
                            default=getattr(DEFAULT_SHRINKING_POLICY, "max_" + name))
    args = parser.parse_args(argv)
    output_allowed = False
    try:
        _check_output(args.output)
        output_allowed = True
        parent = load_input(args.input, max_extension_degree=12)
        policy = replace(DEFAULT_SHRINKING_POLICY, **{
            "max_" + name: getattr(args, "max_" + name)
            for name in ("work", "seconds", "calls", "edges", "precision")
        })
        report = contract_general_shrinking(parent, policy=policy, max_points=args.max_points,
                                            groups=args.groups)
    except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, OSError) as exc:
        report = {"status": getattr(exc, "status", "INVALID_GENERAL_SHRINKING_CALL"),
                  "reason": str(exc), "source_qualified": False, "theorem_mode_enabled": False}
    if output_allowed:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical(report))
    print(json.dumps({"status": report["status"], "reason": report.get("reason"),
                      "output": str(args.output) if output_allowed else None,
                      "actual_calls": report.get("ledger", {}).get("actual_calls")}))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
