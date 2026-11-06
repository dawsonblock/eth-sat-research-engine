"""External CLI for checked finite shrinking packet recursion.

Inputs retain the legacy little-endian port-table convention. The direct
adapter below explicitly converts it to lexicographic creation-time recipes.
The active executor accepts its certified row-constant family and refuses
unsupported tensors or component layouts; it does not qualify source recursion.
"""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.tapered_v4.provenance import source_binding
from veritas.research.tapered_v4.source_recipes import EntryLimits, make_reference
from veritas.research.tapered_v4.source_state import SourceVertex

from .model import ParentCall
from .shrinking_engine import DEFAULT_SHRINKING_POLICY, contract_shrinking


def load_input(path, *, max_extension_degree=8):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("shrinking input byte cap")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate input field")
            result[key] = value
        return result

    data = json.loads(path.read_text(), object_pairs_hook=unique)
    if type(data) is not dict or set(data) != {
        "root_s",
        "precision",
        "extension_degree",
        "edges",
        "vertices",
    }:
        raise ValueError("shrinking input fields")
    M, precision, degree = data["edges"], data["precision"], data["extension_degree"]
    if type(M) is not int or not 0 <= M <= 1024:
        raise ValueError("shrinking input supports 0..1024 edges")
    if type(precision) is not int or not 1 <= precision <= 1024:
        raise ValueError("integer input precision must be 1..1024")
    if type(max_extension_degree) is not int or not 2 <= max_extension_degree <= 12:
        raise ValueError("invalid input extension degree cap")
    if type(degree) is not int or not 2 <= degree <= max_extension_degree:
        raise ValueError(f"extension degree must be 2..{max_extension_degree}")
    if type(data["vertices"]) is not list or len(data["vertices"]) > 4096:
        raise ValueError("bounded input vertices required")
    f, modulus = first_irreducible(degree), 1 << precision
    sides, references = {"row": [], "column": []}, {}
    for vertex in data["vertices"]:
        if (
            type(vertex) is not dict
            or set(vertex) != {"side", "ports", "table"}
            or type(vertex["side"]) is not str
            or vertex["side"] not in sides
        ):
            raise ValueError("input vertex fields")
        ports, table = vertex["ports"], vertex["table"]
        if (
            type(ports) is not list
            or len(ports) > 16
            or any(type(edge) is not int or not 0 <= edge < M for edge in ports)
            or type(table) is not list
            or len(table) != 1 << len(ports)
            or any(
                type(value) is not int or value.bit_length() > 1024 for value in table
            )
        ):
            raise ValueError("invalid bounded integer tensor table or ports")
        key = len(ports), tuple(table)
        if key not in references:
            # A lexicographic index reads the first port as the most significant
            # bit. The input table reads that same port as the least significant.
            arity = len(ports)
            entries = []
            for lexicographic in range(1 << arity):
                little_endian = sum(
                    ((lexicographic >> (arity - 1 - k)) & 1) << k for k in range(arity)
                )
                entries.append([[table[little_endian] % modulus] + [0] * (degree - 1)])
            references[key] = make_reference(
                kind="dense",
                arity=arity,
                creation_precision=precision,
                defining_polynomial=f,
                jet_length=1,
                data=entries,
                limits=EntryLimits(max_precision_bits=precision),
            )
        side = vertex["side"]
        sides[side].append(
            SourceVertex(side, len(sides[side]), tuple(ports), references[key])
        )
    return ParentCall(
        data["root_s"],
        0,
        precision,
        f,
        M,
        tuple(sides["row"] + sides["column"]),
    )


def _check_output(path):
    if path is None:
        return
    root = Path(__file__).resolve().parents[4]
    if (
        (root / "src/veritas").is_dir()
        and (root / "pyproject.toml").is_file()
        and path.resolve().is_relative_to(root)
    ):
        raise ValueError("shrinking evidence must be outside the source tree")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--groups", type=int, default=64,
                        help="fixed finite group count, 64..1024; source schedule remains 64")
    parser.add_argument(
        "--max-work", type=int, default=DEFAULT_SHRINKING_POLICY.max_work
    )
    parser.add_argument(
        "--max-seconds", type=int, default=DEFAULT_SHRINKING_POLICY.max_seconds
    )
    parser.add_argument(
        "--max-calls", type=int, default=DEFAULT_SHRINKING_POLICY.max_calls
    )
    parser.add_argument(
        "--max-edges", type=int, default=DEFAULT_SHRINKING_POLICY.max_edges
    )
    args = parser.parse_args(argv)
    output_allowed = False
    try:
        _check_output(args.output)
        output_allowed = True
        parent = load_input(args.input)
        binding = source_binding()["digest"]
        policy = replace(
            DEFAULT_SHRINKING_POLICY,
            max_work=args.max_work,
            max_seconds=args.max_seconds,
            max_calls=args.max_calls,
            max_edges=args.max_edges,
        )
        report = contract_shrinking(parent, policy=policy, groups=args.groups)
        if source_binding()["digest"] != binding:
            raise ValueError("source changed during shrinking execution")
        report["implementation_source_sha256"] = binding
        report["policy"] = asdict(policy)
    except (
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
        RuntimeError,
        OSError,
    ) as exc:
        report = {
            "status": "INVALID_SHRINKING_CALL",
            "reason": str(exc),
            "source_qualified": False,
            "theorem_mode_enabled": False,
        }
    if args.output is not None and output_allowed:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
