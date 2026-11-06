"""Bounded proof-carrying exact unweighted #SAT.

Every leaf is a falsified input clause or a partial assignment satisfying all
input clauses. All non-leaf nodes must be forced units or complete binary
splits. The INDEPENDENT checker recalculates the sum over *all declared*
variables, including unused variables, using only the original CNF and the
certificate. No solver call is made by the checker.

This is a transparent exponential reference proof; NOT a polynomial-size
counting proof and NOT the paper's subexponential algorithm.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import time
from typing import Any
from veritas.core.cnf import CNF

FORMAT = "veritas-shannon-count-tree-v1"
MAX_VARS = 26
MAX_NODES = 80_000
MAX_BYTES = 4_000_000


@dataclass
class CountCertificateBuild:
    status: str
    count: int | None = None
    certificate: dict[str, Any] | None = None
    nodes: int = 0
    reason: str | None = None


class _Limit(Exception):
    pass


def _active(cnf: CNF, assignment: dict[int, bool]):
    """A fresh evaluator (does not depend on the SAT solver)."""
    active = []
    for index, clause in enumerate(cnf.clauses):
        pending = []
        for lit in clause:
            var = abs(lit)
            if var not in assignment:
                pending.append(lit)
            elif assignment[var] == (lit > 0):
                break
        else:
            active.append((index, pending))
    return active


def make_count_certificate(cnf: CNF, *, timeout_s: float = 5,
                           max_nodes: int = 30_000,
                           max_bytes: int = MAX_BYTES) -> CountCertificateBuild:
    if not 0 < timeout_s <= 30 or not 1 <= max_nodes <= MAX_NODES or not 256 <= max_bytes <= MAX_BYTES:
        raise ValueError("invalid count certificate budget")
    if cnf.n > MAX_VARS:
        return CountCertificateBuild("UNKNOWN", reason=f"count certificate limited to {MAX_VARS} variables")
    deadline = time.monotonic() + timeout_s
    nodes = 0

    def walk(assignment: dict[int, bool]) -> tuple[dict, int]:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or time.monotonic() >= deadline:
            raise _Limit("count certificate node/time budget exceeded")
        active = _active(cnf, assignment)
        for idx, rem in active:
            if not rem:
                return {"conflict": idx, "count": "0"}, 0
        if not active:
            count = 1 << (cnf.n - len(assignment))
            return {"satisfied": True, "count": str(count)}, count
        for idx, rem in active:
            literals = set(rem)
            if len(literals) == 1:
                lit = next(iter(literals))
                updated = dict(assignment)
                updated[abs(lit)] = lit > 0
                child, count = walk(updated)
                return {"unit": lit, "clause": idx, "next": child, "count": str(count)}, count
        _, shortest = min(active, key=lambda item: len(item[1]))
        var = abs(shortest[0])
        left, lc = walk({**assignment, var: False})
        right, rc = walk({**assignment, var: True})
        count = lc + rc
        return {"split": var, "false": left, "true": right, "count": str(count)}, count

    try:
        root, count = walk({})
        proof = {"format": FORMAT, "cnf_sha256": cnf.digest(), "count": str(count), "root": root}
        if len(json.dumps(proof, separators=(",", ":")).encode()) > max_bytes:
            return CountCertificateBuild("UNKNOWN", nodes=nodes, reason="count certificate exceeds byte cap")
        return CountCertificateBuild("COUNT", count, proof, nodes)
    except (_Limit, RecursionError) as exc:
        return CountCertificateBuild("UNKNOWN", nodes=nodes, reason=str(exc))


def check_count_certificate(cnf: CNF, certificate: Any, *,
                            max_nodes: int = MAX_NODES,
                            max_bytes: int = MAX_BYTES) -> tuple[bool, str, int | None, int]:
    """Verify the full count for every declared variable, independently.

    In particular, a certificate cannot claim that an undecided clause is
    satisfied, skip a binary branch, or invent a non-forced unit step.
    Returns (valid, reason, recomputed_count_or_none, checked_nodes).
    """
    if not 1 <= max_nodes <= MAX_NODES or not 256 <= max_bytes <= MAX_BYTES:
        raise ValueError("invalid checker budget")
    try:
        raw = json.dumps(certificate, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError, OverflowError):
        return False, "not JSON serializable", None, 0
    if len(raw.encode()) > max_bytes:
        return False, "certificate exceeds byte cap", None, 0
    if not isinstance(certificate, dict) or set(certificate) != {"format", "cnf_sha256", "count", "root"}:
        return False, "envelope shape mismatch", None, 0
    if certificate["format"] != FORMAT or certificate["cnf_sha256"] != cnf.digest():
        return False, "format or CNF hash mismatch", None, 0

    nodes = 0

    def valid_count(v: Any) -> int:
        if not isinstance(v, str) or not v.isascii() or not v.isdecimal() or (len(v) > 1 and v[0] == '0') or len(v) > 160:
            raise ValueError("noncanonical count encoding")
        result = int(v)
        if result > (1 << cnf.n):
            raise ValueError("count exceeds assignment universe")
        return result

    def check(root: Any, assignment: dict[int, bool]) -> int:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            raise ValueError("checker node budget exceeded")
        if not isinstance(root, dict) or "count" not in root:
            raise ValueError("invalid proof node")
        claimed = valid_count(root["count"])
        keys = set(root)
        if keys == {"conflict", "count"}:
            idx = root["conflict"]
            if type(idx) is not int or not 0 <= idx < len(cnf.clauses):
                raise ValueError("bad conflict clause index")
            if any(abs(lit) not in assignment or assignment[abs(lit)] == (lit > 0)
                   for lit in cnf.clauses[idx]):
                raise ValueError("conflict clause is not falsified")
            actual = 0
        elif keys == {"satisfied", "count"}:
            if root["satisfied"] is not True:
                raise ValueError("invalid satisfied marker")
            for clause in cnf.clauses:
                if not any(abs(lit) in assignment and assignment[abs(lit)] == (lit > 0) for lit in clause):
                    raise ValueError("not every original clause is satisfied")
            actual = 1 << (cnf.n - len(assignment))
        elif keys == {"unit", "clause", "next", "count"}:
            lit, idx = root["unit"], root["clause"]
            if type(lit) is not int or lit == 0 or abs(lit) > cnf.n or abs(lit) in assignment:
                raise ValueError("bad unit step")
            if type(idx) is not int or not 0 <= idx < len(cnf.clauses):
                raise ValueError("bad unit premise")
            pending = set()
            for original in cnf.clauses[idx]:
                if abs(original) in assignment:
                    if assignment[abs(original)] == (original > 0):
                        raise ValueError("unit premise already satisfied")
                else:
                    pending.add(original)
            if pending != {lit}:
                raise ValueError("unit is not forced by original clause")
            actual = check(root["next"], {**assignment, abs(lit): lit > 0})
        elif keys == {"split", "false", "true", "count"}:
            var = root["split"]
            if type(var) is not int or not 1 <= var <= cnf.n or var in assignment:
                raise ValueError("bad split variable")
            actual = check(root["false"], {**assignment, var: False}) + check(root["true"], {**assignment, var: True})
        else:
            raise ValueError("unrecognized proof node")
        if actual != claimed:
            raise ValueError("claimed subtree count is incorrect")
        return actual

    try:
        actual = check(certificate["root"], {})
        if actual != valid_count(certificate["count"]):
            raise ValueError("claimed root count is incorrect")
        return True, "independently checked complete Shannon counting tree", actual, nodes
    except (ValueError, RecursionError) as exc:
        return False, str(exc), None, nodes
