"""Immutable tensor descriptions; inherited descriptions are shared by reference."""
from dataclasses import dataclass
from .parameters import natural


@dataclass(frozen=True)
class OriginalTensor:
    """Base-ring entry procedure supplied by the input description.

    The callback receives (Boolean ports, execution budget) and returns canonical
    integer V coefficients at creation precision. Its claimed time/space bound
    remains an input hypothesis, not something sampling can establish.
    """
    arity: int
    creation_precision: int
    ell: int
    description: bytes
    evaluate: object

    def __post_init__(self):
        natural(self.arity,'arity');natural(self.creation_precision,'creation precision',1)
        natural(self.ell,'jet length',1)
        if type(self.description) is not bytes or not callable(self.evaluate):
            raise ValueError('immutable description bytes and entry procedure required')

    def entry(self,bits,ring):
        if len(bits)!=self.arity or any(type(x) is not int or x not in (0,1) for x in bits):
            raise ValueError('Boolean port assignment required')
        if ring.p<self.creation_precision or ring.ell!=self.ell:
            raise ValueError('entry precision or truncation mismatch')
        ring.budget.tick()
        values=self.evaluate(bits,ring.budget)
        modulus=1 << self.creation_precision
        if (type(values) is not tuple or len(values)!=self.ell or
            any(type(x) is not int or not 0<=x<modulus for x in values)):
            raise ValueError('entry procedure must return canonical creation-time base-ring coefficients')
        return tuple(ring.scalar(x) for x in values)


@dataclass(frozen=True)
class DenseTensor:
    arity: int
    creation_precision: int
    values: tuple[tuple[int, ...], ...]

    def __post_init__(self):
        natural(self.arity,'arity'); natural(self.creation_precision,'creation precision',1)
        if (type(self.values) is not tuple or len(self.values)!=(1 << self.arity)
            or not self.values or type(self.values[0]) is not tuple or not self.values[0]):
            raise ValueError('complete immutable dense coefficient table required')
        ell=len(self.values[0]);mod=1 << self.creation_precision
        if any(type(v) is not tuple or len(v)!=ell or any(type(x) is not int or not 0<=x<mod for x in v) for v in self.values):
            raise ValueError('canonical creation-time coefficients required')

    def entry(self, bits, ring):
        if len(bits)!=self.arity or ring.p<self.creation_precision:
            raise ValueError('entry arity or canonical-lift precision mismatch')
        value=self.values[sum(bit << j for j,bit in enumerate(bits))]
        if len(value)!=ring.ell:raise ValueError('truncation length mismatch')
        return tuple(ring.scalar(c) for c in value)


@dataclass(frozen=True)
class EqualityTensor:
    arity: int
    creation_precision: int

    def entry(self,bits,ring):
        if len(bits)!=self.arity or ring.p<self.creation_precision:raise ValueError('equality entry metadata')
        return ring.integer(int(not bits or all(x==bits[0] for x in bits)))


@dataclass(frozen=True)
class ClauseTensor:
    positive: tuple[bool, ...]
    creation_precision: int

    @property
    def arity(self):return len(self.positive)

    def entry(self,bits,ring):
        if len(bits)!=self.arity or ring.p<self.creation_precision:raise ValueError('clause entry metadata')
        return ring.integer(int(any(bool(bit)==positive for bit,positive in zip(bits,self.positive))))


@dataclass(frozen=True)
class Vertex:
    side: str
    identity: int
    ports: tuple[int, ...]
    tensor: object


@dataclass(frozen=True)
class Network:
    wires: int
    vertices: tuple[Vertex, ...]

    def __post_init__(self):
        natural(self.wires,'wire count')
        if type(self.vertices) is not tuple:raise ValueError('immutable vertices required')
        seen=set();owners=set()
        for v in self.vertices:
            if type(v) is not Vertex or v.side not in ('row','column') or (v.side,v.identity) in seen:
                raise ValueError('distinct tagged vertex identities required')
            natural(v.identity,'vertex identity');seen.add((v.side,v.identity))
            if type(v.ports) is not tuple or len(v.ports)!=v.tensor.arity:
                raise ValueError('tensor port arity mismatch')
            for e in v.ports:
                natural(e,'edge')
                if e>=self.wires or (v.side,e) in owners:raise ValueError('invalid or repeated wire endpoint')
                owners.add((v.side,e))
        if len(owners)!=2*self.wires:raise ValueError('each wire requires both endpoints')

    @property
    def maximum_degree(self):return max((len(v.ports) for v in self.vertices),default=0)

    def edges(self):
        ends={side:{} for side in ('row','column')}
        for v in self.vertices:
            for e in v.ports:ends[v.side][e]=v.identity
        return tuple((ends['row'][e],ends['column'][e]) for e in range(self.wires))


def direct(network,ring):
    """Paper leaf routine: direct Boolean summation, with polynomial working space."""
    answer=ring.zero
    for assignment in range(1 << network.wires):
        ring.budget.tick()
        term=ring.one
        for vertex in network.vertices:
            bits=tuple((assignment >> e)&1 for e in vertex.ports)
            term=ring.mul(term,ring.canonical(vertex.tensor.entry(bits,ring)))
        answer=ring.add(answer,term)
    return answer
