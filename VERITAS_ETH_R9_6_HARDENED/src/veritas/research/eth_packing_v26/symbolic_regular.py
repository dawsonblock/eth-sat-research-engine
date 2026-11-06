"""Closed-form D.3 packing witness for a regular, disconnected family.

Each directed label class contains disjoint copies of K_(degree,degree).
The object computes one edge/slot correspondence at a time; it does not run
the conditional-expectation constructor, construct a tensor network, or
prove the universal contraction theorem.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegularPackingWitness:
    """Explicit balanced a=1 packet family; storage is independent of M.

    An edge is (row_label, column_label, copy, row_in_copy, col_in_copy).
    A slot address is (low_label, high_label, packet_index, slot_bit).
    """

    radix: int
    degree: int
    copies: int

    def __post_init__(self):
        if type(self.radix) is not int or not 2 <= self.radix <= 64:
            raise ValueError('radix must be an integer in 2..64')
        if type(self.degree) is not int or not 4 <= self.degree <= 64 or self.degree % 2:
            raise ValueError('degree must be an even integer in 4..64')
        if type(self.copies) is not int or not 1 <= self.copies <= 1 << 24:
            raise ValueError('copies must be an integer in 1..2^24')

    @property
    def class_edges(self):
        return self.copies * self.degree ** 2

    @property
    def edge_count(self):
        return self.radix ** 2 * self.class_edges

    @property
    def vertex_count(self):
        return 2 * self.radix ** 2 * self.copies * self.degree

    @property
    def packet_count(self):
        return self.edge_count // 2

    def edge_to_slot(self, edge):
        if (type(edge) is not tuple or len(edge) != 5 or
                any(type(x) is not int for x in edge)):
            raise ValueError('edge address must be a five-integer tuple')
        row, col, copy, i, j = edge
        if (not 0 <= row < self.radix or not 0 <= col < self.radix or
                not 0 <= copy < self.copies or not 0 <= i < self.degree or
                not 0 <= j < self.degree):
            raise ValueError('edge address outside family')
        offset = copy * self.degree ** 2 + i * self.degree + j
        if row == col:
            return row, col, offset // 2, offset % 2
        return min(row, col), max(row, col), offset, int(row > col)

    def slot_to_edge(self, slot):
        if (type(slot) is not tuple or len(slot) != 4 or
                any(type(x) is not int for x in slot)):
            raise ValueError('slot address must be a four-integer tuple')
        low, high, index, bit = slot
        if (not 0 <= low <= high < self.radix or bit not in (0, 1) or
                not 0 <= index < (self.class_edges // 2 if low == high else self.class_edges)):
            raise ValueError('packet slot outside family')
        if low == high:
            row = col = low
            offset = 2 * index + bit
        else:
            row, col = (low, high) if bit == 0 else (high, low)
            offset = index
        copy, within = divmod(offset, self.degree ** 2)
        i, j = divmod(within, self.degree)
        return row, col, copy, i, j

    def audit(self):
        """Compute exact sufficient-condition and per-group size quantities.

        The balanced loads and complete slot correspondence follow from the
        explicit family and bijections in the accompanying derivation. This
        calculation is not a replay of the general packing algorithm.
        """
        r, delta, h = self.radix, self.degree, self.class_edges
        M, D, L = self.edge_count, r ** 2, 2
        side_load = r * h
        child_edges = 2 * side_load
        numeric = M >= 2 * D ** 2 * delta and M >= L * D and 2 * L <= delta
        return {
            'status': 'EXPLICIT_STRUCTURED_PACKING_WITNESS',
            'radix': r, 'a': 1, 'L': L, 'directed_classes': D,
            'degree_bound': delta, 'class_edges': h, 'padded_class_size': h,
            'parent_edges': M, 'vertices': self.vertex_count,
            'packets': self.packet_count, 'row_load_each_group': side_load,
            'column_load_each_group': side_load, 'child_edges_each_group': child_edges,
            'packing_numeric_conditions': numeric,
            'packing_count_bound': D * h <= 3 * M,
            'side_load_bound': r * side_load <= 3 * M,
            'child_six_M_over_r_bound': r * child_edges <= 6 * M,
            'strict_one_eighth_shrink': 8 * child_edges < M,
            'three_M_over_32_bound': 32 * child_edges <= 3 * M,
            # The active manuscript schedule uses a=2*sum(u_j), hence an
            # even positive a. This a=1 witness exercises only the packing lemma.
            'manuscript_active_schedule_compatible': False,
            'full_contraction_executed': False,
            'deterministic_constructor_replayed': False,
            'uniform_complexity_proven': False,
        }


@dataclass(frozen=True)
class MultiCoordinateRegularPackingWitness:
    """Balanced a-coordinate family with an implicit, exact slot bijection.

    Each directed label pair has ``copies`` disjoint ``K_degree,degree``
    components. Edges are addressed by ``(row_word, column_word, copy,
    row_in_copy, column_in_copy)`` and slots by ``(unordered_pairs, index,
    slot_bits)``. Neither the graph nor its packets are materialized.
    """

    radix: int
    a: int
    degree: int
    copies: int

    def __post_init__(self):
        if type(self.radix) is not int or not 2 <= self.radix <= 64:
            raise ValueError('radix must be an integer in 2..64')
        if type(self.a) is not int or not 1 <= self.a <= 8:
            raise ValueError('a must be an integer in 1..8')
        L = 1 << self.a
        if (type(self.degree) is not int or not 2 * L <= self.degree <= 1024 or
                self.degree % L):
            raise ValueError('degree must be a multiple of L in 2L..1024')
        if type(self.copies) is not int or self.copies < 1 or self.copies.bit_length() > 262144:
            raise ValueError('copies must be a positive integer of at most 262144 bits')

    @property
    def L(self):
        return 1 << self.a

    @property
    def directed_classes(self):
        return self.radix ** (2 * self.a)

    @property
    def class_edges(self):
        return self.copies * self.degree ** 2

    @property
    def edge_count(self):
        return self.directed_classes * self.class_edges

    @property
    def vertex_count(self):
        return 2 * self.directed_classes * self.copies * self.degree

    @property
    def packet_count(self):
        return self.edge_count // self.L

    def _word(self, word):
        if (type(word) is not tuple or len(word) != self.a or
                any(type(x) is not int or not 0 <= x < self.radix for x in word)):
            raise ValueError('label must be an immutable radix word')
        return word

    def edge_to_slot(self, edge):
        if type(edge) is not tuple or len(edge) != 5:
            raise ValueError('edge address must have five entries')
        row, col, copy, i, j = edge
        self._word(row)
        self._word(col)
        if (any(type(x) is not int for x in (copy, i, j)) or
                not 0 <= copy < self.copies or not 0 <= i < self.degree or
                not 0 <= j < self.degree):
            raise ValueError('edge address outside family')
        offset = copy * self.degree ** 2 + i * self.degree + j
        pairs = tuple((min(x, y), max(x, y)) for x, y in zip(row, col))
        equal = [d for d, (x, y) in enumerate(pairs) if x == y]
        copies_per_class = 1 << len(equal)
        packet_index, copy_index = divmod(offset, copies_per_class)
        bits = sum((int(row[d] > col[d]) << d) for d in range(self.a))
        bits |= sum(((copy_index >> k) & 1) << d for k, d in enumerate(equal))
        return pairs, packet_index, bits

    def slot_to_edge(self, address):
        if type(address) is not tuple or len(address) != 3:
            raise ValueError('slot address must have three entries')
        pairs, packet_index, bits = address
        if (type(pairs) is not tuple or len(pairs) != self.a or
                any(type(pair) is not tuple or len(pair) != 2 or
                    any(type(x) is not int for x in pair) or
                    not 0 <= pair[0] <= pair[1] < self.radix for pair in pairs)):
            raise ValueError('invalid unordered label pairs')
        equal = [d for d, (x, y) in enumerate(pairs) if x == y]
        copies_per_class = 1 << len(equal)
        if (type(packet_index) is not int or not 0 <= packet_index < self.class_edges // copies_per_class or
                type(bits) is not int or not 0 <= bits < self.L):
            raise ValueError('packet slot outside family')
        row = tuple(y if (bits >> d) & 1 else x for d, (x, y) in enumerate(pairs))
        col = tuple(x if (bits >> d) & 1 else y for d, (x, y) in enumerate(pairs))
        copy_index = sum(((bits >> d) & 1) << k for k, d in enumerate(equal))
        offset = packet_index * copies_per_class + copy_index
        copy, within = divmod(offset, self.degree ** 2)
        i, j = divmod(within, self.degree)
        return row, col, copy, i, j

    def audit(self, *, degree_bound=None):
        """Check symbolic loads and sufficient D.3 inequalities, not the solver."""
        if degree_bound is None:
            degree_bound = self.degree
        if (type(degree_bound) is not int or degree_bound < self.degree or
                degree_bound.bit_length() > 262144):
            raise ValueError('degree bound must cover the graph and fit the bit limit')
        M, D, L, r = self.edge_count, self.directed_classes, self.L, self.radix
        side_load = M // r
        child = 2 * side_load
        return {
            'status': 'EXPLICIT_MULTI_COORDINATE_PACKING_WITNESS',
            'radix': r, 'a': self.a, 'L': L, 'directed_classes': D,
            'degree': self.degree, 'degree_bound': degree_bound,
            'class_edges': self.class_edges, 'padded_class_size': self.class_edges,
            'parent_edges': M, 'vertices': self.vertex_count, 'packets': self.packet_count,
            'row_load_each_group': side_load, 'column_load_each_group': side_load,
            'child_half_wires_each_group': child,
            'packing_numeric_conditions': M >= 2 * D ** 2 * degree_bound and M >= L * D and 2 * L <= degree_bound,
            'packing_count_bound': D * self.class_edges <= 3 * M,
            'side_load_bound': r * side_load <= 3 * M,
            'child_six_M_over_r_bound': r * child <= 6 * M,
            'strict_one_eighth_shrink': 8 * child < M,
            'three_M_over_32_bound': 32 * child <= 3 * M,
            'a_has_active_schedule_parity': self.a % 2 == 0,
            'manuscript_schedule_verified': False,
            'full_contraction_executed': False,
            'deterministic_constructor_replayed': False,
            'uniform_complexity_proven': False,
        }
