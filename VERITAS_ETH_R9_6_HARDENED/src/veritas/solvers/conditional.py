"""Exact conditional probabilities using two independently checked weighted DAGs.

Input weights must be fully specified normalized Bernoulli priors. Supports
P(query-CNF | evidence-CNF) = WMC(evidence AND query) / WMC(evidence).
A zero-probability evidence event produces UNDEFINED, not an invented zero.
This is bounded, exponential-worst-case logic, not a general probabilistic
programming or causal inference system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from veritas.core.cnf import CNF
from veritas.solvers.weighted_dag import (
    make_weighted_dag_certificate, check_weighted_dag_certificate,
    parse_weights, is_normalized, decode_fraction, encode_fraction,
)


@dataclass
class ConditionalResult:
    status: str
    probability: str | None = None
    numerator: str | None = None
    denominator: str | None = None
    evidence_certificate: dict[str, Any] | None = None
    joint_certificate: dict[str, Any] | None = None
    reason: str | None = None


def exact_conditional(cnf: CNF, query: CNF, supplied: Any, *,
                      timeout_s: float = 5.0, max_nodes: int = 30_000,
                      max_bytes: int = 4_000_000) -> ConditionalResult:
    if cnf.n != query.n:
        raise ValueError('evidence and query must use the same declared variable scope')
    weights = parse_weights(cnf.n, supplied)
    if not is_normalized(weights):
        raise ValueError('conditional probability requires weights summing to 1 for every variable; omitted values default to [1,1]')
    denominator = make_weighted_dag_certificate(cnf, supplied, timeout_s=timeout_s,
                                                 max_nodes=max_nodes, max_bytes=max_bytes)
    if denominator.status != 'WEIGHTED_COUNT':
        return ConditionalResult('UNKNOWN', reason=f'evidence proof incomplete: {denominator.reason}')
    ok, why, count, _ = check_weighted_dag_certificate(cnf, supplied, denominator.certificate,
                                                         max_bytes=max_bytes)
    if not ok or count != denominator.count:
        raise RuntimeError(f'failed internal evidence proof verification: {why}')
    if decode_fraction(count) == 0:
        return ConditionalResult('UNDEFINED', denominator='0',
                                 evidence_certificate=denominator.certificate,
                                 reason='evidence has zero probability; conditioning undefined')
    joint = cnf.with_extra_clauses([list(c) for c in query.clauses])
    numerator = make_weighted_dag_certificate(joint, supplied, timeout_s=timeout_s,
                                               max_nodes=max_nodes, max_bytes=max_bytes)
    if numerator.status != 'WEIGHTED_COUNT':
        return ConditionalResult('UNKNOWN', denominator=denominator.count,
                                 evidence_certificate=denominator.certificate,
                                 reason=f'joint proof incomplete: {numerator.reason}')
    ok, why, value, _ = check_weighted_dag_certificate(joint, supplied, numerator.certificate,
                                                        max_bytes=max_bytes)
    if not ok or value != numerator.count:
        raise RuntimeError(f'failed internal joint proof verification: {why}')
    ratio = decode_fraction(value) / decode_fraction(count)
    if not 0 <= ratio <= 1:
        raise RuntimeError('probability invariants violated')
    return ConditionalResult('PROBABILITY', encode_fraction(ratio), value, count,
                             denominator.certificate, numerator.certificate)
