"""Generate or verify the fixed R9.7 64-group finite grid from external fixture parameters."""

import json
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from veritas.core.cnf import CNF
from veritas.research.paper_verification.evidence_report import grid_certificate
from veritas.research.finite_reductions.__main__ import _unique, _read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", type=Path)
    group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    try:
        submitted = (
            json.loads(_read(args.verify, 32_000_000), object_pairs_hook=_unique)
            if args.verify
            else None
        )
        if args.verify and type(submitted) is not dict:
            raise ValueError("invalid grid object")
        record, verdict = grid_certificate(
            CNF.from_lists(2, [[1, 2], [-1, 2]]),
            s=16,
            r=64,
            a=2,
            u=1,
            submitted=submitted,
        )
        if args.write:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(
                json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
            )
        print(json.dumps(verdict))
        return 0
    except (
        OSError,
        RuntimeError,
        ArithmeticError,
        MemoryError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
    ) as exc:
        print(
            json.dumps({"status": "INCONCLUSIVE_OR_INVALID_GRID", "reason": str(exc)})
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
