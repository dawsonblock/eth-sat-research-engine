"""Source-sized immutable state and bounded structural admission.

This is not an executor. Tensor descriptions are content-bound references;
their denotations and uniform entry-cost contracts still require proofs.
The finite TaperedState and its caps are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isqrt
from pathlib import Path

from veritas.research.appendix_d_schedule import schedule_preflight
from veritas.research.eth_arithmetic.gf2 import is_irreducible

MANUSCRIPT_SHA256 = "671642d7b53154d92344e8c4be0240f18929632ebcfdf73b07c3e9939b873860"


class SourceAdmissionError(ValueError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def _natural(value, name, *, positive=False):
    if type(value) is not int or value < int(positive):
        raise ValueError(f"{name} must be an {'positive' if positive else 'nonnegative'} integer")


@dataclass(frozen=True)
class SourceLimits:
    max_size_bits: int = 4096
    max_extension_degree: int = 64
    max_precision_bits: int = 4096
    max_jet_length: int = 1024
    max_edges: int = 100_000
    max_vertices: int = 100_000
    max_description_bytes: int = 16_000_000
    max_check_work: int = 5_000_000
    max_depth: int = 64

    def __post_init__(self):
        ceilings = (65536, 4096, 1_000_000, 1_000_000, 1_000_000,
                    1_000_000, 100_000_000, 100_000_000, 4096)
        for name, ceiling in zip(self.__dataclass_fields__, ceilings):
            value = getattr(self, name)
            _natural(value, name, positive=True)
            if value > ceiling:
                raise ValueError(f"{name} exceeds the supported admission cap")


@dataclass(frozen=True)
class SourceContext:
    """Fixed root parameters, distinct from a node's current edge count.

    C,A,b are integer upper bounds for the theorem's fixed positive constants.
    Recording them does not certify an arbitrary description's entry routine.
    The polynomial is supplied explicitly, never chosen anew at child calls.
    """
    size_parameter: int
    size_constant: int
    entry_time_constant: int
    entry_polynomial_exponent: int
    initial_precision: int
    jet_length: int
    defining_polynomial: int
    limits: SourceLimits = SourceLimits()
    manuscript_sha256: str = MANUSCRIPT_SHA256

    def __post_init__(self):
        if type(self.limits) is not SourceLimits:
            raise TypeError("SourceLimits required")
        for name in ("size_parameter", "size_constant", "entry_time_constant",
                     "entry_polynomial_exponent", "initial_precision", "jet_length"):
            value = getattr(self, name)
            _natural(value, name, positive=True)
            if value.bit_length() > self.limits.max_size_bits:
                raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT", f"{name} bit cap exceeded")
        if self.size_parameter < 2 or self.manuscript_sha256 != MANUSCRIPT_SHA256:
            raise ValueError("invalid source size or manuscript identity")
        if (self.initial_precision > self.size_constant * self.size_parameter or
                self.jet_length > self.size_constant * self.size_parameter):
            raise ValueError("root precision and jet length must be at most C*s")
        if (self.initial_precision > self.limits.max_precision_bits or
                self.jet_length > self.limits.max_jet_length or
                self.extension_degree > self.limits.max_extension_degree):
            raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT", "source ring exceeds admission limits")
        _natural(self.defining_polynomial, "defining_polynomial", positive=True)
        if self.defining_polynomial.bit_length() != self.extension_degree + 1:
            raise ValueError("extension polynomial degree must be exactly 4*ceil(log2(s))")
        # Polynomial bit-length/degree is capped BEFORE the algebraic test.
        if self.extension_degree ** 3 > self.limits.max_check_work:
            raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT", "irreducibility admission work exceeded")
        if not is_irreducible(self.defining_polynomial):
            raise ValueError("extension polynomial is reducible modulo two")

    @property
    def lambda_value(self):
        return (self.size_parameter - 1).bit_length()

    @property
    def extension_degree(self):
        return 4 * self.lambda_value

    @property
    def leaf_threshold(self):
        divisor = isqrt(self.lambda_value)
        return (self.size_parameter + divisor - 1) // divisor


@dataclass(frozen=True)
class SourceTensorReference:
    """Immutable recipe bytes and creation-ring metadata, not a cost proof."""
    arity: int
    creation_precision: int
    defining_polynomial: int
    jet_length: int
    recipe_kind: str
    description: bytes

    def __post_init__(self):
        _natural(self.arity, "arity")
        for name in ("creation_precision", "defining_polynomial", "jet_length"):
            _natural(getattr(self, name), name, positive=True)
        if type(self.recipe_kind) is not str or not 1 <= len(self.recipe_kind) <= 128:
            raise ValueError("recipe kind must be a bounded nonempty name")
        if type(self.description) is not bytes:
            raise TypeError("immutable recipe bytes required")

    @property
    def description_sha256(self):
        return sha256(self.description).hexdigest()


@dataclass(frozen=True)
class SourceVertex:
    side: str
    vertex_id: int
    ports: tuple[int, ...]
    tensor: SourceTensorReference

    def __post_init__(self):
        if type(self.side) is not str or self.side not in ("row", "column"):
            raise ValueError("tagged row/column side required")
        _natural(self.vertex_id, "vertex_id")
        if type(self.ports) is not tuple or type(self.tensor) is not SourceTensorReference:
            raise TypeError("immutable ports and source tensor reference required")


@dataclass(frozen=True)
class SourceNode:
    context: SourceContext
    edge_count: int
    vertices: tuple[SourceVertex, ...]
    depth: int
    precision: int

    def __post_init__(self):
        if type(self.context) is not SourceContext or type(self.vertices) is not tuple:
            raise TypeError("immutable source context and vertices required")
        for name in ("edge_count", "depth", "precision"):
            _natural(getattr(self, name), name, positive=name == "precision")
        limits = self.context.limits
        if (self.edge_count > limits.max_edges or len(self.vertices) > limits.max_vertices or
                self.depth > limits.max_depth or self.precision > limits.max_precision_bits):
            raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT", "source node exceeds admission limits")
        if self.precision < self.context.initial_precision:
            raise ValueError("node precision is below the root precision")
        if self.depth == 0 and self.precision != self.context.initial_precision:
            raise ValueError("root node precision must equal P0")
        if self.edge_count * 8 ** self.depth > self.context.size_constant * self.context.size_parameter:
            raise ValueError("node violates M <= C*s/8^depth")
        # Bound scanning and retained port maps before allocating them.
        port_count = description_bytes = 0
        for vertex in self.vertices:
            if type(vertex) is not SourceVertex:
                raise TypeError("SourceVertex required")
            port_count += len(vertex.ports)
            description_bytes += len(vertex.tensor.description)
            if (port_count > 2 * self.edge_count or
                    port_count + len(self.vertices) > limits.max_check_work or
                    description_bytes > limits.max_description_bytes):
                raise SourceAdmissionError("INCONCLUSIVE_RESOURCE_LIMIT", "source description or incidence cap exceeded")
        owners, identities = set(), set()
        for vertex in self.vertices:
            key = (vertex.side, vertex.vertex_id)
            if vertex.vertex_id.bit_length() > limits.max_size_bits or key in identities:
                raise ValueError("duplicate or oversized tagged vertex identity")
            identities.add(key)
            tensor = vertex.tensor
            if (len(vertex.ports) != tensor.arity or
                    tensor.defining_polynomial != self.context.defining_polynomial or
                    tensor.jet_length != self.context.jet_length or
                    not self.context.initial_precision <= tensor.creation_precision <= self.precision):
                raise ValueError("tensor arity or creation ring differs from source context")
            for edge in vertex.ports:
                if type(edge) is not int or not 0 <= edge < self.edge_count or (vertex.side, edge) in owners:
                    raise ValueError("invalid or multiply owned edge occurrence")
                owners.add((vertex.side, edge))
        if len(owners) != 2 * self.edge_count:
            raise ValueError("every edge must have one endpoint on each side")
        if self.maximum_degree > self.edge_count:
            raise ValueError("degree exceeds edge count")
        # The degree and schedule use s, never edge_count as a substitute.
        check = schedule_preflight(self.context.size_parameter, self.edge_count,
                                   self.maximum_degree, self.depth,
                                   size_constant=self.context.size_constant,
                                   max_size_bits=limits.max_size_bits)
        if check["status"].startswith("INVALID"):
            raise ValueError(check["status"])
        if check["status"] == "INCONCLUSIVE_RESOURCE_LIMIT":
            raise SourceAdmissionError(check["status"], "source schedule admission cap exceeded")

    @property
    def maximum_degree(self):
        return max((len(v.ports) for v in self.vertices), default=0)


def inspect_source_node(node: SourceNode):
    if type(node) is not SourceNode:
        raise TypeError("SourceNode required")
    source = Path(__file__).resolve().parents[4] / "paper/quantitative-contraction.tex"
    if not source.is_file() or sha256(source.read_bytes()).hexdigest() != node.context.manuscript_sha256:
        raise SourceAdmissionError("INCONCLUSIVE_SOURCE_MISMATCH", "pinned manuscript is absent or changed")
    context = node.context
    numeric = schedule_preflight(context.size_parameter, node.edge_count, node.maximum_degree,
                                 node.depth, size_constant=context.size_constant,
                                 max_size_bits=context.limits.max_size_bits)
    return {"status": "SOURCE_STATE_STRUCTURALLY_ADMITTED", "s": context.size_parameter,
            "M": node.edge_count, "depth": node.depth, "precision": node.precision,
            "extension_degree": context.extension_degree, "schedule": numeric,
            "entry_semantics_verified": False, "entry_cost_contract_proven": False,
            "ancestry_verified": False, "source_schedule_theorem_proven": False,
            "executable_refinement_proven": False, "theorem_mode_enabled": False,
            "count_available": False}


def check_source_transition(parent: SourceNode, child: SourceNode):
    """Check necessary numeric transition conditions, not child identity."""
    if type(parent) is not SourceNode or type(child) is not SourceNode:
        raise TypeError("SourceNode parent and child required")
    if parent.context != child.context or child.depth != parent.depth + 1:
        raise ValueError("root context or depth changed")
    if child.precision <= parent.precision or 32 * child.edge_count > 3 * parent.edge_count:
        raise ValueError("source precision increase or child shrinking failed")
    if parent.edge_count <= parent.context.leaf_threshold:
        raise ValueError("a source leaf must not generate children")
    admission = inspect_source_node(parent)
    inspect_source_node(child)
    if admission["schedule"]["status"] != "ACTIVE_NUMERIC_PRECONDITIONS_MET":
        raise SourceAdmissionError(admission["schedule"]["status"],
                                   "parent does not satisfy the active numeric preflight")
    return {"status": "NECESSARY_TRANSITION_CONDITIONS_CHECKED",
            "child_identity_proven": False, "theorem_mode_enabled": False}
