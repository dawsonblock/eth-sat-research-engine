"""Run or replay an explicitly bounded finite DIMACS model count."""

import argparse
import json
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from .boundary import BoundaryPolicy, contract_boundary, replay_boundary


def _read(path, maximum):
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("input exceeds byte limit")
    return raw.decode("utf-8")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate certificate field")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dimacs", type=Path)
    parser.add_argument("--leaf-edges", type=int, default=8)
    parser.add_argument(
        "--piece-method", choices=("direct", "tapered"), default="direct"
    )
    parser.add_argument("--on-call-overflow", choices=("refuse", "certified_elimination"), default="refuse")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", type=Path)
    group.add_argument("--replay", type=Path)
    args = parser.parse_args()
    try:
        formula = CNF.from_dimacs(_read(args.dimacs, 65_536))
        if (
            formula.n > 64
            or sum(map(len, formula.clauses)) > 16
            or len(formula.clauses) > 64
        ):
            raise ValueError("finite input exceeds variable, wire or factor limits")
        network = from_cnf(formula, max_degree=16)
        p = formula.n + 1
        policy = BoundaryPolicy(
            leaf_edges=args.leaf_edges, piece_method=args.piece_method, on_call_overflow=args.on_call_overflow
        )
        if args.replay:
            cert = json.loads(
                _read(args.replay, policy.max_certificate_bytes),
                object_pairs_hook=_unique,
            )
            out = replay_boundary(network, cert, precision=p, policy=policy)
            print(json.dumps(out))
            return 0 if out["valid"] else 1
        out = contract_boundary(network, precision=p, policy=policy)
        cert = out.pop("certificate", None)
        if cert is not None:
            if args.write:
                args.write.write_text(
                    json.dumps(cert, separators=(",", ":")), encoding="utf-8"
                )
            out["model_count"] = out["result"]
        print(json.dumps(out))
        return 0 if cert is not None else 1
    except (ValueError, OSError, RecursionError) as exc:
        print(
            json.dumps({"status": "INCONCLUSIVE_INPUT_OR_IO_ERROR", "reason": str(exc)})
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
