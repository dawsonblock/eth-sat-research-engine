"""Generate finite point certificates and benchmark each algorithm in a fresh process."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
from random import Random
import subprocess
import sys
from time import perf_counter, process_time

from veritas.core.cnf import CNF
from veritas.research.finite_reductions import (
    BoundaryPolicy,
    contract_boundary,
    replay_boundary,
)
from veritas.research.finite_reductions.recipe_point import (
    contract_recipe_point,
    replay_recipe_point,
)
from veritas.research.tensor import (
    Factor,
    TensorNetwork,
    brute_contract,
    eliminate,
    from_cnf,
)
from veritas.solvers.count_dag import make_dag_count_certificate
from veritas.solvers.reference import solve
from validate_r82 import _case


def peak_bytes():
    try:
        import resource
    except ImportError:
        return None
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
        1 if sys.platform == "darwin" else 1024
    )


def fixture(name):
    if name == "sat12":
        clauses = [[1, 2], [-1, 3], [-3, 2], [-2, 4], [4, -1], [-4, 1]]
        cnf = CNF.from_lists(5, clauses)
    elif name == "unsat12":
        cnf = CNF.from_lists(5, [[1], [-1], [2, 3], [-4, 1], [3, 4], [-3, 2], [4, -2]])
    elif name == "units16":
        cnf = CNF.from_lists(16, [[x] for x in range(1, 17)])
    else:
        n = int(name.removeprefix("cycle"))
        rng = Random(91)
        return (
            TensorNetwork(
                n,
                tuple(
                    Factor(
                        (i, (i + 1) % n),
                        tuple(rng.randint(-4, 5) for _ in range(4)),
                        str(i),
                    )
                    for i in range(n)
                ),
            ),
            None,
            41,
        )
    return from_cnf(cnf), cnf, cnf.n + 1


def measure(args):
    net, cnf, p = fixture(args.case)
    policy = BoundaryPolicy(
        leaf_edges=8 if args.case == "units16" else 3,
        piece_method="tapered" if args.method == "hybrid" else "direct",
        max_seconds=240,
        verify_root=False,
    )
    start, cpu = perf_counter(), process_time()
    details = {}
    if args.method in ("boundary", "hybrid"):
        report = contract_boundary(net, precision=p, policy=policy)
        if "result" not in report:
            raise ValueError(report)
        value = report["result"]
        details.update(ledger=report["ledger"], policy=asdict(policy))
    elif args.method == "direct":
        value = brute_contract(net, max_edges=16, timeout_s=60) % (1 << p)
    elif args.method == "eliminate":
        value = eliminate(net, timeout_s=60) % (1 << p)
    elif args.method == "dag":
        value = make_dag_count_certificate(cnf).count
    elif args.method == "dpll_count":
        value = solve(cnf, count=True).count
    else:
        raise ValueError("unknown method")
    details.update(
        wall_seconds=perf_counter() - start,
        cpu_seconds=process_time() - cpu,
        peak_process_rss_bytes=peak_bytes(),
        result=value,
    )
    if args.method in ("boundary", "hybrid"):
        begin = perf_counter()
        cert = report["certificate"]
        verdict = replay_boundary(net, cert, precision=p, policy=policy)
        if not verdict["valid"]:
            raise ValueError(verdict)
        details.update(replay=verdict["status"], replay_seconds=perf_counter() - begin)
        path = args.output.parent / (
            "r96_" + args.case + "_" + args.method + "_certificate.json"
        )
        path.write_text(
            json.dumps(cert, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        details["certificate"] = path.name
    print(json.dumps(details))


def validate(args):
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "schema": "VERITAS_FINITE_R96_VALIDATION_V1",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "peak_scope": "individual measurement process lifetime",
        "hard_memory_limit": False,
        "universal_theorem_proven": False,
        "complete_bit_bound": False,
        "point_policy": "one fixed point per parent size",
        "points": [],
        "cases": [],
        "status": "INCOMPLETE",
    }
    try:
        for n in (4, 6, 8):
            _, parent, _, modes = _case(n)
            report = contract_recipe_point(parent, modes)
            if "result" not in report or not replay_recipe_point(
                parent, modes, report["certificate"]
            ):
                raise ValueError(
                    report.get("reason", "point certificate replay failed")
                )
            cert = report["certificate"]
            if n == 8 and (
                report["result"] != ((169600000000, 0, 0, 0, 0),)
                or len(cert["terms"]) != 64
                or len(modes["modes"]) != 6
                or cert["p"] != 521
            ):
                raise ValueError("eight-wire anchor differs")
            path = output.parent / f"r96_recipe_point_{n}.json"
            path.write_text(
                json.dumps(cert, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            audit["points"].append(
                {
                    "wires": n,
                    "p": cert["p"],
                    "point": cert["point"],
                    "modes": len(modes["modes"]),
                    "tuples": len(cert["terms"]),
                    "group_children": len(cert["terms"]) * cert["groups_per_tuple"],
                    "result": report["result"],
                    "direct": report["direct_parent_result"],
                    "replayed": True,
                    "certificate": path.name,
                }
            )
        for name in ("sat12", "unsat12", "cycle12", "cycle14", "cycle16", "units16"):
            net, cnf, p = fixture(name)
            case = {"name": name, "wires": net.edges, "p": p, "measurements": {}}
            audit["cases"].append(case)
            methods = ["direct", "eliminate", "boundary"]
            if cnf:
                methods.extend(["dpll_count", "dag"])
            if name == "units16":
                methods.append("hybrid")
            for method in methods:
                worker = subprocess.run(
                    [
                        sys.executable,
                        __file__,
                        "--case",
                        name,
                        "--method",
                        method,
                        "--output",
                        str(output),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=510,
                )
                result = json.loads(worker.stdout)
                case["measurements"][method] = result
                direct = case["measurements"]["direct"]["result"]
                if type(result["result"]) is not int or result["result"] != direct:
                    raise ValueError(f"disagreement for {name} {method}")
        audit["status"] = "PASS_FINITE_CASES"
    finally:
        output.write_text(
            json.dumps(audit, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "points": len(audit["points"]),
                "networks": len(audit["cases"]),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("validation/r96_reductions.json")
    )
    parser.add_argument("--case")
    parser.add_argument("--method")
    args = parser.parse_args()
    if args.case:
        measure(args)
    else:
        validate(args)
