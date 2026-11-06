"""Exact #SAT with a compact, independently checkable component-DAG certificate.

All operations are count preserving, including declared-but-unused variables.
The verifier reconstructs *every* residual CNF state from the original input;
it does not call the solver, trust submitted residuals, or assume component
independence. Every child reference must precede its parent (acyclic DAG).

This is an exact exponential worst-case reference, NOT the ETH algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from time import monotonic
from typing import Any

from veritas.core.cnf import CNF

FORMAT = 'veritas-component-count-dag-v1'
MAX_NODES = 80_000
MAX_BYTES = 8_000_000
MAX_VARS = 128

State = tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]


class CertificateLimit(Exception):
    pass


@dataclass
class DagCountResult:
    status: str
    count: int | None = None
    certificate: dict[str, Any] | None = None
    nodes: int = 0
    cache_hits: int = 0
    reason: str | None = None


def _norm(clauses: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    """Canonical CNF: erase duplicate literals, tautologies, duplicate clauses."""
    normalized = set()
    for clause in clauses:
        bits = set(clause)
        if any(-lit in bits for lit in bits):
            continue
        normalized.add(tuple(sorted(bits, key=lambda x: (abs(x), x))))
    return tuple(sorted(normalized, key=lambda c: (len(c), c)))


def _restrict(state: State, variable: int, value: bool) -> State:
    scope, clauses = state
    if variable not in scope:
        raise ValueError('variable not in scope')
    remaining = []
    for clause in clauses:
        if any(abs(lit) == variable and (lit > 0) == value for lit in clause):
            continue
        remaining.append(tuple(lit for lit in clause if abs(lit) != variable))
    return tuple(v for v in scope if v != variable), _norm(tuple(remaining))


def _components(clauses: tuple[tuple[int, ...], ...]) -> tuple[State, ...]:
    variables = {abs(lit) for clause in clauses for lit in clause}
    parent = {v: v for v in variables}

    def root(v: int) -> int:
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    def merge(a: int, b: int) -> None:
        aa, bb = root(a), root(b)
        if aa != bb:
            parent[max(aa, bb)] = min(aa, bb)

    for clause in clauses:
        if clause:
            start = abs(clause[0])
            for lit in clause[1:]:
                merge(start, abs(lit))
    groups: dict[int, list[tuple[int, ...]]] = {}
    for clause in clauses:
        if clause:
            groups.setdefault(root(abs(clause[0])), []).append(clause)
    pieces = []
    for part in groups.values():
        vs = tuple(sorted({abs(l) for c in part for l in c}))
        pieces.append((vs, tuple(sorted(part, key=lambda c: (len(c), c)))))
    return tuple(sorted(pieces, key=lambda p: p[0]))


def _rule(state: State) -> tuple[str, dict[str, Any], tuple[State, ...]]:
    """Deterministic independent reference reduction, evaluated by both sides."""
    scope, clauses = state
    if any(not clause for clause in clauses):
        return 'conflict', {}, ()
    if not clauses:
        return 'satisfied', {}, ()
    used = {abs(lit) for clause in clauses for lit in clause}
    if not used.issubset(scope):
        raise ValueError('clause references variable outside scope')
    free = len(scope) - len(used)
    if free:
        child = (tuple(v for v in scope if v in used), clauses)
        return 'free', {'free': free}, (child,)
    units = sorted((c[0] for c in clauses if len(c) == 1), key=lambda l: (abs(l), l))
    if units:
        lit = units[0]
        return 'unit', {'literal': lit}, (_restrict(state, abs(lit), lit > 0),)
    components = _components(clauses)
    if len(components) > 1:
        return 'product', {}, components
    # Deterministically choose the most frequently occurring variable in a
    # shortest clause, using a stable tie-break (no numerical solver input).
    shortest = clauses[0]
    occurrences = {v: 0 for v in used}
    for c in clauses:
        for lit in c:
            occurrences[abs(lit)] += 1
    var = min((abs(l) for l in shortest), key=lambda v: (-occurrences[v], v))
    return 'split', {'variable': var}, (
        _restrict(state, var, False), _restrict(state, var, True))


def _root_state(cnf: CNF) -> State:
    return tuple(range(1, cnf.n + 1)), _norm(cnf.clauses)


def _count_digits(value: Any, maximum: int) -> int:
    if (not isinstance(value, str) or not value or not value.isascii() or
            not value.isdecimal() or len(value) > 160 or
            (len(value) > 1 and value[0] == '0')):
        raise ValueError('invalid canonical count encoding')
    number = int(value)
    if number > maximum:
        raise ValueError('count exceeds declared assignment space')
    return number


def make_dag_count_certificate(cnf: CNF, *, timeout_s: float = 5,
                               max_nodes: int = 30_000,
                               max_bytes: int = MAX_BYTES) -> DagCountResult:
    if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 30:
        raise ValueError('timeout_s must be in (0,30]')
    if type(max_nodes) is not int or not 1 <= max_nodes <= MAX_NODES:
        raise ValueError('max_nodes outside permitted range')
    if type(max_bytes) is not int or not 256 <= max_bytes <= MAX_BYTES:
        raise ValueError('max_bytes outside permitted range')
    if cnf.n > MAX_VARS:
        return DagCountResult('UNKNOWN', reason=f'at most {MAX_VARS} variables supported')
    deadline = monotonic() + timeout_s
    memo: dict[State, int] = {}
    entries: list[dict[str, Any]] = []
    hits = 0

    def build(state: State) -> int:
        nonlocal hits
        if monotonic() >= deadline or len(entries) >= max_nodes:
            raise CertificateLimit('node/time budget exceeded')
        if state in memo:
            hits += 1
            return memo[state]
        kind, payload, children = _rule(state)
        child_ids = [build(child) for child in children]
        if kind == 'conflict':
            count = 0
        elif kind == 'satisfied':
            count = 1 << len(state[0])
        elif kind == 'free':
            count = (1 << payload['free']) * int(entries[child_ids[0]]['count'])
        elif kind == 'unit':
            count = int(entries[child_ids[0]]['count'])
        elif kind == 'product':
            count = 1
            for child_id in child_ids:
                count *= int(entries[child_id]['count'])
        else:
            count = sum(int(entries[child_id]['count']) for child_id in child_ids)
        node = {'kind': kind, 'count': str(count), **payload, 'children': child_ids}
        idx = len(entries)
        entries.append(node)
        memo[state] = idx
        return idx

    try:
        root = build(_root_state(cnf))
        count = int(entries[root]['count'])
        certificate = {'format': FORMAT, 'cnf_sha256': cnf.digest(), 'root': root,
                       'count': str(count), 'nodes': entries}
        packed = json.dumps(certificate, separators=(',', ':'), allow_nan=False).encode()
        if len(packed) > max_bytes:
            return DagCountResult('UNKNOWN', nodes=len(entries), cache_hits=hits,
                                  reason='certificate byte budget exceeded')
        return DagCountResult('COUNT', count, certificate, len(entries), hits)
    except (CertificateLimit, RecursionError, OverflowError) as error:
        return DagCountResult('UNKNOWN', nodes=len(entries), cache_hits=hits, reason=str(error))


def check_dag_count_certificate(cnf: CNF, certificate: Any, *,
                                max_nodes: int = MAX_NODES,
                                max_bytes: int = MAX_BYTES) -> tuple[bool, str, int | None, int]:
    """Independently check a DAG using only source clauses and structural rules.

    Even a malicious certificate with valid node counts cannot invent a free
    variable, omit a component, or share one node between unequal subproblems.
    """
    if type(max_nodes) is not int or not 1 <= max_nodes <= MAX_NODES:
        raise ValueError('invalid max_nodes')
    if type(max_bytes) is not int or not 256 <= max_bytes <= MAX_BYTES:
        raise ValueError('invalid max_bytes')
    try:
        packed = json.dumps(certificate, separators=(',', ':'), allow_nan=False).encode()
        if len(packed) > max_bytes:
            return False, 'certificate exceeds byte limit', None, 0
        if not isinstance(certificate, dict) or set(certificate) != {'format', 'cnf_sha256', 'root', 'count', 'nodes'}:
            return False, 'invalid certificate envelope', None, 0
        if certificate['format'] != FORMAT or certificate['cnf_sha256'] != cnf.digest():
            return False, 'wrong CNF hash or certificate format', None, 0
        nodes = certificate['nodes']
        if not isinstance(nodes, list) or not 1 <= len(nodes) <= max_nodes:
            return False, 'invalid number of nodes', None, 0
        root = certificate['root']
        if type(root) is not int or root != len(nodes)-1:
            return False, 'root must be final DAG node', None, 0
        count = _count_digits(certificate['count'], 1 << cnf.n)
        verified: dict[int, State] = {}
        checked: dict[int, int] = {}
        visiting: set[int] = set()

        def check(node_id: int, state: State) -> int:
            if node_id in visiting:
                raise ValueError('cycle in proof DAG')
            if node_id in verified:
                if verified[node_id] != state:
                    raise ValueError('DAG node reused for different residual formulas')
                return checked[node_id]
            if type(node_id) is not int or not 0 <= node_id < len(nodes):
                raise ValueError('invalid child index')
            node = nodes[node_id]
            if not isinstance(node, dict):
                raise ValueError('invalid DAG node')
            kind, expected, next_states = _rule(state)
            if set(node) != ({'kind', 'count', 'children'} | set(expected)):
                raise ValueError('unexpected node fields')
            if node['kind'] != kind or any(node[k] != v or type(node[k]) is not type(v)
                                             for k, v in expected.items()):
                raise ValueError('node rule does not match residual formula')
            children = node['children']
            if not isinstance(children, list) or len(children) != len(next_states):
                raise ValueError('wrong number of children')
            if any(type(cid) is not int or cid >= node_id or cid < 0 for cid in children):
                raise ValueError('children must be earlier DAG nodes')
            visiting.add(node_id)
            values = [check(cid, target) for cid, target in zip(children, next_states)]
            visiting.remove(node_id)
            if kind == 'conflict':
                actual = 0
            elif kind == 'satisfied':
                actual = 1 << len(state[0])
            elif kind == 'free':
                actual = values[0] << expected['free']
            elif kind == 'unit':
                actual = values[0]
            elif kind == 'product':
                actual = 1
                for v in values:
                    actual *= v
            else:
                actual = sum(values)
            if actual != _count_digits(node['count'], 1 << len(state[0])):
                raise ValueError('incorrect claimed node count')
            checked[node_id] = actual
            verified[node_id] = state
            return actual

        result = check(root, _root_state(cnf))
        if len(verified) != len(nodes):
            raise ValueError('unreachable extraneous certificate nodes')
        if result != count:
            raise ValueError('root count mismatch')
        return True, 'independently verified count-preserving component DAG', result, len(verified)
    except (TypeError, ValueError, KeyError, RecursionError, OverflowError) as error:
        return False, str(error), None, 0
