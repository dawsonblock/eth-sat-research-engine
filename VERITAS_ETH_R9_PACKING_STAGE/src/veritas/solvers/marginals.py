"""Exact all-variable posterior marginals by reverse accumulation on a checked WMC DAG.

Given a normalized independent Bernoulli prior and Boolean evidence F,
  Z = sum_{x |= F} prod_v w[v, x_v],
  P(X_v=b | F) = (w[v,b] * dZ/dw[v,b]) / Z.

One forward weighted component-DAG counts the evidence once; a reverse pass
uses its arithmetic circuit to recover *all* single-variable posteriors.  An
independent replayer validates the source DAG, reconstructs residual states,
and recomputes every marginal. No divisions are used during differentiation:
zero-valued weights and zero-valued subcircuits are handled exactly.

This does not implement the manuscript's collision packing or subexponential
contraction. The general-case runtime and certificate size remain exponential.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from time import monotonic
from typing import Any

from veritas.core.cnf import CNF
from veritas.solvers.count_dag import _root_state, _rule
from veritas.solvers.weighted_dag import (
    _bounded, WeightedLimit, make_weighted_dag_certificate,
    check_weighted_dag_certificate, parse_weights, is_normalized,
    encode_fraction, decode_fraction,
)

FORMAT = 'veritas-exact-posterior-marginals-v1'
MAX_REVERSE_WORK = 2_000_000


@dataclass
class MarginalsResult:
    status: str
    evidence_weight: str | None = None
    marginals: dict[str, list[str]] | None = None
    certificate: dict[str, Any] | None = None
    nodes: int = 0
    reason: str | None = None


def _prefix_suffix(values: list[Fraction]):
    """Zero-safe products excluding each index, with no rational division."""
    prefix = [Fraction(1)]
    for value in values:
        prefix.append(_bounded(prefix[-1] * value))
    right = Fraction(1)
    products = [Fraction(0)] * len(values)
    for i in range(len(values) - 1, -1, -1):
        products[i] = _bounded(prefix[i] * right)
        right = _bounded(right * values[i])
    return products


def _recover_states(cnf: CNF, certificate: dict) -> dict[int, tuple]:
    """Recover the scopes of checked DAG nodes from the original CNF."""
    nodes = certificate['nodes']
    states = {}
    stack = [(certificate['root'], _root_state(cnf))]
    while stack:
        idx, state = stack.pop()
        if idx in states:
            if states[idx] != state:
                raise ValueError('one DAG node used for two different states')
            continue
        states[idx] = state
        kind, payload, children = _rule(state)
        node = nodes[idx]
        if node['kind'] != kind or len(node['children']) != len(children):
            raise ValueError('DAG structure does not match the source formula')
        stack.extend(zip(node['children'], children))
    if len(states) != len(nodes):
        raise ValueError('unreachable DAG nodes')
    return states


def _differentiate(cnf: CNF, weights, certificate: dict, *, timeout_s: float = 10.0,
                   max_ops: int = MAX_REVERSE_WORK):
    if type(max_ops) is not int or not 1 <= max_ops <= MAX_REVERSE_WORK:
        raise ValueError('invalid differentiation operation budget')
    if type(timeout_s) not in (float, int) or not 0 < timeout_s <= 30:
        raise ValueError('invalid differentiation timeout')
    deadline = monotonic() + timeout_s
    nodes = certificate['nodes']
    states = _recover_states(cnf, certificate)
    counts = [decode_fraction(node['count']) for node in nodes]
    adjoints = [Fraction(0)] * len(nodes)
    adjoints[certificate['root']] = Fraction(1)
    derivatives = [[Fraction(0), Fraction(0)] for _ in range(cnf.n + 1)]
    operations = 0

    def account(amount=1):
        nonlocal operations
        operations += amount
        if operations > max_ops or monotonic() >= deadline:
            raise WeightedLimit('posterior reverse-pass time/operation limit exceeded')

    def add_factor_derivative(scope, outer):
        masses = [weights[v][0] + weights[v][1] for v in scope]
        for v, others in zip(scope, _prefix_suffix(masses)):
            account()
            contribution = _bounded(outer * others)
            derivatives[v][0] = _bounded(derivatives[v][0] + contribution)
            derivatives[v][1] = _bounded(derivatives[v][1] + contribution)

    for idx in range(len(nodes) - 1, -1, -1):
        account()
        outer = adjoints[idx]
        if outer == 0:
            continue
        node = nodes[idx]
        scope, _ = states[idx]
        child_ids = node['children']
        kind = node['kind']
        if kind == 'conflict':
            continue
        if kind == 'satisfied':
            add_factor_derivative(scope, outer)
        elif kind == 'free':
            child_scope = set(states[child_ids[0]][0])
            free = tuple(v for v in scope if v not in child_scope)
            masses = [sum(weights[v]) for v in free]
            factor = Fraction(1)
            for mass in masses:
                account()
                factor = _bounded(factor * mass)
            adjoints[child_ids[0]] = _bounded(adjoints[child_ids[0]] + outer * factor)
            add_factor_derivative(free, _bounded(outer * counts[child_ids[0]]))
        elif kind == 'unit':
            literal = node['literal']
            v, bit = abs(literal), int(literal > 0)
            adjoints[child_ids[0]] = _bounded(adjoints[child_ids[0]] + outer * weights[v][bit])
            derivatives[v][bit] = _bounded(derivatives[v][bit] + outer * counts[child_ids[0]])
        elif kind == 'split':
            v = node['variable']
            for bit, child_id in enumerate(child_ids):
                account()
                adjoints[child_id] = _bounded(adjoints[child_id] + outer * weights[v][bit])
                derivatives[v][bit] = _bounded(derivatives[v][bit] + outer * counts[child_id])
        elif kind == 'product':
            others = _prefix_suffix([counts[child_id] for child_id in child_ids])
            for child_id, product in zip(child_ids, others):
                account()
                adjoints[child_id] = _bounded(adjoints[child_id] + outer * product)
        else:
            raise ValueError('unknown checked DAG rule')

    z = counts[certificate['root']]
    if z == 0:
        return 'UNDEFINED', '0', None
    marginals = {}
    for v in range(1, cnf.n + 1):
        account()
        joint0 = _bounded(weights[v][0] * derivatives[v][0])
        joint1 = _bounded(weights[v][1] * derivatives[v][1])
        if joint0 + joint1 != z:
            raise ValueError('posterior normalization invariant failed')
        p0, p1 = _bounded(joint0 / z), _bounded(joint1 / z)
        marginals[str(v)] = [encode_fraction(p0), encode_fraction(p1)]
    return 'POSTERIORS', encode_fraction(z), marginals


def _marginal_binding(cnf: CNF, weights, certificate: dict) -> str:
    msg = {'format': FORMAT, 'cnf_sha256': cnf.digest(),
           'weight_pairs': [[encode_fraction(w0), encode_fraction(w1)] for w0, w1 in weights[1:]],
           'dag': certificate}
    return sha256(json.dumps(msg, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')).hexdigest()


def check_marginal_certificate(cnf: CNF, supplied: Any, claim: Any, *,
                               timeout_s: float = 10.0, max_ops: int = MAX_REVERSE_WORK):
    """Independently replay count certificate and all posterior derivatives."""
    try:
        weights = parse_weights(cnf.n, supplied)
        if not is_normalized(weights):
            raise ValueError('fully specified normalized priors required')
        if type(claim) is not dict or set(claim) != {'format', 'binding_sha256', 'evidence_weight', 'marginals', 'dag'}:
            raise ValueError('invalid marginal certificate fields')
        if claim['format'] != FORMAT or claim['binding_sha256'] != _marginal_binding(cnf, weights, claim['dag']):
            raise ValueError('marginal certificate binding mismatch')
        valid, message, weight, nodes = check_weighted_dag_certificate(cnf, supplied, claim['dag'])
        if not valid:
            raise ValueError('underlying counting certificate rejected: ' + message)
        status, expected_z, expected = _differentiate(cnf, weights, claim['dag'],
                                                      timeout_s=timeout_s, max_ops=max_ops)
        if claim['evidence_weight'] != expected_z or claim['marginals'] != expected:
            raise ValueError('marginal values disagree with exact reverse replay')
        if weight != expected_z:
            raise ValueError('DAG count and marginal evidence weight disagree')
        return True, 'replayed weighted counting DAG and exact posterior derivatives', status, expected, nodes
    except (TypeError, ValueError, KeyError, OverflowError, RecursionError, WeightedLimit) as exc:
        return False, str(exc), 'REJECTED', None, 0


def exact_marginals(cnf: CNF, supplied: Any, *, timeout_s: float = 5.0,
                    max_nodes: int = 30000, max_bytes: int = 4_000_000,
                    max_reverse_ops: int = MAX_REVERSE_WORK) -> MarginalsResult:
    weights = parse_weights(cnf.n, supplied)
    if not is_normalized(weights):
        raise ValueError('normalized prior weights required for every variable; omitted pairs default to [1,1]')
    proof = make_weighted_dag_certificate(cnf, supplied, timeout_s=timeout_s,
                                          max_nodes=max_nodes, max_bytes=max_bytes)
    if proof.status != 'WEIGHTED_COUNT':
        return MarginalsResult('UNKNOWN', nodes=proof.nodes, reason=proof.reason)
    ok, reason, count, _ = check_weighted_dag_certificate(cnf, supplied, proof.certificate,
                                                           max_nodes=max_nodes, max_bytes=max_bytes)
    if not ok or count != proof.count:
        raise RuntimeError('the generated weighted DAG failed an independent check: ' + reason)
    try:
        status, z, marginals = _differentiate(cnf, weights, proof.certificate,
                                               timeout_s=timeout_s, max_ops=max_reverse_ops)
        cert = {'format': FORMAT, 'binding_sha256': _marginal_binding(cnf, weights, proof.certificate),
                'evidence_weight': z, 'marginals': marginals, 'dag': proof.certificate}
        if len(json.dumps(cert, separators=(',', ':')).encode('utf8')) > max_bytes:
            return MarginalsResult('UNKNOWN', nodes=proof.nodes, reason='marginal certificate byte limit exceeded')
        valid, reason, reproduced_status, reproduced, _ = check_marginal_certificate(
            cnf, supplied, cert, timeout_s=timeout_s, max_ops=max_reverse_ops)
        if not valid or reproduced != marginals or reproduced_status != status:
            raise RuntimeError('marginal certificate did not independently replay: ' + reason)
        return MarginalsResult(status, z, marginals, cert, proof.nodes,
                               'evidence probability zero' if status == 'UNDEFINED' else None)
    except (WeightedLimit, RecursionError, OverflowError) as exc:
        return MarginalsResult('UNKNOWN', nodes=proof.nodes, reason=str(exc))
