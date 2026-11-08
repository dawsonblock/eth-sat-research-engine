"""Run isolated finite structural cases, including explicit call-budget refusals."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import platform
from random import Random
import subprocess
import sys
from time import perf_counter, process_time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from veritas.core.cnf import CNF
from veritas.research.tensor import (
    Factor,
    TensorNetwork,
    brute_contract,
    eliminate,
    from_cnf,
)
from veritas.research.finite_reductions import (
    BoundaryPolicy,
    contract_boundary,
    replay_boundary,
)
from veritas.research.paper_verification.boundary_identity import verify_boundary_tree
from veritas.research.paper_verification.exact_parameters import check_schedule
from veritas.research.paper_verification.source_registry import source_registry
from veritas.solvers.reference import solve
from validate_r96 import peak_bytes


def fixture(n, name):
    rng = Random(97000 + n)
    if name == "dense":
        values = (1,) * (1 << n)
        return TensorNetwork(
            n,
            (
                Factor(tuple(range(n)), values, "row"),
                Factor(tuple(reversed(range(n))), values, "col"),
            ),
        ), None
    if name in ("satisfiable", "conflict"):
        clauses = [[1], [-1]] if name == "conflict" else []
        while sum(map(len, clauses)) < n:
            x, y = rng.sample(range(1, 7), 2)
            clauses.append([x, y if rng.randrange(2) else -y])
        cnf = CNF.from_lists(7, clauses)
        return from_cnf(cnf), cnf
    factors = []
    permutation = list(range(n))
    rng.shuffle(permutation)
    for i in range(n):
        end = (i + 1) % n
        if name == "disconnected":
            k = n // 2
            end = (i + 1) % k if i < k else k + (i - k + 1) % (n - k)
        factors.append(
            Factor(
                (permutation[end], permutation[i]),
                tuple(rng.randint(-5, 6) for _ in range(4)),
                str(i),
            )
        )
    rng.shuffle(factors)
    return TensorNetwork(n, tuple(factors)), None


def timed(fn):
    start, cpu = perf_counter(), process_time()
    value = fn()
    return value, {
        "wall_seconds": perf_counter() - start,
        "cpu_seconds": process_time() - cpu,
    }


def worker(n, name):
    net, cnf = fixture(n, name)
    p = cnf.n + 1 if cnf else 41
    policy = BoundaryPolicy(leaf_edges=3, verify_root=False)
    direct, dtime = timed(lambda: brute_contract(net, max_edges=16, timeout_s=90))
    value = direct % (1 << p)
    reduced, etime = timed(lambda: eliminate(net, modulus=1 << p, timeout_s=90))
    strict, stime = timed(lambda: contract_boundary(net, precision=p, policy=policy))
    summary = {
        "name": name,
        "wires": n,
        "p": p,
        "direct_integer": direct,
        "residue": value,
        "direct": dtime,
        "conventional_elimination": etime,
        "strict_status": strict["status"],
        "strict_measurement": stime,
        "strict_work": strict["ledger"],
        "strict_reason": strict.get("reason"),
    }
    if "result" not in strict:
        if name != "dense" or strict["reason"] != "boundary call limit":
            raise ValueError(strict)
        policy = replace(policy, on_call_overflow="certified_elimination")
        actual, elapsed = timed(
            lambda: contract_boundary(net, precision=p, policy=policy)
        )
    else:
        actual, elapsed = strict, stime
    cert = actual.get("certificate")
    if actual.get("result") != value or reduced != value or cert is None:
        raise ValueError("finite disagreement")
    checked = verify_boundary_tree(net, cert, precision=p, policy=policy)
    if (
        checked.get("result") != value
        or not replay_boundary(net, cert, precision=p, policy=policy)["valid"]
    ):
        raise ValueError("certificate did not verify")
    if cnf:
        dpll, dt = timed(lambda: solve(cnf, count=True))
        if dpll.count != value:
            raise ValueError("DPLL disagreement")
        summary["dpll_count"] = dt
    schedule = check_schedule(n, n, max(len(f.ports) for f in net.factors), 0)
    summary.update(
        actual_method=cert["tree"]["method"],
        observed=actual["ledger"],
        measurement=elapsed,
        independent_tree=checked,
        peak_case_process_rss_bytes=peak_bytes(),
        source_recursion="UNAVAILABLE",
        source_u=schedule["parameters"]["u"],
        source_preflight=schedule["status"],
    )
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--worker", nargs=2)
    p.add_argument("--output", type=Path, default=Path("validation/r97_matrix.json"))
    args = p.parse_args()
    if args.worker:
        print(json.dumps(worker(int(args.worker[0]), args.worker[1])))
        return
    report = {
        "status": "INCOMPLETE",
        "source_registry": source_registry(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "safeguards": "16 explicit wires, bounded cooperative wall/work, no hard memory cap",
        "cases": [],
    }
    try:
        for n in (12, 14, 16):
            for name in (
                "satisfiable",
                "conflict",
                "weighted_cycle",
                "disconnected",
                "dense",
            ):
                proc = subprocess.run(
                    [sys.executable, __file__, "--worker", str(n), name],
                    text=True,
                    capture_output=True,
                    timeout=300,
                )
                if proc.returncode:
                    raise ValueError(proc.stderr[-1500:])
                report["cases"].append(json.loads(proc.stdout))
        report["status"] = "PASS_FINITE_MATRIX"
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], len(report["cases"]))


if __name__ == "__main__":
    main()
