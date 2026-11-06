"""Independent finite boundary proof-tree consumer. Never invokes the production cut or gather."""

from dataclasses import asdict
from itertools import product
from time import monotonic
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.finite_reductions.boundary import (
    BoundaryPolicy,
    _Run,
    _admit,
    _bytes,
    _digest,
    _network_data,
    _source_identity,
)
from veritas.research.finite_reductions.elimination import verify_steps


def _restrict(parent, indices, free, boundary, mask, run):
    assignment = {e: bool(mask & (1 << j)) for j, e in enumerate(boundary)}
    factors = []
    for i in indices:
        f = parent.factors[i]
        keep = [p for p in f.ports if p in free]
        run.charge("reference_restricted_entries", 1 << len(keep))
        table = []
        for bits in product((False, True), repeat=len(keep)):
            # product makes its last bit fastest; reverse when binding original ports.
            assignment.update(zip(keep, reversed(bits)))
            table.append(f.value(assignment))
        factors.append(Factor(tuple(free.index(w) for w in keep), table, f.label))
    return TensorNetwork(len(free), tuple(factors))


def verify_boundary_tree(network, cert, *, precision, policy=BoundaryPolicy()):
    run = _Run(policy)
    states = set()
    maxchild = 0
    try:
        _admit(network, precision)
        norm = asdict(policy)
        schema = "VERITAS_FINITE_BOUNDARY_ELIMINATION_V2"
        if policy.on_call_overflow == "refuse":
            norm.pop("on_call_overflow")
            schema = "VERITAS_FINITE_BOUNDARY_V1"
        header = {
            "schema": schema,
            "policy": norm,
            "input": _network_data(network),
            "source": _source_identity(),
            "creation_precision": precision,
        }
        if set(cert) != set(header) | {"tree", "result"} or any(
            _bytes(cert[k]) != _bytes(v) for k, v in header.items()
        ):
            raise ValueError("external input or policy differs")
        if len(_bytes(cert)) > policy.max_certificate_bytes:
            raise ValueError("certificate size cap")
        modulus = 1 << precision

        def visit(net, node, d):
            nonlocal maxchild
            run.charge("recursive_calls")
            run.depth = max(d, run.depth)
            if d:
                maxchild = max(maxchild, net.edges)
            ident = _digest(_network_data(net))
            states.add((ident, precision))
            if (
                run.counts["recursive_calls"] > policy.max_boundary_calls
                or node["parent_sha256"] != ident
                or type(node["wires"]) is not int
                or node["wires"] != net.edges
                or type(node["precision"]) is not int
                or node["precision"] != precision
            ):
                raise ValueError("node dependency differs")
            method = node["method"]
            extras = {
                "direct_leaf": set(),
                "boolean_boundary": {"groups", "child_wires", "boundary", "terms"},
                "certified_elimination": {
                    "steps",
                    "remaining_calls",
                    "required_child_visits",
                    "boundary",
                    "candidate_groups",
                    "candidate_free",
                },
            }
            if (
                method not in extras
                or set(node)
                != {"parent_sha256", "precision", "wires", "value", "method"}
                | extras[method]
            ):
                raise ValueError("unexpected node schema")
            if (
                method == "direct_leaf"
                and net.edges <= policy.leaf_edges
                and (net.edges == 0 or policy.piece_method == "direct")
            ):
                value = 0
                run.charge(
                    "direct_leaf_work_bound", (len(net.factors) + 1) * (1 << net.edges)
                )
                for bits in product((False, True), repeat=net.edges):
                    env = dict(enumerate(bits))
                    term = 1
                    for f in net.factors:
                        term = (term * f.value(env)) % modulus
                    value = (value + term) % modulus
            elif (
                method == "certified_elimination"
                and policy.on_call_overflow == "certified_elimination"
                and net.edges > policy.leaf_edges
            ):
                # Policy replay separately checks the canonical cut; independently establish its incidence here.
                groups = node["candidate_groups"]
                boundary = node["boundary"]
                _check_partition(net, groups, boundary, node["candidate_free"])
                required = 2 * (1 << len(boundary))
                available = policy.max_boundary_calls - run.counts["recursive_calls"]
                if (
                    required <= available
                    or node["required_child_visits"] != required
                    or node["remaining_calls"] != available
                ):
                    raise ValueError("elimination trigger differs")
                value = node["value"]
                verify_steps(net, precision, node["steps"], value, run)
            elif method == "boolean_boundary" and net.edges > policy.leaf_edges:
                groups = node["groups"]
                boundary = node["boundary"]
                free = node["child_wires"]
                _check_partition(net, groups, boundary, free)
                terms = node["terms"]
                if len(terms) != 1 << len(boundary):
                    raise ValueError("missing boundary assignment")
                value = 0
                for mask, term in enumerate(terms):
                    if set(term) != {"mask", "coefficient", "product", "children"}:
                        raise ValueError("unexpected term schema")
                    if (
                        type(term["mask"]) is not int
                        or term["mask"] != mask
                        or type(term["coefficient"]) is not int
                        or term["coefficient"] != 1
                        or len(term["children"]) != 2
                    ):
                        raise ValueError("invalid term")
                    run.charge("boundary_assignments")
                    factors = [
                        visit(
                            _restrict(net, groups[j], free[j], boundary, mask, run),
                            term["children"][j],
                            d + 1,
                        )
                        for j in range(2)
                    ]
                    part = factors[0] * factors[1] % modulus
                    if type(term["product"]) is not int or part != term["product"]:
                        raise ValueError("incorrect product")
                    value = (value + part) % modulus
            else:
                raise ValueError("unsupported proof node or policy")
            if type(node["value"]) is not int or node["value"] != value:
                raise ValueError("incorrect node value")
            return value

        value = visit(network, cert["tree"], 0)
        if type(cert["result"]) is not int or cert["result"] != value:
            raise ValueError("incorrect root")
        run.charge("verification_complete")
        return {
            "status": "FINITE_BOUNDARY_TREE_CHECKED",
            "result": value,
            "distinct_states": len(states),
            "maximum_child_wires": maxchild,
            "ledger": run.ledger(),
            "actual_machine_bit_operations": None,
        }
    except (
        OSError,
        KeyError,
        ValueError,
        RuntimeError,
        ArithmeticError,
        TypeError,
        IndexError,
        MemoryError,
    ) as exc:
        return {"status": "INCONCLUSIVE_OR_INVALID_BOUNDARY_TREE", "reason": str(exc)}


def _check_partition(net, groups, boundary, free):
    if (
        len(groups) != 2
        or len(free) != 2
        or any(type(i) is not int for g in groups for i in g)
        or sorted([i for g in groups for i in g]) != list(range(len(net.factors)))
    ):
        raise ValueError("factor occurrence coverage")
    sides = [{e for i in group for e in net.factors[i].ports} for group in groups]
    a, b = sides
    for actual, expected in zip([*free, boundary], [a - b, b - a, a & b]):
        if any(type(w) is not int for w in actual) or list(actual) != sorted(expected):
            raise ValueError("wire partition")
    if any(len(w) >= net.edges or len(w) > (net.edges + 1) // 2 for w in free):
        raise ValueError("nonshrinking cut")
