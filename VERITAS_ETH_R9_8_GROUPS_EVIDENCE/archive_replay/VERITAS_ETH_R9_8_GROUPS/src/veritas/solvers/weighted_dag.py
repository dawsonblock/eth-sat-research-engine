"""Bounded, proof-carrying exact rational weighted model counting.

For a CNF F with variable weights w0[v], w1[v], computes
  Z(F) = sum_{x models F} product_{v=1..n} w_{x[v]}[v].

Absent variable entries default to (1,1), hence all-ones weights recover #SAT.
Nonnegative rational arithmetic is exact. The verifier reconstructs each residual
formula from the original CNF, validates every DAG transition and recomputes
arithmetic independently of the generator. Neither the format nor the algorithm
is a polynomial-size proof guarantee or the manuscript ETH algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
import re
from time import monotonic
from typing import Any

from veritas.core.cnf import CNF
from veritas.solvers.count_dag import _root_state, _rule, MAX_NODES, MAX_BYTES, MAX_VARS, CertificateLimit

FORMAT = 'veritas-rational-weighted-component-dag-v1'
MAX_WEIGHT_COMPONENT = 1_000_000
MAX_COUNT_BITS = 8192
MAX_ENCODED_FRACTION = 3000
_TOKEN = re.compile(r'(?:0|[1-9][0-9]{0,6})(?:/(?:[1-9][0-9]{0,6}))?\Z', re.ASCII)
_CANONICAL = re.compile(r'(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z', re.ASCII)

Weights = tuple[tuple[Fraction, Fraction], ...]  # index 0 unused; entries (false,true)


class WeightedLimit(Exception):
    pass


@dataclass
class WeightedDagResult:
    status: str
    count: str | None = None
    certificate: dict[str, Any] | None = None
    nodes: int = 0
    cache_hits: int = 0
    normalized: bool = False
    reason: str | None = None


def _check_fraction(raw: Any) -> Fraction:
    if type(raw) is not str or not _TOKEN.fullmatch(raw):
        raise ValueError('weight must be a nonnegative canonical integer or fraction string')
    numerator, sep, denominator = raw.partition('/')
    n = int(numerator)
    d = int(denominator) if sep else 1
    if n > MAX_WEIGHT_COMPONENT or d > MAX_WEIGHT_COMPONENT:
        raise ValueError('weight component exceeds 1000000')
    return Fraction(n, d)


def parse_weights(n: int, supplied: Any) -> Weights:
    """Input mapping: {'1': ['w_false','w_true'], ...}; omitted = [1,1]."""
    if type(n) is not int or not 0 <= n <= MAX_VARS:
        raise ValueError(f'weighted model counting requires 0..{MAX_VARS} variables')
    if type(supplied) is not dict or len(supplied) > n:
        raise ValueError('weights must be a variable-index mapping')
    out = [(Fraction(1), Fraction(1)) for _ in range(n + 1)]
    for key, pair in supplied.items():
        if type(key) is not str or not re.fullmatch(r'[1-9][0-9]*', key, flags=re.ASCII):
            raise ValueError('variable indices must be canonical positive decimal strings')
        v = int(key)
        if not 1 <= v <= n:
            raise ValueError('weight variable outside declared scope')
        if type(pair) is not list or len(pair) != 2:
            raise ValueError('each weight must be [weight_false, weight_true]')
        out[v] = (_check_fraction(pair[0]), _check_fraction(pair[1]))
    return tuple(out)


def encode_fraction(number: Fraction) -> str:
    if number.denominator == 1:
        return str(number.numerator)
    return f'{number.numerator}/{number.denominator}'


def decode_fraction(raw: Any) -> Fraction:
    if type(raw) is not str or len(raw) > MAX_ENCODED_FRACTION or not _CANONICAL.fullmatch(raw):
        raise ValueError('invalid canonical rational count')
    numerator, sep, denominator = raw.partition('/')
    result = Fraction(int(numerator), int(denominator) if sep else 1)
    if encode_fraction(result) != raw:
        raise ValueError('rational count is not in reduced canonical form')
    if result.numerator.bit_length() > MAX_COUNT_BITS or result.denominator.bit_length() > MAX_COUNT_BITS:
        raise ValueError('rational count exceeds bit budget')
    return result


def weight_digest(weights: Weights) -> str:
    content = [[encode_fraction(a), encode_fraction(b)] for a, b in weights[1:]]
    return sha256(json.dumps(content, separators=(',', ':'), ensure_ascii=True).encode('ascii')).hexdigest()


def is_normalized(weights: Weights) -> bool:
    return all(a + b == 1 for a, b in weights[1:])


def _bounded(number: Fraction) -> Fraction:
    if number < 0 or number.numerator.bit_length() > MAX_COUNT_BITS or number.denominator.bit_length() > MAX_COUNT_BITS:
        raise WeightedLimit('rational numerator or denominator exceeds safe bit budget')
    return number


def _free_multiplier(scope: tuple[int, ...], weights: Weights) -> Fraction:
    result = Fraction(1)
    for v in scope:
        result = _bounded(result * sum(weights[v]))
    return result


def _transition(kind: str, payload: dict, scope: tuple[int, ...], children: list[Fraction], weights: Weights,
                subscopes: tuple[tuple[int, ...], ...]) -> Fraction:
    if kind == 'conflict': return Fraction(0)
    if kind == 'satisfied': return _free_multiplier(scope, weights)
    if kind == 'free':
        reduced = set(subscopes[0]); free = tuple(v for v in scope if v not in reduced)
        if len(free) != payload['free']:
            raise ValueError('incorrect number of free variables')
        return _bounded(_free_multiplier(free, weights) * children[0])
    if kind == 'unit':
        lit = payload['literal']
        w = weights[abs(lit)][1 if lit > 0 else 0]
        return _bounded(w * children[0])
    if kind == 'product':
        z = Fraction(1)
        for child in children: z = _bounded(z * child)
        return z
    if kind == 'split':
        w0, w1 = weights[payload['variable']]
        return _bounded(w0 * children[0] + w1 * children[1])
    raise ValueError('unexpected DAG rule')


def make_weighted_dag_certificate(cnf: CNF, supplied: Any, *, timeout_s: float = 5.0,
                                  max_nodes: int = 30_000, max_bytes: int = MAX_BYTES) -> WeightedDagResult:
    if type(timeout_s) not in (float, int) or not 0 < timeout_s <= 30:
        raise ValueError('timeout_s must be in (0,30]')
    if type(max_nodes) is not int or not 1 <= max_nodes <= MAX_NODES:
        raise ValueError('max_nodes invalid')
    if type(max_bytes) is not int or not 256 <= max_bytes <= MAX_BYTES:
        raise ValueError('max_bytes invalid')
    if cnf.n > MAX_VARS:
        return WeightedDagResult('UNKNOWN', reason=f'at most {MAX_VARS} variables supported')
    weights = parse_weights(cnf.n, supplied)
    normalized = is_normalized(weights)
    deadline = monotonic() + timeout_s
    memo: dict[Any, int] = {}
    nodes: list[dict[str, Any]] = []
    hits = 0

    def build(state):
        nonlocal hits
        if monotonic() >= deadline or len(nodes) >= max_nodes:
            raise CertificateLimit('node/time budget exceeded')
        if state in memo:
            hits += 1
            return memo[state]
        kind, payload, sub = _rule(state)
        ids = [build(child) for child in sub]
        value = _transition(kind, payload, state[0],
                            [decode_fraction(nodes[i]['count']) for i in ids],
                            weights, tuple(c[0] for c in sub))
        node = {'kind': kind, 'count': encode_fraction(value), **payload, 'children': ids}
        idx = len(nodes)
        nodes.append(node)
        memo[state] = idx
        return idx

    try:
        root = build(_root_state(cnf))
        count = nodes[root]['count']
        cert = {'format': FORMAT, 'cnf_sha256': cnf.digest(), 'weights_sha256': weight_digest(weights),
                'root': root, 'count': count, 'nodes': nodes}
        if len(json.dumps(cert, separators=(',', ':'), allow_nan=False).encode('utf8')) > max_bytes:
            return WeightedDagResult('UNKNOWN', nodes=len(nodes), cache_hits=hits,
                                     normalized=normalized, reason='certificate byte budget exceeded')
        return WeightedDagResult('WEIGHTED_COUNT', count, cert, len(nodes), hits, normalized)
    except (CertificateLimit, WeightedLimit, RecursionError, OverflowError) as exc:
        return WeightedDagResult('UNKNOWN', nodes=len(nodes), cache_hits=hits,
                                 normalized=normalized, reason=str(exc))


def check_weighted_dag_certificate(cnf: CNF, supplied: Any, certificate: Any, *,
                                   max_nodes: int = MAX_NODES, max_bytes: int = MAX_BYTES) -> tuple[bool, str, str | None, int]:
    """Re-derive every node, branch and rational operation; never trust submitted residuals."""
    if type(max_nodes) is not int or not 1 <= max_nodes <= MAX_NODES:
        raise ValueError('invalid max_nodes')
    if type(max_bytes) is not int or not 256 <= max_bytes <= MAX_BYTES:
        raise ValueError('invalid max_bytes')
    try:
        weights = parse_weights(cnf.n, supplied)
        packed = json.dumps(certificate, separators=(',', ':'), allow_nan=False).encode('utf8')
        if len(packed) > max_bytes:
            raise ValueError('certificate byte budget exceeded')
        if type(certificate) is not dict or set(certificate) != {
            'format', 'cnf_sha256', 'weights_sha256', 'root', 'count', 'nodes'
        }:
            raise ValueError('invalid certificate envelope')
        if certificate['format'] != FORMAT or certificate['cnf_sha256'] != cnf.digest() or certificate['weights_sha256'] != weight_digest(weights):
            raise ValueError('formula/weights digest mismatch')
        nodes = certificate['nodes']
        if type(nodes) is not list or not 1 <= len(nodes) <= max_nodes:
            raise ValueError('invalid nodes')
        root = certificate['root']
        if type(root) is not int or root != len(nodes) - 1:
            raise ValueError('root must be final node')
        expected_count = decode_fraction(certificate['count'])
        seen: dict[int, tuple] = {}
        checked: dict[int, Fraction] = {}
        visiting: set[int] = set()

        def verify(idx: int, state):
            if type(idx) is not int or not 0 <= idx < len(nodes):
                raise ValueError('invalid node reference')
            if idx in visiting:
                raise ValueError('cycle')
            if idx in seen:
                if seen[idx] != state:
                    raise ValueError('node shared across different residual states')
                return checked[idx]
            node = nodes[idx]
            if type(node) is not dict:
                raise ValueError('invalid node')
            kind, data, sub = _rule(state)
            if set(node) != {'kind', 'count', 'children'} | set(data):
                raise ValueError('unexpected node fields')
            if node['kind'] != kind or any(type(node[k]) is not type(v) or node[k] != v for k, v in data.items()):
                raise ValueError('invalid residual rule')
            children = node['children']
            if type(children) is not list or len(children) != len(sub) or any(type(i) is not int or i < 0 or i >= idx for i in children):
                raise ValueError('invalid child references')
            visiting.add(idx)
            values = [verify(j, s) for j, s in zip(children, sub)]
            visiting.remove(idx)
            value = _transition(kind, data, state[0], values, weights, tuple(c[0] for c in sub))
            if decode_fraction(node['count']) != value:
                raise ValueError('incorrect rational node count')
            checked[idx] = value
            seen[idx] = state
            return value

        actual = verify(root, _root_state(cnf))
        if actual != expected_count or len(seen) != len(nodes):
            raise ValueError('root mismatch or unreachable certificate nodes')
        return True, 'independently verified exact rational weighted component DAG', encode_fraction(actual), len(seen)
    except (TypeError, ValueError, KeyError, OverflowError, RecursionError, WeightedLimit) as exc:
        return False, str(exc), None, 0
