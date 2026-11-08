"""External CLI for bounded scaled recursion and independently checked points.

Input tables use the legacy little-endian port convention. The explicit
DescribedNetwork adapter converts them to the lexicographic recipe convention.
"""

import argparse
import json
from pathlib import Path

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.tensor import Factor, TensorNetwork

from .engine import contract_scaled, evaluate_point, verify_point_certificate
from .model import (
    Budget,
    PointEvaluationCertificate,
    Policy,
    canonical,
    digest,
    from_described,
)
from .modes import build_modes
from .packing import construct_layout, preconditions


def load_input(path):
    if path.stat().st_size > 2_000_000:
        raise ValueError("input byte cap")

    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError("duplicate input field")
            obj[k] = v
        return obj

    data = json.loads(path.read_text(), object_pairs_hook=unique)
    if set(data) != {"root_s", "precision", "extension_degree", "edges", "vertices"}:
        raise ValueError("input fields")
    if type(data["edges"]) is not int or not 0 < data["edges"] <= 8:
        raise ValueError("bounded scaled input supports 1..8 edges")
    if (
        type(data["extension_degree"]) is not int
        or not 2 <= data["extension_degree"] <= 8
    ):
        raise ValueError("scaled extension degree must be 2..8")
    factors = []
    for i, v in enumerate(data["vertices"]):
        if set(v) != {"side", "ports", "table"} or v["side"] not in ("row", "column"):
            raise ValueError("vertex fields")
        if (
            len(v["ports"]) > 16
            or len(v["table"]) != 1 << len(v["ports"])
            or any(type(x) is not int or x.bit_length() > 1024 for x in v["table"])
        ):
            raise ValueError("invalid bounded integer table")
        label = ("row:" if v["side"] == "row" else "col:") + str(i)
        factors.append(Factor(tuple(v["ports"]), tuple(v["table"]), label))
    described = describe_integer_network(
        TensorNetwork(data["edges"], tuple(factors)),
        creation_precision=data["precision"],
        defining_polynomial=first_irreducible(data["extension_degree"]),
    )
    return from_described(described, root_s=data["root_s"], precision=data["precision"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("scaled", "point", "verify-point", "source-preflight")
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--strategy", choices=("canonical", "scaled_singletons"), default="canonical"
    )
    parser.add_argument("--a", type=int, default=2)
    parser.add_argument("--u", type=int, default=1)
    parser.add_argument("--levels", type=int, default=1)
    parser.add_argument("--node", type=int, default=-1)
    parser.add_argument(
        "--zeta", default=None, help="JSON list of extension coordinates"
    )
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-work", type=int, default=100_000_000)
    parser.add_argument("--max-seconds", type=int, default=300)
    parser.add_argument("--max-tuples", type=int, default=4096)
    args = parser.parse_args()
    try:
        parent = load_input(args.input)
        policy = Policy(
            max_work=args.max_work,
            max_seconds=args.max_seconds,
            max_tuples=args.max_tuples,
        )
        if args.command == "source-preflight":
            report = preconditions(parent)
            report.update(source_qualified=False, theorem_mode_enabled=False)
        elif args.command == "scaled":
            report = contract_scaled(
                parent,
                levels=args.levels,
                a=args.a,
                u=args.u,
                strategy=args.strategy,
                policy=policy,
            )
        else:
            if args.certificate is None:
                raise ValueError("--certificate is required")
            budget = Budget(policy)
            layout = construct_layout(
                parent, a=args.a, u=args.u, strategy=args.strategy, budget=budget
            )
            zeta = (
                tuple(json.loads(args.zeta))
                if args.zeta
                else (0,) * (parent.defining_polynomial.bit_length() - 1)
            )
            modes = build_modes(parent, layout, args.node, zeta, budget=budget)
            if args.command == "point":
                _, cert, report = evaluate_point(
                    parent, layout, modes, budget=budget, capture=True
                )
                envelope = {
                    "sha256": cert.content_digest,
                    "certificate": json.loads(cert.payload),
                }
                args.certificate.parent.mkdir(parents=True, exist_ok=True)
                args.certificate.write_bytes(canonical(envelope))
            else:
                if args.certificate.stat().st_size > policy.max_certificate_bytes:
                    raise ValueError("certificate byte cap")
                from .model import decode

                envelope = decode(
                    args.certificate.read_bytes(), cap=policy.max_certificate_bytes
                )
                if (
                    set(envelope) != {"sha256", "certificate"}
                    or digest(envelope["certificate"]) != envelope["sha256"]
                ):
                    raise ValueError("stored certificate digest mismatch")
                cert = PointEvaluationCertificate(canonical(envelope["certificate"]))
                report = verify_point_certificate(
                    parent, layout, modes, cert, policy=policy
                )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, sort_keys=True))
        return 0 if report["status"].startswith("PASS_") else 1
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        ArithmeticError,
        RuntimeError,
        MemoryError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": getattr(exc, "status", "INVALID_OR_INCONCLUSIVE_R98"),
                    "reason": str(exc),
                    "source_qualified": False,
                }
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
