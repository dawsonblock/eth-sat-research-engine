"""Finite child graphs with immutable, creation-precision entry recipes.

This is a bridge towards recursive inputs.  It evaluates each tensor entry at
its creation precision, then lifts its coordinate representatives.  It does
not yet run the D.4.4 transformation recursively.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product

from veritas.research.eth_arithmetic.creation_lifts import CreationJetEntry
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.tensor import TensorNetwork
from .lazy_children import GroupChildDescription, PacketTensorEntry, _Budget


def _immutable_tree(value):
    return (type(value) in (int, str) or
            (type(value) is tuple and all(_immutable_tree(item) for item in value)))


@dataclass(frozen=True)
class CreatedDenseTensor:
    """A bounded dense table whose entries were captured at creation time."""
    arity: int
    entries: tuple[CreationJetEntry, ...]

    def __post_init__(self):
        if type(self.arity) is not int or not 0 <= self.arity <= 16:
            raise ValueError('finite dense arity must be in 0..16')
        if type(self.entries) is not tuple or len(self.entries) != 1 << self.arity:
            raise ValueError('dense entry table has the wrong size')
        if any(not isinstance(entry, CreationJetEntry) for entry in self.entries):
            raise TypeError('creation-time jet entries required')
        first = self.entries[0]
        if any((e.creation_precision, e.defining_polynomial, len(e.coefficients)) !=
               (first.creation_precision, first.defining_polynomial, len(first.coefficients))
               for e in self.entries):
            raise ValueError('dense entries have inconsistent creation rings')

    def evaluate(self, bits, ring, budget):
        if len(bits) != self.arity or any(type(bit) is not int or bit not in (0, 1) for bit in bits):
            raise ValueError('tensor index must be Boolean')
        budget.tick()
        index = sum(bit << i for i, bit in enumerate(bits))
        return self.entries[index].evaluate(ring)


@dataclass(frozen=True)
class CreatedPacketTensor:
    """Lazy packet recipe evaluated at its fixed creation precision."""
    recipe: PacketTensorEntry
    creation_precision: int
    defining_polynomial: int
    jet_length: int

    def __post_init__(self):
        if not isinstance(self.recipe, PacketTensorEntry):
            raise TypeError('immutable packet recipe required')
        if not all(_immutable_tree(getattr(self.recipe, name))
                   for name in ('packet_id', 'ports', 'variables', 'rows',
                                'target_modes', 'source_modes')):
            raise ValueError('packet recipe must be deeply immutable')
        JetRing(ExtensionRing(self.creation_precision, self.defining_polynomial), self.jet_length)

    @property
    def arity(self):
        return len(self.recipe.ports)

    def evaluate(self, bits, ring, budget):
        if (not isinstance(ring, JetRing) or ring.base.f != self.defining_polynomial or
                ring.base.p < self.creation_precision or ring.length != self.jet_length):
            raise ValueError('incompatible evaluation ring or decreased precision')
        created_ring = JetRing(ExtensionRing(self.creation_precision,
                                             self.defining_polynomial), self.jet_length)
        # Recompute the entry at its creation precision, never at the larger
        # target precision: canonical lifting does not preserve arithmetic.
        entry = self.recipe.evaluate(tuple(bits), created_ring, budget)
        return CreationJetEntry.capture(created_ring, entry).evaluate(ring)


@dataclass(frozen=True)
class DescribedVertex:
    side: str
    label: str
    ports: tuple[int, ...]
    tensor: CreatedDenseTensor | CreatedPacketTensor

    def __post_init__(self):
        if self.side not in ('row', 'column') or type(self.label) is not str:
            raise ValueError('invalid child vertex identity')
        if (type(self.ports) is not tuple or any(type(p) is not int or p < 0 for p in self.ports) or
                len(set(self.ports)) != len(self.ports)):
            raise ValueError('invalid immutable vertex ports')
        if not isinstance(self.tensor, (CreatedDenseTensor, CreatedPacketTensor)) or len(self.ports) != self.tensor.arity:
            raise ValueError('vertex arity and entry recipe do not agree')


@dataclass(frozen=True)
class DescribedNetwork:
    edges: int
    vertices: tuple[DescribedVertex, ...]

    def __post_init__(self):
        if type(self.edges) is not int or not 0 <= self.edges <= 64:
            raise ValueError('finite described network supports 0..64 edges')
        if type(self.vertices) is not tuple or any(not isinstance(v, DescribedVertex) for v in self.vertices):
            raise ValueError('vertices must be immutable descriptions')
        incidence = Counter((side, port) for vertex in self.vertices
                            for side in (vertex.side,) for port in vertex.ports)
        if incidence != Counter({(side, edge): 1 for side in ('row', 'column')
                                 for edge in range(self.edges)}):
            raise ValueError('every edge must meet one vertex on each side')

    def bipartite_edges(self):
        """Expose edge endpoints in port order for a subsequent packing."""
        owners = [{} for _ in range(self.edges)]
        for side in ('row', 'column'):
            vertices = (vertex for vertex in self.vertices if vertex.side == side)
            for index, vertex in enumerate(vertices):
                for edge in vertex.ports:
                    owners[edge][side] = index
        return tuple((owner['row'], owner['column']) for owner in owners)


def describe_integer_network(network, *, creation_precision, defining_polynomial,
                             jet_length=1):
    """Capture an explicit bipartite integer network at root precision."""
    if not isinstance(network, TensorNetwork):
        raise TypeError('TensorNetwork required')
    ring = JetRing(ExtensionRing(creation_precision, defining_polynomial), jet_length)
    vertices = []
    for factor in network.factors:
        if factor.label.startswith(('row:', 'clause:')):
            side = 'row'
        elif factor.label.startswith(('col:', 'variable:')):
            side = 'column'
        else:
            raise ValueError('factor label must identify one bipartite side')
        entries = tuple(CreationJetEntry.capture(ring, ring.elem([[value]]))
                        for value in factor.table)
        vertices.append(DescribedVertex(side, factor.label, tuple(factor.ports),
                                        CreatedDenseTensor(len(factor.ports), entries)))
    return DescribedNetwork(network.edges, tuple(vertices))


def describe_group_child(child, mode_certificate, *, original_creation_precisions):
    """Freeze a finite v39 group child as a bipartite described network.

    The caller supplies the creation precision of each original vertex in
    child order; it is not inferred from the later packet precision.
    """
    if not isinstance(child, GroupChildDescription):
        raise TypeError('GroupChildDescription required')
    if (type(original_creation_precisions) is not tuple or
            len(original_creation_precisions) != len(child.original_vertices)):
        raise ValueError('one immutable creation precision is required per original vertex')
    p = mode_certificate['precision']
    f = first_irreducible(mode_certificate['extension_degree'])
    length = mode_certificate['jet_length']
    vertices = []
    for vertex, created_at in zip(child.original_vertices, original_creation_precisions):
        if type(created_at) is not int or not 1 <= created_at <= p:
            raise ValueError('invalid original tensor creation precision')
        created_ring = JetRing(ExtensionRing(created_at, f), length)
        entries = tuple(CreationJetEntry.capture(created_ring, created_ring.elem([[value]]))
                        for value in vertex.table)
        vertices.append(DescribedVertex('row', vertex.label, vertex.ports,
                                        CreatedDenseTensor(len(vertex.ports), entries)))
    for packet in child.packet_tensors:
        vertices.append(DescribedVertex('column', f'packet:{packet.packet_id}', packet.ports,
                                        CreatedPacketTensor(packet, p, f, length)))
    return DescribedNetwork(child.edge_count, tuple(vertices))


def contract_described_network(network, ring, *, max_work=250_000, timeout_s=10.0,
                               max_edges=12):
    """Direct finite contraction of a described graph, with no entry cache."""
    if not isinstance(network, DescribedNetwork) or not isinstance(ring, JetRing):
        raise TypeError('DescribedNetwork and JetRing required')
    if type(max_edges) is not int or not 0 <= max_edges <= 16 or network.edges > max_edges:
        raise ValueError('finite described-network edge limit exceeded')
    budget = _Budget(max_work, timeout_s)
    total = ring.zero
    for bits in product((0, 1), repeat=network.edges):
        budget.tick()
        term = ring.one
        for vertex in network.vertices:
            value = vertex.tensor.evaluate(tuple(bits[p] for p in vertex.ports), ring, budget)
            term = ring.mul(term, value)
            if term == ring.zero:
                break
        total = ring.add(total, term)
    return {'result': total, 'work_units': budget.used,
            'full_recursive_contraction': False,
            'subexponential_runtime_proven': False}
