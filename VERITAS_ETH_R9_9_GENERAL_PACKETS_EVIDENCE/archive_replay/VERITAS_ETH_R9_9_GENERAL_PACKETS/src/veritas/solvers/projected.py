"""Bounded exact existential/projected model counting via blocking clauses.

Counts distinct valuations of `projected` variables for which an extension to
all other declared variables satisfies the CNF. Models are independently checked.
No probabilistic counter is used; truncated searches return UNKNOWN, not counts.
"""
from __future__ import annotations
from dataclasses import dataclass
import time
from veritas.core.cnf import CNF
from veritas.solvers.reference import solve

MAX_PROJECTED = 12

@dataclass
class ProjectedResult:
    status: str
    count: int | None = None
    solver_calls: int = 0
    nodes: int = 0
    reason: str | None = None


def projected_count(cnf: CNF, projected: list[int], *, timeout_s: float = 5.0, max_nodes: int = 150_000) -> ProjectedResult:
    if type(projected) is not list or any(type(v) is not int or not 1 <= v <= cnf.n for v in projected):
        raise ValueError("projected must be a list of declared variable indices")
    if len(set(projected)) != len(projected) or len(projected) > MAX_PROJECTED:
        raise ValueError(f"projected variables must be unique and at most {MAX_PROJECTED} in number")
    if not (0 < timeout_s <= 30 and 1 <= max_nodes <= 2_000_000):
        raise ValueError("invalid resource budget")
    proj = tuple(sorted(projected))
    deadline = time.monotonic() + timeout_s
    count = 0
    nodes = 0
    calls = 0
    blocks: list[tuple[int, ...]] = []
    # At most 2^k distinct projected solutions and one final UNSAT call.
    for _ in range((1 << len(proj)) + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or nodes >= max_nodes:
            return ProjectedResult("UNKNOWN", solver_calls=calls, nodes=nodes, reason="projected search budget exhausted")
        try:
            current = CNF(cnf.n, cnf.clauses + tuple(blocks))
        except ValueError:
            # A finished partial enumeration is not an exact final count.
            return ProjectedResult("UNKNOWN", solver_calls=calls, nodes=nodes,
                                   reason="CNF representation budget exhausted by blocking clauses")
        result = solve(current, timeout_s=min(30.0, remaining), max_nodes=min(2_000_000, max_nodes-nodes))
        calls += 1
        nodes += result.nodes
        if result.status == "UNKNOWN":
            return ProjectedResult("UNKNOWN", solver_calls=calls, nodes=nodes, reason=result.reason)
        if result.status == "UNSAT":
            return ProjectedResult("COUNT", count=count, solver_calls=calls, nodes=nodes)
        if not current.evaluate(result.model) or not cnf.evaluate(result.model):
            raise RuntimeError("invalid projected SAT witness")
        count += 1
        block = tuple(-v if result.model[v] else v for v in proj)
        blocks.append(block)
    raise AssertionError("projected counting exceeded cardinality bound")
