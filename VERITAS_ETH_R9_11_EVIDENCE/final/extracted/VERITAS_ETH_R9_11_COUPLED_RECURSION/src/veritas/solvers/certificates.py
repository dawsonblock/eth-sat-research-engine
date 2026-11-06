"""Bounded, independently verifiable DPLL-tree UNSAT certificates.

A certificate closes the Boolean search space through exhaustive binary splits,
forced unit clauses, and explicit falsified-clause leaves. The checker does not
call the SAT solver or trust any statement from the certificate creator. It is
NOT LRAT/DRAT and can be exponentially large. Verification cost is proportional
to certificate size and bounded by caller-controlled node and byte limits.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any

from veritas.core.cnf import CNF

FORMAT = "veritas-dpll-refutation-v1"
MAX_CERT_VARS = 28
MAX_CERT_NODES = 100_000
MAX_CERT_BYTES = 4_000_000


class CertificateLimit(Exception):
    pass


class Satisfiable(Exception):
    def __init__(self, model: dict[int, bool]):
        super().__init__("found satisfying assignment")
        self.model = model


@dataclass
class CertificateBuild:
    status: str
    certificate: dict[str, Any] | None = None
    model: dict[int, bool] | None = None
    nodes: int = 0
    reason: str | None = None


def _unsatisfied_clauses(cnf: CNF, partial: dict[int, bool]):
    """Yield (index, remaining literals), skipping satisfied clauses."""
    for idx, clause in enumerate(cnf.clauses):
        remaining = []
        for lit in clause:
            val = partial.get(abs(lit))
            if val is None:
                remaining.append(lit)
            elif val == (lit > 0):
                break
        else:
            yield idx, remaining


def make_unsat_certificate(
    cnf: CNF, *, timeout_s: float = 5.0, max_nodes: int = 30_000,
    max_bytes: int = MAX_CERT_BYTES,
) -> CertificateBuild:
    if not (0 < timeout_s <= 30) or not (1 <= max_nodes <= MAX_CERT_NODES):
        raise ValueError("invalid certificate budget")
    if not (256 <= max_bytes <= MAX_CERT_BYTES):
        raise ValueError("invalid maximum certificate bytes")
    if cnf.n > MAX_CERT_VARS:
        return CertificateBuild("UNKNOWN", reason=f"certificate generation limited to {MAX_CERT_VARS} variables")
    deadline = time.monotonic() + timeout_s
    nodes = 0

    def walk(partial: dict[int, bool]):
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or time.monotonic() > deadline:
            raise CertificateLimit("certificate generation budget exceeded")
        active = list(_unsatisfied_clauses(cnf, partial))
        for idx, lits in active:
            if not lits:
                return {"conflict": idx}
        if not active:
            model = {v: partial.get(v, False) for v in range(1, cnf.n + 1)}
            raise Satisfiable(model)
        for idx, lits in active:
            # Deduplicated unit literal; opposite signs of same variable are not a unit.
            remaining = set(lits)
            if len(remaining) == 1:
                lit = next(iter(remaining))
                child = dict(partial)
                child[abs(lit)] = lit > 0
                return {"unit": lit, "clause": idx, "next": walk(child)}
        _, short = min(active, key=lambda pair: len(pair[1]))
        var = abs(short[0])
        child0 = dict(partial)
        child0[var] = False
        false_branch = walk(child0)
        child1 = dict(partial)
        child1[var] = True
        true_branch = walk(child1)
        return {"split": var, "false": false_branch, "true": true_branch}

    try:
        root = walk({})
        result = {"format": FORMAT, "cnf_sha256": cnf.digest(), "root": root}
        if len(json.dumps(result, separators=(",", ":")).encode("utf-8")) > max_bytes:
            return CertificateBuild("UNKNOWN", nodes=nodes, reason="certificate exceeds byte limit")
        return CertificateBuild("UNSAT", certificate=result, nodes=nodes)
    except Satisfiable as exc:
        if not cnf.evaluate(exc.model):
            raise AssertionError("internal SAT witness invalid")
        return CertificateBuild("SAT", model=exc.model, nodes=nodes)
    except (CertificateLimit, RecursionError) as exc:
        return CertificateBuild("UNKNOWN", nodes=nodes, reason=str(exc))


def check_unsat_certificate(
    cnf: CNF, certificate: Any, *, max_nodes: int = MAX_CERT_NODES,
    max_bytes: int = MAX_CERT_BYTES,
) -> tuple[bool, str, int]:
    """Pure checker. A valid certificate covers all assignments to declared CNF.

    All unit steps must be logically forced by the specified original clause.
    Splits must branch on one previously unassigned declared variable.
    Every leaf explicitly identifies a clause falsified by its path assignment.
    """
    if not (1 <= max_nodes <= MAX_CERT_NODES and 256 <= max_bytes <= MAX_CERT_BYTES):
        raise ValueError("invalid checker budget")
    try:
        raw = json.dumps(certificate, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return False, "certificate is not JSON serializable", 0
    if len(raw.encode("utf-8")) > max_bytes:
        return False, "certificate exceeds byte limit", 0
    if not isinstance(certificate, dict) or set(certificate) != {"format", "cnf_sha256", "root"}:
        return False, "certificate envelope mismatch", 0
    if certificate["format"] != FORMAT or certificate["cnf_sha256"] != cnf.digest():
        return False, "certificate format or CNF hash mismatch", 0

    stack = [(certificate["root"], {})]
    processed = 0
    while stack:
        node, partial = stack.pop()
        processed += 1
        if processed > max_nodes:
            return False, "checker node budget exceeded", processed
        if not isinstance(node, dict):
            return False, "proof node is not an object", processed
        if set(node) == {"conflict"}:
            idx = node["conflict"]
            if type(idx) is not int or not 0 <= idx < len(cnf.clauses):
                return False, "invalid conflict clause index", processed
            clause = cnf.clauses[idx]
            if any(abs(lit) not in partial or partial[abs(lit)] == (lit > 0) for lit in clause):
                return False, "conflict clause is not falsified", processed
            continue
        if set(node) == {"unit", "clause", "next"}:
            lit, idx = node["unit"], node["clause"]
            if (type(lit) is not int or lit == 0 or abs(lit) > cnf.n
                    or abs(lit) in partial or type(idx) is not int or not 0 <= idx < len(cnf.clauses)):
                return False, "invalid unit step", processed
            unknown = set()
            for clause_lit in cnf.clauses[idx]:
                if abs(clause_lit) not in partial:
                    unknown.add(clause_lit)
                elif partial[abs(clause_lit)] == (clause_lit > 0):
                    return False, "unit premise clause already satisfied", processed
            if unknown != {lit}:
                return False, "unit step not forced by clause", processed
            stack.append((node["next"], {**partial, abs(lit): lit > 0}))
            continue
        if set(node) == {"split", "false", "true"}:
            var = node["split"]
            if type(var) is not int or not 1 <= var <= cnf.n or var in partial:
                return False, "invalid split variable", processed
            stack.append((node["false"], {**partial, var: False}))
            stack.append((node["true"], {**partial, var: True}))
            continue
        return False, "unrecognized proof node", processed
    return True, "independently checked refutation tree", processed
