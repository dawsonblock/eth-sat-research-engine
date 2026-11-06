"""Immutable inputs and explicit finite-resource policy for v4 experiments."""
from __future__ import annotations

from dataclasses import dataclass
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursive_contraction_v39.described_network import DescribedNetwork


@dataclass(frozen=True)
class TaperedState:
    network: DescribedNetwork
    depth: int
    target_precision: int
    extension_polynomial: int
    jet_length: int
    root_size: int
    schedule_id: str = 'FINITE_SCALED_V1'
    parent_certificate_hash: str | None = None

    def __post_init__(self):
        if not isinstance(self.network, DescribedNetwork):
            raise TypeError('immutable described network required')
        if (type(self.depth) is not int or self.depth < 0 or
                type(self.root_size) is not int or self.root_size < 0 or
                type(self.target_precision) is not int or self.target_precision < 1 or
                type(self.schedule_id) is not str or not self.schedule_id):
            raise ValueError('invalid recursion state')
        # Every current execution policy caps extension degree at eight. Check
        # that bound before the irreducibility test, which otherwise runs before
        # a policy or cooperative deadline exists.
        if (type(self.extension_polynomial) is not int or
                self.extension_polynomial < 2 or
                self.extension_polynomial.bit_length() > 9):
            raise ValueError('finite state extension degree must be in 1..8')
        # The execution policy separately rejects excess target precision.
        JetRing(ExtensionRing(1, self.extension_polynomial), self.jet_length)
        h = self.parent_certificate_hash
        if h is not None and (type(h) is not str or len(h) != 64 or
                              any(c not in '0123456789abcdef' for c in h)):
            raise ValueError('parent state hash must be a SHA-256 hex digest')


@dataclass(frozen=True)
class RecursionPolicy:
    """Caps for observed work, not a certified total-bit or hard-memory limit."""
    mode: str = 'finite'
    leaf_edge_limit: int = 0
    max_depth: int = 8
    max_work: int = 2_000_000
    max_seconds: float = 30.0
    max_precision_bits: int = 1024
    max_extension_degree: int = 8
    max_jet_length: int = 64
    max_active_wires: int = 6
    max_vertex_degree: int = 16
    max_points: int = 32
    max_tuples: int = 3000
    max_certificate_bytes: int = 4_000_000
    max_description_bytes: int = 20_000_000
    max_memory_bytes: int | None = None
    verify_small_nodes: bool = False
    oracle_edge_limit: int = 4
    allow_nonshrinking_leaf: bool = False
    nonshrinking_leaf_limit: int = 6
    require_one_eighth_shrink: bool = False
    enable_hall_pruning: bool = False
    finite_parameters: tuple[int, int, int] = (1, 1, 2)
    require_complete_accounting: bool = False
    verify_point_identities: bool = False
    point_oracle_edge_limit: int = 3
    verify_tuple_identities: bool = False
    tuple_oracle_edge_limit: int = 3
    auto_point_oracle_edges: int = 2

    def __post_init__(self):
        if self.mode not in ('finite', 'theorem'):
            raise ValueError('mode must be finite or theorem')
        integer_limits = (self.leaf_edge_limit, self.max_depth, self.max_work,
                          self.max_precision_bits, self.max_points, self.max_tuples,
                          self.max_active_wires, self.max_extension_degree, self.max_jet_length,
                          self.max_vertex_degree,
                          self.max_certificate_bytes, self.max_description_bytes,
                          self.oracle_edge_limit, self.nonshrinking_leaf_limit,
                          self.point_oracle_edge_limit, self.tuple_oracle_edge_limit,
                          self.auto_point_oracle_edges)
        if any(type(value) is not int for value in integer_limits):
            raise ValueError('integer resource limits required')
        if (not 0 <= self.leaf_edge_limit <= 16 or not 0 <= self.max_depth <= 64 or
                not 1 <= self.max_work <= 10_000_000 or
                not 1 <= self.max_precision_bits <= 1024 or
                not 1 <= self.max_extension_degree <= 8 or not 1 <= self.max_jet_length <= 64 or
                not 1 <= self.max_active_wires <= 8 or
                not 0 <= self.max_vertex_degree <= 64 or
                not 1 <= self.max_points <= 32 or not 1 <= self.max_tuples <= 100_000 or
                not 1 <= self.max_certificate_bytes <= 50_000_000 or
                not 1 <= self.max_description_bytes <= 50_000_000 or
                not 0 <= self.oracle_edge_limit <= 16 or
                not 0 <= self.nonshrinking_leaf_limit <= 16 or
                not 1 <= self.point_oracle_edge_limit <= 4 or
                not 1 <= self.tuple_oracle_edge_limit <= 3 or
                not 2 <= self.auto_point_oracle_edges <= 4):
            raise ValueError('resource limit outside finite reference bounds')
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError('max_seconds must be in (0,120]')
        if self.max_memory_bytes is not None and (type(self.max_memory_bytes) is not int or
                                                   self.max_memory_bytes < 1):
            raise ValueError('hard memory limit must be a positive integer or None')
        for flag in (self.verify_small_nodes, self.allow_nonshrinking_leaf,
                     self.require_one_eighth_shrink, self.enable_hall_pruning,
                     self.require_complete_accounting, self.verify_point_identities,
                     self.verify_tuple_identities):
            if type(flag) is not bool:
                raise ValueError('policy flags must be Boolean')
        if (type(self.finite_parameters) is not tuple or len(self.finite_parameters) != 3 or
                any(type(value) is not int for value in self.finite_parameters)):
            raise ValueError('finite_parameters must be an immutable (a,u,r) tuple')
        a, u, r = self.finite_parameters
        if a not in (1, 2, 3) or not 1 <= u <= a or not 2 <= r <= 64:
            raise ValueError('scaled parameters require a in {1,2,3}, 1<=u<=a, 2<=r<=64')
