"""Immutable R9.8 wire contracts. Hashes bind bytes; they do not prove semantics."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
from functools import cached_property
from copy import deepcopy
from time import monotonic

from veritas.research.bounded_integer_encoding import (
    canonical_integer_json,
    decode_integer_object,
)
from veritas.research.paper_verification.source_registry import PIN, source_registry
from veritas.research.tapered_v4.source_recipes import (
    EntryBudget,
    EntryLimits,
    compile_entry,
)
from veritas.research.tapered_v4.source_state import (
    SourceContext,
    SourceNode,
    SourceTensorReference,
    SourceVertex,
)


class Semantics(str, Enum):
    FINITE_SCALED_EXPERIMENT = "FINITE_SCALED_EXPERIMENT"
    FINITE_BOUNDARY_EXACT = "FINITE_BOUNDARY_EXACT"
    SOURCE_QUALIFIED = "SOURCE_QUALIFIED"


class Refusal(ValueError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def canonical(value):
    return canonical_integer_json(value)


def digest(value):
    return sha256(value if type(value) is bytes else canonical(value)).hexdigest()


def decode(raw, *, cap=20_000_000):
    if type(raw) is not bytes or len(raw) > cap:
        raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "serialized byte cap")

    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("duplicate JSON field")
            result[k] = v
        return decode_integer_object(result)

    def integer(s):
        if len(s) > 400:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "integer byte cap")
        return int(s)

    def invalid(_):
        raise ValueError("noninteger JSON number")

    value = json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_int=integer,
        parse_float=invalid,
        parse_constant=invalid,
    )
    if canonical(value) != raw:
        raise ValueError("noncanonical JSON")
    return value


def natural(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("invalid " + name)


def hash_string(value):
    if (
        type(value) is not str
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("invalid digest")


def layout_group_count(parent, layout):
    """Admit a bounded finite radix without changing the manuscript schedule."""
    groups = layout.source["r"]
    natural(groups, 64, 1024, "finite group count")
    if groups != 64 and (
        parent.semantics is not Semantics.FINITE_SCALED_EXPERIMENT
        or layout.strategy != "balanced_vertices"
    ):
        raise ValueError("non-64 groups require finite balanced-vertex semantics")
    return groups


def schedule_group_count(record):
    """Read the group range from immutable child metadata, not a global cap."""
    if type(record) is not dict or type(record.get("used")) is not dict:
        raise ValueError("child group schedule required")
    groups = record["used"].get("r")
    natural(groups, 64, 1024, "child schedule group count")
    semantics = record.get("semantics")
    if semantics not in (
        Semantics.FINITE_SCALED_EXPERIMENT.value, Semantics.SOURCE_QUALIFIED.value
    ):
        raise ValueError("child schedule semantics required")
    if semantics == Semantics.SOURCE_QUALIFIED.value and groups != 64:
        raise ValueError("source schedule requires exactly 64 groups")
    if type(record.get("source")) is not dict or record["source"].get("r") != 64:
        raise ValueError("pinned source group count must remain 64")
    return groups


@dataclass(frozen=True)
class Policy:
    max_edges: int = 8
    max_tuples: int = 4096
    max_calls: int = 300_000
    max_work: int = 100_000_000
    max_depth: int = 4
    max_precision: int = 1024
    max_factor_bits: int = 16
    max_seconds: int = 300
    max_certificate_bytes: int = 20_000_000

    def __post_init__(self):
        for name, hi in zip(
            self.__dataclass_fields__,
            (1024, 100_000, 2_000_000, 2_000_000_000, 16, 65536, 20, 3600, 1_000_000_000),
        ):
            natural(getattr(self, name), 1, hi, name)


DEFAULT_POLICY = Policy()


class Budget:
    def __init__(self, policy=DEFAULT_POLICY):
        if type(policy) is not Policy:
            raise TypeError("Policy required")
        self.policy = policy
        self.started = monotonic()
        self.work = self.calls = self.depth = self.points = self.tuples = 0
        self.transitions = self.nonshrinking = 0

    def tick(self, n=1):
        self.work += n
        if (
            self.work > self.policy.max_work
            or monotonic() - self.started > self.policy.max_seconds
        ):
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "R9.8 work/time budget")

    def call(self, depth):
        self.tick()
        self.calls += 1
        self.depth = max(self.depth, depth)
        if self.calls > self.policy.max_calls or depth > self.policy.max_depth:
            raise Refusal("INCONCLUSIVE_RESOURCE_LIMIT", "R9.8 call/depth budget")

    def report(self):
        return {
            "actual_calls": self.calls,
            "maximum_depth": self.depth,
            "point_evaluations": self.points,
            "tuples": self.tuples,
            "transitions": self.transitions,
            "nonshrinking_children": self.nonshrinking,
            "work_units": self.work,
            "elapsed_seconds": monotonic() - self.started,
            "hard_memory_limit_enforced": False,
            "bit_time_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
            "peak_space_bound_status": "COMPLEXITY_NOT_ESTABLISHED",
        }


def reference_record(ref):
    return {
        "arity": ref.arity,
        "creation_precision": ref.creation_precision,
        "defining_polynomial": ref.defining_polynomial,
        "jet_length": ref.jet_length,
        "recipe_kind": ref.recipe_kind,
        "description": ref.description.decode("ascii"),
    }


def vertex_record(v):
    return {
        "side": v.side,
        "vertex_id": v.vertex_id,
        "ports": list(v.ports),
        "tensor": reference_record(v.tensor),
    }


def read_vertex(v):
    if type(v) is not dict or set(v) != {"side", "vertex_id", "ports", "tensor"}:
        raise ValueError("vertex fields")
    ref = dict(v["tensor"])
    ref["description"] = ref["description"].encode("ascii")
    return SourceVertex(
        v["side"], v["vertex_id"], tuple(v["ports"]), SourceTensorReference(**ref)
    )


def validate_graph(M, vertices, p, f, jet_length=1):
    natural(jet_length, 1, 64, "jet length")
    natural(M, 0, 1024, "edge count")
    natural(p, 1, 65536, "precision")
    if type(vertices) is not tuple or len(vertices) > 4096:
        raise ValueError("immutable bounded vertices required")
    expected_ids = {"row": 0, "column": 0}
    keys, owners = [], set()
    budget = EntryBudget(
        EntryLimits(
            max_work=30_000_000, max_seconds=60, max_precision_bits=max(1024, p)
        )
    )
    for v in vertices:
        if type(v) is not SourceVertex or v.vertex_id != expected_ids[v.side]:
            raise ValueError("noncanonical vertex identity/order")
        expected_ids[v.side] += 1
        keys.append((0 if v.side == "row" else 1, v.vertex_id))
        if (
            len(v.ports) != v.tensor.arity
            or v.tensor.defining_polynomial != f
            or v.tensor.jet_length != jet_length
            or v.tensor.creation_precision > p
        ):
            raise ValueError("arity or creation ring mismatch")
        compile_entry(v.tensor, budget)
        for edge in v.ports:
            natural(edge, 0, M - 1, "port")
            if (v.side, edge) in owners:
                raise ValueError("duplicate port owner")
            owners.add((v.side, edge))
    if keys != sorted(keys) or len(owners) != 2 * M:
        raise ValueError("noncanonical order or missing endpoint")


@dataclass(frozen=True)
class ParentCall:
    root_s: int
    depth: int
    precision: int
    defining_polynomial: int
    edge_count: int
    vertices: tuple[SourceVertex, ...]
    semantics: Semantics = Semantics.FINITE_SCALED_EXPERIMENT
    ancestry_digest: str | None = None
    source_context: SourceContext | None = None
    jet_length: int = 1

    def __post_init__(self):
        natural(self.root_s, 2, 2**4096 - 1, "root s")
        natural(self.depth, 0, 16, "depth")
        if type(self.semantics) is not Semantics:
            raise TypeError("explicit Semantics required")
        if self.ancestry_digest is not None:
            hash_string(self.ancestry_digest)
        if self.source_context is not None:
            c = self.source_context
            if (
                type(c) is not SourceContext
                or c.size_parameter != self.root_s
                or c.defining_polynomial != self.defining_polynomial
                or c.jet_length != self.jet_length
            ):
                raise ValueError("source context mismatch")
            SourceNode(c, self.edge_count, self.vertices, self.depth, self.precision)
        if self.semantics is Semantics.SOURCE_QUALIFIED and self.source_context is None:
            raise ValueError("source calls require a SourceContext")
        validate_graph(
            self.edge_count, self.vertices, self.precision, self.defining_polynomial, self.jet_length
        )

    @property
    def maximum_degree(self):
        return max((len(v.ports) for v in self.vertices), default=0)

    def bipartite_edges(self):
        owners = [{}, {}]
        for v in self.vertices:
            for e in v.ports:
                owners[int(v.side == "column")][e] = v.vertex_id
        return tuple((owners[0][e], owners[1][e]) for e in range(self.edge_count))

    def record(self):
        return {
            **({"jet_length": self.jet_length} if self.jet_length != 1 else {}),
            "root_s": self.root_s,
            "depth": self.depth,
            "precision": self.precision,
            "defining_polynomial": self.defining_polynomial,
            "edge_count": self.edge_count,
            "vertices": [vertex_record(v) for v in self.vertices],
            "semantics": self.semantics.value,
            "ancestry_digest": self.ancestry_digest,
            "source_context": None
            if self.source_context is None
            else asdict(self.source_context),
        }

    @cached_property
    def content_digest(self):
        return digest(self.record())


def from_described(network, *, root_s, depth=0, precision):
    from veritas.research.eth_recursive_contraction_v39.described_network import (
        DescribedNetwork,
    )
    from veritas.research.tapered_v4.source_recipe_bridge import (
        source_reference_from_created,
    )

    if type(network) is not DescribedNetwork or not network.vertices:
        raise TypeError("nonempty finite DescribedNetwork required")
    vertices = []
    for side in ("row", "column"):
        for i, v in enumerate(v for v in network.vertices if v.side == side):
            vertices.append(
                SourceVertex(side, i, v.ports, source_reference_from_created(v.tensor))
            )
    return ParentCall(
        root_s,
        depth,
        precision,
        vertices[0].tensor.defining_polynomial,
        network.edges,
        tuple(vertices),
        jet_length=vertices[0].tensor.jet_length,
    )


def from_source(node):
    if type(node) is not SourceNode:
        raise TypeError("SourceNode required")
    # Canonical renumbering is explicit; original port order and recipes survive.
    vertices = tuple(
        SourceVertex(side, i, v.ports, v.tensor)
        for side in ("row", "column")
        for i, v in enumerate(v for v in node.vertices if v.side == side)
    )
    return ParentCall(
        node.context.size_parameter,
        node.depth,
        node.precision,
        node.context.defining_polynomial,
        node.edge_count,
        vertices,
        Semantics.SOURCE_QUALIFIED,
        source_context=node.context,
        jet_length=node.context.jet_length,
    )


@dataclass(frozen=True)
class PacketLayout:
    parent_digest: str
    a: int
    u: int
    source_bytes: bytes
    strategy: str = "canonical"

    def __post_init__(self):
        hash_string(self.parent_digest)
        natural(self.a, 1, 3, "a")
        natural(self.u, 1, self.a, "u")
        if self.strategy not in (
            "canonical",
            "scaled_singletons",
            "balanced_components",
            "balanced_vertices",
        ):
            raise ValueError("unsupported packet strategy")
        decode(self.source_bytes)

    @cached_property
    def _decoded_source(self):
        return decode(self.source_bytes)

    @property
    def source(self):
        return deepcopy(self._decoded_source)

    @cached_property
    def content_digest(self):
        return digest([self.parent_digest, self.a, self.u, self.strategy, self.source])


@dataclass(frozen=True)
class ModeSet:
    layout_digest: str
    certificate_bytes: bytes

    def __post_init__(self):
        hash_string(self.layout_digest)
        decode(self.certificate_bytes)

    @cached_property
    def _decoded_certificate(self):
        return decode(self.certificate_bytes)

    @property
    def certificate(self):
        return deepcopy(self._decoded_certificate)

    @cached_property
    def content_digest(self):
        return digest([self.layout_digest, self.certificate])


@dataclass(frozen=True)
class ExponentTuple:
    modes_digest: str
    values: tuple[int, ...]

    def __post_init__(self):
        hash_string(self.modes_digest)
        if type(self.values) is not tuple or any(
            type(v) is not int or v < 0 for v in self.values
        ):
            raise ValueError("immutable natural exponent tuple required")


@dataclass(frozen=True)
class ChildGraph:
    parent_digest: str
    layout_digest: str
    modes_digest: str
    schedule_bytes: bytes
    depth: int
    node: int
    zeta: tuple[int, ...]
    beta: ExponentTuple
    group: int
    # (Y/X, parent edge, packet id, slot, inherited vertex, original port position).
    edge_map: tuple[tuple, ...]
    # Parent (side,id) for each ordered inherited row vertex; packet id for each column.
    inherited: tuple[tuple[str, int], ...]
    packet_ids: tuple[int, ...]
    vertices: tuple[SourceVertex, ...]
    precision: int
    defining_polynomial: int
    jet_length: int = 1

    def __post_init__(self):
        for h in (self.parent_digest, self.layout_digest, self.modes_digest):
            hash_string(h)
        if (
            type(self.beta) is not ExponentTuple
            or self.beta.modes_digest != self.modes_digest
        ):
            raise ValueError("beta binding mismatch")
        natural(self.group, 0, self.group_count - 1, "group")
        natural(self.depth, 1, 16, "child depth")
        if type(self.node) is not int or not self.node:
            raise ValueError("nonzero interpolation node required")
        for value in (self.edge_map, self.inherited, self.packet_ids, self.zeta):
            if type(value) is not tuple:
                raise ValueError("deeply immutable child metadata required")
        if any(type(x) is not tuple for x in self.edge_map + self.inherited):
            raise ValueError("immutable map records required")
        if any(
            len(row) != 6
            or type(row[0]) is not str
            or row[0] not in ("Y", "X")
            or any(type(n) is not int or n < 0 for n in row[1:])
            for row in self.edge_map
        ):
            raise ValueError("half-edge metadata requires typed natural indices")
        keys = tuple((row[0], row[1]) for row in self.edge_map)
        if len(set(keys)) != len(keys) or keys != tuple(
            sorted(keys, key=lambda key: (key[0] != "Y", key[1]))
        ):
            raise ValueError("duplicate or noncanonical half-edge metadata")
        if any(
            len(origin) != 2
            or type(origin[0]) is not str
            or origin[0] not in ("row", "column")
            or type(origin[1]) is not int
            or origin[1] < 0
            for origin in self.inherited
        ):
            raise ValueError("inherited metadata requires typed vertex identities")
        if len(set(self.inherited)) != len(self.inherited) or self.inherited != tuple(
            sorted(self.inherited, key=lambda origin: (origin[0] != "row", origin[1]))
        ):
            raise ValueError("duplicate or noncanonical inherited metadata")
        if (
            any(type(n) is not int or n < 0 for n in self.packet_ids)
            or tuple(sorted(set(self.packet_ids))) != self.packet_ids
        ):
            raise ValueError(
                "packet identities must be ordered distinct natural indices"
            )
        decode(self.schedule_bytes)
        if len(self.zeta) != self.defining_polynomial.bit_length() - 1:
            raise ValueError("zeta width")
        for z in self.zeta:
            natural(z, 0, (1 << self.precision) - 1, "zeta")
        validate_graph(
            len(self.edge_map), self.vertices, self.precision, self.defining_polynomial, self.jet_length
        )
        if len(self.inherited) != sum(v.side == "row" for v in self.vertices) or len(
            self.packet_ids
        ) != sum(v.side == "column" for v in self.vertices):
            raise ValueError("child origin inventory mismatch")

    @property
    def edge_count(self):
        return len(self.edge_map)

    @property
    def group_count(self):
        return schedule_group_count(decode(self.schedule_bytes))

    def record(self):
        result = {
            k: getattr(self, k)
            for k in self.__dataclass_fields__
            if k not in ("vertices", "schedule_bytes", "beta")
        }
        if self.jet_length == 1:
            result.pop("jet_length")
        result.update(
            vertices=[vertex_record(v) for v in self.vertices],
            schedule=decode(self.schedule_bytes),
            beta=asdict(self.beta),
        )
        return result

    @cached_property
    def content_digest(self):
        return digest(self.record())

    def serialize(self):
        return canonical(
            {
                "schema": "VERITAS_R98_CHILD_V1",
                "sha256": self.content_digest,
                "child": self.record(),
            }
        )

    @classmethod
    def deserialize(cls, raw):
        obj = decode(raw)
        if (
            set(obj) != {"schema", "sha256", "child"}
            or obj["schema"] != "VERITAS_R98_CHILD_V1"
        ):
            raise ValueError("child envelope")
        if digest(obj["child"]) != obj["sha256"]:
            raise ValueError("child content digest mismatch")
        d = dict(obj["child"])
        d["schedule_bytes"] = canonical(d.pop("schedule"))
        d["vertices"] = tuple(read_vertex(v) for v in d["vertices"])
        d["beta"] = ExponentTuple(d["beta"]["modes_digest"], tuple(d["beta"]["values"]))
        for k in ("edge_map", "inherited"):
            d[k] = tuple(tuple(row) for row in d[k])
        for k in ("zeta", "packet_ids"):
            d[k] = tuple(d[k])
        child = cls(**d)
        if child.serialize() != raw:
            raise ValueError("child noncanonical round trip")
        return child

    def as_parent(self, parent):
        if (
            type(parent) is not ParentCall
            or self.parent_digest != parent.content_digest
        ):
            raise ValueError("child belongs to another parent")
        if (
            self.depth != parent.depth + 1
            or self.defining_polynomial != parent.defining_polynomial
            or self.jet_length != parent.jet_length
            or self.precision <= parent.precision
            or decode(self.schedule_bytes)["semantics"] != parent.semantics.value
        ):
            raise ValueError(
                "child depth, ring or precision does not extend its parent"
            )
        return ParentCall(
            parent.root_s,
            self.depth,
            self.precision,
            self.defining_polynomial,
            self.edge_count,
            self.vertices,
            parent.semantics,
            self.content_digest,
            parent.source_context,
            self.jet_length,
        )


@dataclass(frozen=True)
class ChildReductionTerm:
    beta: ExponentTuple
    children: tuple[ChildGraph, ...]
    values: tuple
    product: tuple

    def __post_init__(self):
        if (
            type(self.children) is not tuple or not self.children
            or any(type(c) is not ChildGraph for c in self.children)
        ):
            raise ValueError("immutable complete group term required")
        first = self.children[0]
        groups = first.group_count
        context = lambda c: (
            c.parent_digest, c.layout_digest, c.modes_digest, c.schedule_bytes,
            c.depth, c.node, c.zeta, c.precision, c.defining_polynomial, c.jet_length,
        )
        if (
            type(self.beta) is not ExponentTuple
            or len(self.children) != groups
            or type(self.values) is not tuple
            or len(self.values) != groups
            or type(self.product) is not tuple
            or any(
                c.beta != self.beta or c.group != g or context(c) != context(first)
                for g, c in enumerate(self.children)
            )
        ):
            raise ValueError(f"immutable complete {groups}-group term required")


@dataclass(frozen=True)
class PointEvaluationCertificate:
    payload: bytes

    def __post_init__(self):
        decode(self.payload)

    @cached_property
    def content_digest(self):
        return digest(self.payload)


@dataclass(frozen=True)
class HermiteRecoveryCertificate(PointEvaluationCertificate):
    pass


def schedule_record(parent, layout):
    from veritas.research.paper_verification.exact_parameters import source_schedule

    return {
        "paper_commit": PIN,
        "statement_hashes": source_registry()["labels"],
        "root_s": parent.root_s,
        "source": source_schedule(parent.root_s, parent.depth),
        "used": {"r": layout_group_count(parent, layout), "a": layout.a,
                 "u": layout.u, "L": 1 << layout.a},
        "semantics": parent.semantics.value,
    }
