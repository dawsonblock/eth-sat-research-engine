"""One finite parent-to-ALL-children identity, with two verification routes.

Scope, stated up front
----------------------

This module certifies **one recursion level**: a single parent described
network, its complete finite admissible mode domain at every interpolation
node and residue point required by the tapered plan, and every group child
derived from every admissible tuple.  It does *not* certify recursion, the
manuscript schedule, or a complexity bound.  Those remain
``INCONCLUSIVE_SOURCE_ACTIVE_PATH_NOT_IMPLEMENTED``.

The identity
------------

For every required node ``t`` and residue point ``zeta`` of the tapered plan,

    ParentValue(t, zeta)  ==  SUM over every admissible beta of
                                  weight(beta, t) * Product over groups
                                                     ChildValue(group, beta, t, zeta)

with every factor evaluated in the exact truncated ring
``(Z/2^p Z)[U]/(f)`` at the node's precision.  In this finite construction
``weight(beta, t)`` is the multiplicative unit (each tuple contributes once),
so the sum is the plain sum of the tuple terms; the certificate records the
declared weight, the valuation lower bound and the multiplicity bound anyway so
the accounting is auditable.

Two routes
----------

``build_certificate`` (producer)
    Streams the tuples, builds each group child, contracts it, accumulates.

``verify_certificate`` (consumer)
    Re-derives the packing source, the point modes and the complete ordered
    tuple domain **from the parent and the declared parameters**.  It never
    reads the producer's tuple list to decide what to compute; it compares that
    list against its own enumeration afterwards.  It recomputes every child
    contribution and recomputes the parent side with the independent half-edge
    oracle.

What the consumer trusts
------------------------

The *parent network object* it is handed (bound by digest), the pinned
manuscript hash, and the shared low-level ring/packing/child builders.  It does
not trust the producer's counts, ordering, digests or arithmetic.  A digest
proves byte identity, never mathematical provenance.
"""
from __future__ import annotations

from hashlib import sha256

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.source_hermite import (
    make_source_tapered_plan, validate_source_tapered_plan)
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_sparse_mode_source)
from veritas.research.eth_recursive_contraction_v39.described_network import (
    DescribedNetwork, contract_described_network)
from veritas.research.eth_recursive_contraction_v39.lazy_children import (
    ChildEvaluationBudgetExceeded, _Budget as OracleBudget)
from veritas.research.eth_recursive_contraction_v39.point_children import (
    _build_point_children_checked, _direct_point_oracle, _ring_for)
from veritas.research.eth_recursive_contraction_v39.point_modes import (
    make_point_modes)
from veritas.research.eth_recursive_contraction_v39.structural_tuples import (
    structural_tuples)

from .canonical import domain_digest
from .child_recipe_check import verify_constructed_child_recipes
from .recursor import _network_digest
from .validators import CERTIFICATE_SCHEMA, validate_certificate_document

CLAIM = "FINITE_ONE_LEVEL_PARENT_TO_ALL_CHILDREN"
ENUMERATION_RULE = ("structural_tuples(modes, precision): every exponent vector "
                    "componentwise within each mode's row capacity, with total "
                    "weight < precision, in deterministic lexicographic order")
SCOPE = "ONE_RECURSION_LEVEL_FINITE"
OMITTED = [
    "recursion below the first level (children are leaves of this certificate)",
    "the manuscript source-active schedule and its parameter regime",
    "any asymptotic time or space bound",
    "uniform mode completeness for parameters outside the certified domain",
]


class CertificateRefusal(RuntimeError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status
        self.reason = reason


class ParentChildLimits:
    """Explicit finite bounds.  Every one of them fails closed."""

    __slots__ = ("max_edges", "max_points", "max_tuples", "max_children",
                 "max_work", "max_seconds", "max_extension_degree",
                 "max_precision_bits", "max_jet_length")

    def __init__(self, *, max_edges=4, max_points=16, max_tuples=512,
                 max_children=64, max_work=2_000_000, max_seconds=30.0,
                 max_extension_degree=8, max_precision_bits=256,
                 max_jet_length=4):
        for name, value, ceiling in (
                ("max_edges", max_edges, 8), ("max_points", max_points, 64),
                ("max_tuples", max_tuples, 4096),
                ("max_children", max_children, 256),
                ("max_work", max_work, 2_000_000),
                ("max_extension_degree", max_extension_degree, 8),
                ("max_precision_bits", max_precision_bits, 1024),
                ("max_jet_length", max_jet_length, 8)):
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"invalid {name}")
            setattr(self, name, value)
        if type(max_seconds) not in (int, float) or not 0 < max_seconds <= 30:
            raise ValueError("invalid max_seconds")
        self.max_seconds = float(max_seconds)

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__slots__}


def _parameters(extension_degree, precision, jet_length, a, u, radix):
    for name, value, low, high in (
            ("extension_degree", extension_degree, 1, 8),
            ("precision", precision, 1, 1024),
            ("jet_length", jet_length, 1, 8),
            ("a", a, 1, 8), ("u", u, 1, 8), ("radix", radix, 2, 64)):
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"invalid {name}")
    return {"extension_degree": extension_degree, "precision": precision,
            "jet_length": jet_length, "a": a, "u": u, "radix": radix,
            "packet_size": 1 << a,
            "polynomial": first_irreducible(extension_degree)}


def _plan_and_source(parent, parameters, limits):
    plan = make_source_tapered_plan(
        M=parent.edges, a=parameters["a"], u=parameters["u"],
        p=parameters["precision"],
        max_precision_bits=limits.max_precision_bits)
    validate_source_tapered_plan(plan, max_precision_bits=limits.max_precision_bits,
                                 max_terms=128)
    source = implicit_sparse_mode_source(
        construct_implicit_packing(parent.bipartite_edges(),
                                   r=parameters["radix"],
                                   a=parameters["a"],
                                   max_work=limits.max_work))
    if source["r"] != parameters["radix"] or source["L"] != parameters["packet_size"]:
        raise CertificateRefusal("INVALID_CERTIFICATE",
                                 "packing parameters differ from the declaration")
    if [list(edge) for edge in parent.bipartite_edges()] != source["edges"]:
        raise CertificateRefusal("INVALID_CERTIFICATE",
                                 "packing endpoints differ from the parent")
    return plan, source


def _points_for(node, parameters, limits):
    base = ExtensionRing(node.precision_bits, parameters["polynomial"])
    count = min(limits.max_points, max(1, (2 * (1 << parameters["a"]))))
    return base, distinct_residue_points(base, count, max_points=limits.max_points)


def _point_modes(parent, source, node, point, parameters, limits):
    modes = make_point_modes(
        source, node=node.t, precision=node.precision_bits,
        extension_degree=parameters["extension_degree"], zeta=point,
        max_tuples=limits.max_tuples, max_parent_wires=limits.max_edges)
    ring, checked_source = _ring_for(parent, modes,
                                     max_parent_wires=limits.max_edges)
    return modes, ring, checked_source


def _tuples(modes, precision, limits):
    return list(structural_tuples(modes["modes"], precision,
                                  max_tuples=limits.max_tuples))


def _child_term(parent, modes, beta, ring, source, limits):
    children = _build_point_children_checked(parent, modes, beta, ring, source)
    if len(children) > limits.max_children:
        raise CertificateRefusal("INCONCLUSIVE_RESOURCE_LIMIT",
                                 "group child count exceeds the cap")
    verify_constructed_child_recipes(parent, source, modes, beta, children, ring)
    term = ring.one
    rows = []
    for child in children:
        out = contract_described_network(child.network, ring,
                                         max_work=limits.max_work,
                                         timeout_s=limits.max_seconds,
                                         max_edges=limits.max_edges)
        term = ring.mul(term, out["result"])
        rows.append({"group": child.group, "edges": child.network.edges,
                     "value": [list(row) for row in out["result"]]})
    return term, rows


def build_certificate(parent, *, precision, jet_length, a, u, radix,
                      limits=None, source_context=None, extension_degree=None):
    """Stream every admissible tuple and emit one immutable certificate."""
    limits = limits or ParentChildLimits()
    if not isinstance(parent, DescribedNetwork):
        raise TypeError("described parent network required")
    if parent.edges > limits.max_edges:
        raise CertificateRefusal("INCONCLUSIVE_RESOURCE_LIMIT",
                                 "parent exceeds the certified edge cap")
    degree = extension_degree if extension_degree is not None else 2
    parameters = _parameters(degree, precision, jet_length, a, u, radix)
    plan, source = _plan_and_source(parent, parameters, limits)

    budget_used = 0
    points_required = 0
    points_checked = 0
    point_records = []
    domains = []

    for node in plan.nodes:
        base, points = _points_for(node, parameters, limits)
        points_required += len(points)
        for point_index, point in enumerate(points):
            modes, ring, checked_source = _point_modes(
                parent, source, node, point, parameters, limits)
            tuples = _tuples(modes, node.precision_bits, limits)
            listed = [[int(value) for value in beta] for beta in tuples]
            domains.append({
                "node": node.t, "point_index": point_index,
                "mode_count": len(modes["modes"]),
                "weights": [mode["weight"] for mode in modes["modes"]],
                "packets": [mode["packet"] for mode in modes["modes"]],
                "target_groups": [mode["target_group"] for mode in modes["modes"]],
                "source_groups": [mode["source_group"] for mode in modes["modes"]],
                "ordered_tuples": listed,
                "cardinality": len(listed),
                "mode_set_digest": sha256(repr(sorted(
                    (mode["packet"], mode["source_group"], mode["target_group"],
                     mode["weight"]) for mode in modes["modes"])).encode()).hexdigest(),
            })
            total = ring.zero
            terms = []
            for beta in tuples:
                term, child_rows = _child_term(parent, modes, beta, ring,
                                               checked_source, limits)
                budget_used += 1 + len(child_rows)
                total = ring.add(total, term)
                terms.append({"beta": [int(value) for value in beta],
                              "term": [list(row) for row in term],
                              "children": child_rows})
            oracle = _direct_point_oracle(parent, source, node.t, point, ring,
                                          OracleBudget(limits.max_work,
                                                       limits.max_seconds))
            if total != oracle:
                raise CertificateRefusal(
                    "INVALID_CERTIFICATE",
                    f"parent value differs from the complete tuple sum at node "
                    f"{node.t}, point {point_index}")
            points_checked += 1
            point_records.append({
                "node": node.t, "point_index": point_index,
                "point": list(point),
                "precision": node.precision_bits,
                "multiplicity": node.multiplicity,
                "tuple_count": len(tuples),
                "parent_value": [list(row) for row in oracle],
                "tuple_sum": [list(row) for row in total],
                "identity_holds": True,
                "terms": terms,
            })

    document = {
        "schema": CERTIFICATE_SCHEMA,
        "claim": CLAIM,
        "parent": {
            "network_digest": _network_digest(parent, _DigestBudget()),
            "source_context_digest": (None if source_context is None else
                                      domain_digest("source.context", source_context)),
            "edges": parent.edges,
            "depth": 0,
            "parameters": dict(parameters),
            "row_port_order": [list(v.ports) for v in parent.vertices
                               if v.side == "row"],
            "column_port_order": [list(v.ports) for v in parent.vertices
                                  if v.side == "column"],
            "maximum_degree": max((len(v.ports) for v in parent.vertices),
                                  default=0),
            "precision": precision,
        },
        "modes": {
            "domains": domains,
            "enumeration_rule": ENUMERATION_RULE,
            "exponent_bound": max((sum(entry["ordered_tuples"][i])
                                   for entry in domains
                                   for i in range(entry["cardinality"])),
                                  default=0),
            "point_domain_count": len(domains),
        },
        "children": [{"node": record["node"],
                      "point_index": record["point_index"],
                      "tuple_count": record["tuple_count"],
                      "groups": sorted({child["group"]
                                        for term in record["terms"]
                                        for child in term["children"]})}
                     for record in point_records],
        "coverage": {
            "points_checked": points_checked,
            "points_required": points_required,
            "classification": ("FULL_COVERAGE" if points_checked == points_required
                               and points_required > 0 else "PARTIAL_COVERAGE"),
        },
        "budgets": {"max_work": limits.max_work, "work_used": budget_used,
                    "max_points": limits.max_points,
                    "max_children": limits.max_children,
                    "max_enumeration": limits.max_tuples,
                    "limits": limits.as_dict()},
        "theorem_scope": {"theorem_mode_enabled": False, "scope": SCOPE,
                          "omitted_modes": OMITTED},
        "points": point_records,
        "refusals": [],
        "trust_class": "HASH_MATCH_UNSIGNED",
    }
    document["digest"] = domain_digest("parent.child.certificate", document)
    return document


class _DigestPolicy:
    max_description_bytes = 16_000_000


class _DigestBudget:
    """Minimal budget object accepted by the network digest routine."""

    def __init__(self):
        self.used = 0
        self.policy = _DigestPolicy()

    def charge(self, name, amount=1):
        self.used += amount

    def check(self):
        return None


def verify_certificate(document, *, parent, limits=None):
    """Independent consumer: rebuild the domain, recompute every term.

    Returns a structured verdict.  A partial or failed verification never
    reports ``FULL_COVERAGE``.
    """
    limits = limits or ParentChildLimits()
    try:
        validate_certificate_document(document)
    except ValueError as exc:
        return {"valid": False, "status": "INVALID_CERTIFICATE",
                "reason": str(exc), "points_checked": 0,
                "points_required": 0, "classification": "PARTIAL_COVERAGE",
                "theorem_mode_enabled": False}
    if not isinstance(parent, DescribedNetwork):
        return {"valid": False, "status": "INVALID_CERTIFICATE",
                "reason": "described parent network required",
                "points_checked": 0, "points_required": 0,
                "classification": "PARTIAL_COVERAGE",
                "theorem_mode_enabled": False}
    parameters = dict(document["parent"]["parameters"])
    if parent.edges != document["parent"]["edges"]:
        return _fail("parent edge count differs from the certificate")
    digest = _network_digest(parent, _DigestBudget())
    if digest != document["parent"]["network_digest"]:
        return _fail("parent network digest differs from the certificate")
    if document["parent"]["row_port_order"] != [list(v.ports) for v in parent.vertices
                                                if v.side == "row"]:
        return _fail("row port order differs from the parent")
    if document["parent"]["column_port_order"] != [list(v.ports) for v in parent.vertices
                                                   if v.side == "column"]:
        return _fail("column port order differs from the parent")
    try:
        plan, source = _plan_and_source(parent, parameters, limits)
    except (CertificateRefusal, ValueError) as exc:
        return _fail(f"the declared parameters do not reproduce the packing: {exc}")

    checked = 0
    required = 0
    declared = {(entry["node"], entry["point_index"]): entry
                for entry in document["modes"]["domains"]}
    if len(declared) != len(document["modes"]["domains"]):
        return _fail("duplicate per-point domain entries")
    for node in plan.nodes:
        base, points = _points_for(node, parameters, limits)
        required += len(points)
        for point_index, point in enumerate(points):
            modes, ring, checked_source = _point_modes(
                parent, source, node, point, parameters, limits)
            # The consumer enumerates the domain itself, then compares.
            tuples = _tuples(modes, node.precision_bits, limits)
            listed = [[int(value) for value in beta] for beta in tuples]
            entry = declared.get((node.t, point_index))
            if entry is None:
                return _fail("the certificate omits a required point domain")
            if entry["ordered_tuples"] != listed:
                return _fail("the declared tuple domain differs from an "
                             "independent enumeration")
            if entry["cardinality"] != len(listed):
                return _fail("the declared cardinality is wrong")
            recomputed = {
                "mode_count": len(modes["modes"]),
                "weights": [mode["weight"] for mode in modes["modes"]],
                "packets": [mode["packet"] for mode in modes["modes"]],
                "target_groups": [mode["target_group"] for mode in modes["modes"]],
                "source_groups": [mode["source_group"] for mode in modes["modes"]],
            }
            for name, value in recomputed.items():
                if name in entry and entry[name] != value:
                    return _fail(f"the declared {name} differs from the "
                                 f"recomputed mode construction")
            total = ring.zero
            for beta in tuples:
                term, _ = _child_term(parent, modes, beta, ring, checked_source,
                                      limits)
                total = ring.add(total, term)
            oracle = _direct_point_oracle(parent, source, node.t, point, ring,
                                          OracleBudget(limits.max_work,
                                                       limits.max_seconds))
            if total != oracle:
                return _fail(f"recomputed tuple sum differs from the parent at "
                             f"node {node.t}, point {point_index}")
            record = _record(document, node.t, point_index)
            if record is None:
                return _fail("the certificate omits a required point")
            if record["parent_value"] != [list(row) for row in oracle]:
                return _fail("recorded parent value differs from the recomputation")
            if record["tuple_sum"] != [list(row) for row in total]:
                return _fail("recorded tuple sum differs from the recomputation")
            if record["tuple_count"] != len(tuples):
                return _fail("recorded tuple count differs from the enumeration")
            checked += 1
    full = checked == required and required > 0
    return {
        "valid": full,
        "status": "FINITE_PARENT_CHILD_IDENTITY_VERIFIED" if full
                  else "INCONCLUSIVE_INCOMPLETE_POINT_COVERAGE",
        "points_checked": checked,
        "points_required": required,
        "classification": "FULL_COVERAGE" if full else "PARTIAL_COVERAGE",
        "certificate_digest": document.get("digest"),
        "theorem_mode_enabled": False,
        "scope": SCOPE,
        "trust_class": "HASH_MATCH_UNSIGNED",
    }


def _record(document, node, point_index):
    for record in document["points"]:
        if record["node"] == node and record["point_index"] == point_index:
            return record
    return None


def _fail(reason):
    return {"valid": False, "status": "INVALID_CERTIFICATE", "reason": reason,
            "points_checked": 0, "points_required": 0,
            "classification": "PARTIAL_COVERAGE",
            "theorem_mode_enabled": False}
