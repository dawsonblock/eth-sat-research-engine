"""Finite contraction by conditioning all wires crossing a partition of factors.

For each boundary assignment the two restricted graphs have disjoint free
wires. Their contraction product is the corresponding summand. All arithmetic
uses integer tensor entries captured at the root and a fixed output modulus.
"""

from collections import Counter, deque
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from time import monotonic

from veritas.research.tapered_v4.provenance import (
    SourceBindingError,
    manuscript_binding,
    source_binding,
)
from veritas.research.tensor import Factor, TensorNetwork, brute_contract

ALGORITHM = "VERITAS_FINITE_BOUNDARY_V1"


def _bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def _digest(value):
    return sha256(_bytes(value)).hexdigest()


def _source_identity():
    manuscript = manuscript_binding()
    if manuscript["pin_matches"] is not True:
        raise Incomplete("INCONCLUSIVE_SOURCE_MISMATCH", "pinned manuscript differs")
    return {
        "source_sha256": source_binding()["digest"],
        "manuscript": manuscript,
        "authentication": "UNSIGNED_HASH_MATCH_ONLY",
    }


def _network_data(network):
    return {
        "edges": network.edges,
        "factors": [
            {"ports": f.ports, "table": f.table, "label": f.label}
            for f in network.factors
        ],
    }


@dataclass(frozen=True)
class BoundaryPolicy:
    leaf_edges: int = 8
    # Eligible pieces run the existing finite packet + Hermite executor once.
    piece_method: str = "direct"
    max_boundary_calls: int = 12000
    max_work: int = 15_000_000
    max_seconds: float = 120
    max_certificate_bytes: int = 8_000_000
    verify_root: bool = True

    def __post_init__(self):
        for name, maximum in (
            ("leaf_edges", 8),
            ("max_boundary_calls", 100000),
            ("max_work", 100_000_000),
            ("max_certificate_bytes", 64_000_000),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f"invalid {name}")
        if (
            self.piece_method not in ("direct", "tapered")
            or type(self.verify_root) is not bool
        ):
            raise ValueError("unsupported finite piece policy")
        if (
            type(self.max_seconds) not in (int, float)
            or not 0 < self.max_seconds <= 240
        ):
            raise ValueError("invalid deadline")


class Incomplete(ValueError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def _require(condition, message):
    if not condition:
        raise Incomplete("INCONCLUSIVE_INVARIANT_FAILURE", message)


class _Run:
    def __init__(self, policy):
        self.policy = policy
        self.start = monotonic()
        self.work = 0
        self.counts = Counter()
        self.depth = 0
        self.proof_bytes = 0

    def charge(self, category, count=1):
        self.counts[category] += count
        self.work += count
        if (
            self.work > self.policy.max_work
            or monotonic() - self.start > self.policy.max_seconds
        ):
            raise Incomplete(
                "INCONCLUSIVE_RESOURCE_LIMIT", "boundary work or time limit"
            )

    def record(self, data):
        self.proof_bytes += len(_bytes(data))
        if self.proof_bytes > self.policy.max_certificate_bytes:
            raise Incomplete("INCONCLUSIVE_RESOURCE_LIMIT", "certificate size limit")

    def ledger(self):
        return {
            "work_units": self.work,
            "counters": dict(self.counts),
            "maximum_depth": self.depth,
            "wall_seconds": monotonic() - self.start,
            "complete_bit_work": False,
            "hard_memory_limit_enforced": False,
        }


def _owners(network):
    owners = [[] for _ in range(network.edges)]
    for i, factor in enumerate(network.factors):
        for edge in factor.ports:
            owners[edge].append(i)
    return owners


def _cut(network):
    owners = _owners(network)
    graph = [set() for _ in network.factors]
    for left, right in owners:
        graph[left].add(right)
        graph[right].add(left)
    order = []
    seen = set()
    for first in range(len(graph)):
        if first in seen:
            continue
        seen.add(first)
        queue = deque([first])
        while queue:
            index = queue.popleft()
            order.append(index)
            for neighbor in sorted(graph[index] - seen):
                seen.add(neighbor)
                queue.append(neighbor)
    best = None
    for stop in range(1, len(order)):
        left = set(order[:stop])
        wires = [[], [], []]
        for edge, (a, b) in enumerate(owners):
            side = (
                0
                if a in left and b in left
                else 1
                if a not in left and b not in left
                else 2
            )
            wires[side].append(edge)
        largest = max(len(wires[0]), len(wires[1]))
        if largest >= network.edges or largest > (network.edges + 1) // 2:
            continue
        score = (len(wires[2]), largest, stop)
        if best is None or score < best[0]:
            best = (
                score,
                (tuple(sorted(left)), tuple(sorted(order[stop:]))),
                tuple(map(tuple, wires)),
            )
    if best is None:
        raise Incomplete(
            "INCONCLUSIVE_UNSUPPORTED_PARTITION", "bounded partition search exhausted"
        )
    return best[1], best[2]


def _check_cut(network, groups, wires):
    _require(len(groups) == 2 and len(wires) == 3, "cut dimensions")
    left, right = groups
    _require(
        sorted(left + right) == list(range(len(network.factors))), "factor partition"
    )
    scopes = [{p for i in side for p in network.factors[i].ports} for side in groups]
    expected = (scopes[0] - scopes[1], scopes[1] - scopes[0], scopes[0] & scopes[1])
    _require(
        all(tuple(sorted(s)) == w for s, w in zip(expected, wires)),
        "incorrect cut incidence",
    )
    _require(
        all(
            len(w) < network.edges and len(w) <= (network.edges + 1) // 2
            for w in wires[:2]
        ),
        "child shrink condition",
    )


def _child(network, group, free, fixed, budget):
    numbering = {wire: i for i, wire in enumerate(free)}
    factors = []
    for index in group:
        original = network.factors[index]
        kept = [i for i, p in enumerate(original.ports) if p in numbering]
        offset = sum(fixed[p] << i for i, p in enumerate(original.ports) if p in fixed)
        budget.charge("restricted_entries", 1 << len(kept))
        table = tuple(
            original.table[
                offset + sum(((mask >> j) & 1) << slot for j, slot in enumerate(kept))
            ]
            for mask in range(1 << len(kept))
        )
        factors.append(
            Factor(
                tuple(numbering[original.ports[i]] for i in kept), table, original.label
            )
        )
    return TensorNetwork(len(free), tuple(factors))


def _check_child(network, child, group, free, fixed, budget):
    _require(
        child.edges == len(free) and len(child.factors) == len(group),
        "child dimensions",
    )
    for factor, index in zip(child.factors, group):
        parent = network.factors[index]
        expected = tuple(w for w in parent.ports if w not in fixed)
        _require(
            tuple(free[i] for i in factor.ports) == expected
            and factor.label == parent.label,
            "child port order or origin",
        )
        budget.charge("checked_entries", len(factor.table))
        for mask, entry in enumerate(factor.table):
            assignment = dict(fixed)
            assignment.update(
                {w: bool(mask & (1 << j)) for j, w in enumerate(expected)}
            )
            _require(
                entry == parent.value(assignment),
                "restricted coefficient differs from parent",
            )


def _admit(network, precision):
    if (
        type(network) is not TensorNetwork
        or type(precision) is not int
        or not 1 <= precision <= 512
    ):
        raise ValueError("integer TensorNetwork and precision in 1..512 required")
    if (
        network.edges > 16
        or len(network.factors) > 128
        or sum(len(f.table) for f in network.factors) > 131072
        or any(
            len(f.label) > 256 or any(v.bit_length() > 512 for v in f.table)
            for f in network.factors
        )
    ):
        raise Incomplete(
            "INCONCLUSIVE_RESOURCE_LIMIT",
            "explicit tensor dimensions or entry width exceed cap",
        )


def _direct_leaf(network, modulus, budget):
    budget.charge(
        "leaf_factor_visits", (1 << network.edges) * (1 + len(network.factors))
    )
    total = 0
    for mask in range(1 << network.edges):
        term = 1
        for factor in network.factors:
            index = sum(((mask >> p) & 1) << j for j, p in enumerate(factor.ports))
            term = term * factor.table[index] % modulus
        total += term
    return total % modulus


def _tapered_piece(network, precision, budget):
    from veritas.research.eth_arithmetic.gf2 import first_irreducible
    from veritas.research.eth_recursive_contraction_v39.described_network import (
        describe_integer_network,
    )
    from veritas.research.tapered_v4.model import RecursionPolicy, TaperedState
    from veritas.research.tapered_v4.recursor import contract_recursive

    polynomial = first_irreducible(5)
    described = describe_integer_network(
        network, creation_precision=precision, defining_polynomial=polynomial
    )
    state = TaperedState(described, 0, precision, polynomial, 1, network.edges)
    available = budget.policy.max_work - budget.work
    seconds = min(60.0, budget.policy.max_seconds / 2)
    if (
        available < 1
        or monotonic() - budget.start + seconds > budget.policy.max_seconds
    ):
        raise Incomplete(
            "INCONCLUSIVE_RESOURCE_LIMIT", "insufficient reserved piece budget"
        )
    policy = RecursionPolicy(
        max_active_wires=8,
        leaf_edge_limit=network.edges - 1,
        finite_parameters=(1, 1, 4),
        max_depth=2,
        max_seconds=seconds,
        max_work=min(4_000_000, available),
        max_certificate_bytes=30_000_000,
    )
    report = contract_recursive(state, policy)
    if report["status"] != "EXACT_MODULAR_CONTRACTION_FINITE":
        raise Incomplete(report["status"], report.get("reason", "tapered piece failed"))
    result = report["result"]
    _require(
        len(result) == 1 and not any(result[0][1:]),
        "integer piece produced extension coordinates",
    )
    ledger = report["ledger"]
    _require(
        ledger["maximum_child_edges"] < network.edges, "tapered piece did not shrink"
    )
    budget.charge("tapered_piece_work", ledger["observed_work_units"])
    for name in (
        "generated_children",
        "retained_tuples",
        "hermite_recoveries",
        "point_evaluations",
        "algorithm_leaf_work",
        "recursive_calls",
    ):
        budget.counts["tapered_" + name] += ledger["counters"].get(name, 0)
    return result[0][0], {
        "method": "FINITE_SCALED_V1",
        "certificate_sha256": report["certificate"]["evidence_sha256"],
        "child_calls": ledger["counters"]["generated_children"],
        "depth": ledger["maximum_depth"],
    }


def _visit(network, precision, depth, run):
    run.charge("recursive_calls")
    if run.counts["recursive_calls"] > run.policy.max_boundary_calls:
        raise Incomplete("INCONCLUSIVE_RESOURCE_LIMIT", "boundary call limit")
    run.depth = max(run.depth, depth)
    node = {
        "parent_sha256": _digest(_network_data(network)),
        "wires": network.edges,
        "precision": precision,
    }
    modulus = 1 << precision
    if network.edges <= run.policy.leaf_edges:
        if network.edges and run.policy.piece_method == "tapered":
            value, nested = _tapered_piece(network, precision, run)
            node["piece"] = nested
            run.depth = max(run.depth, depth + nested["depth"])
        else:
            value = _direct_leaf(network, modulus, run)
            node["method"] = "direct_leaf"
        node["value"] = value
        run.record(node)
        return value, node

    groups, wires = _cut(network)
    _check_cut(network, groups, wires)
    node.update(
        method="boolean_boundary",
        groups=groups,
        child_wires=wires[:2],
        boundary=wires[2],
    )
    run.record(node)
    terms = []
    total = 0
    for mask in range(1 << len(wires[2])):
        run.charge("boundary_tuples")
        fixed = {p: (mask >> j) & 1 for j, p in enumerate(wires[2])}
        children = []
        term = 1
        for group, free in zip(groups, wires[:2]):
            child = _child(network, group, free, fixed, run)
            _check_child(network, child, group, free, fixed, run)
            child_value, child_proof = _visit(child, precision, depth + 1, run)
            children.append(child_proof)
            term = term * child_value % modulus
        total = (total + term) % modulus
        run.record({"mask": mask, "coefficient": 1, "product": term})
        terms.append(
            {"mask": mask, "coefficient": 1, "product": term, "children": children}
        )
    _require(
        len(terms) == 2 ** len(wires[2])
        and all(t["mask"] == i for i, t in enumerate(terms)),
        "incomplete boundary assignment domain",
    )
    node.update(terms=terms, value=total)
    return total, node


def contract_boundary(network, *, precision, policy=BoundaryPolicy()):
    """Return a residue and deterministic replay certificate, or a structured refusal."""
    if type(policy) is not BoundaryPolicy:
        raise TypeError("BoundaryPolicy required")
    run = _Run(policy)
    try:
        _admit(network, precision)
        identity = _source_identity()
        value, tree = _visit(network, precision, 0, run)
        if policy.verify_root:
            run.charge(
                "oracle_factor_visit_bound",
                (1 << network.edges) * (1 + len(network.factors)),
            )
            expected = brute_contract(
                network,
                max_edges=16,
                modulus=1 << precision,
                timeout_s=max(0.0, policy.max_seconds - (monotonic() - run.start)),
            )
            _require(expected == value, "independent direct parent contraction differs")
        run.charge("completion_checks")
        certificate = {
            "schema": ALGORITHM,
            "policy": asdict(policy),
            "input": _network_data(network),
            "source": identity,
            "creation_precision": precision,
            "tree": tree,
            "result": value,
        }
        if len(_bytes(certificate)) > policy.max_certificate_bytes:
            raise Incomplete(
                "INCONCLUSIVE_RESOURCE_LIMIT", "final certificate size limit"
            )
        return {
            "status": "EXACT_FINITE_BOUNDARY_CONTRACTION",
            "result": value,
            "certificate": certificate,
            "direct_parent_checked": policy.verify_root,
            "ledger": run.ledger(),
            "theorem_qualified": False,
        }
    except (
        ValueError,
        TypeError,
        ArithmeticError,
        OSError,
        SourceBindingError,
        MemoryError,
    ) as exc:
        return {
            "status": getattr(
                exc,
                "status",
                "INCONCLUSIVE_RESOURCE_LIMIT"
                if isinstance(exc, (TimeoutError, MemoryError))
                else "INCONCLUSIVE_SOURCE_MISMATCH"
                if isinstance(exc, (OSError, SourceBindingError))
                else "INCONCLUSIVE_INVALID_INPUT",
            ),
            "reason": str(exc),
            "ledger": run.ledger(),
        }


def replay_boundary(network, certificate, *, precision, policy=BoundaryPolicy()):
    """Reconstruct every restriction and nested contraction from the caller's input and policy."""
    if not isinstance(certificate, dict) or certificate.get("schema") != ALGORITHM:
        return {"valid": False, "status": "INVALID_BOUNDARY_CERTIFICATE"}
    regenerated = contract_boundary(network, precision=precision, policy=policy)
    if "certificate" not in regenerated:
        return {"valid": False, "status": regenerated["status"]}
    try:
        same = _bytes(certificate) == _bytes(regenerated["certificate"])
    except (TypeError, ValueError, RecursionError):
        same = False
    return {
        "valid": same,
        "status": "FINITE_BOUNDARY_REPLAYED"
        if same
        else "INVALID_BOUNDARY_CERTIFICATE",
    }
