"""The manuscript's whole-label conditional-expectation packet construction."""
from collections import Counter
from dataclasses import dataclass
from itertools import product
from types import MappingProxyType
from veritas.research.eth_packing_v26.expectation import expected_sq_load_scaled
from veritas.research.eth_packing_v26.packet_bijection import encode_class_offset


@dataclass(frozen=True)
class Packet:
    pattern: tuple[tuple[int,int], ...]
    index: int
    slots: tuple[tuple[int,int], ...]


@dataclass(frozen=True)
class Layout:
    a: int
    r: int
    rows: object
    columns: object
    packets: tuple[Packet, ...]
    padded_height: int
    variance_scaled: int

    @property
    def L(self):return 1 << self.a

    def labels(self,side):return self.rows if side=='row' else self.columns


def construct(network,a,delta,budget,*,r=64,require_bounds=True):
    """Enumerate whole candidate labels as in lem:tensor-packets.

    r=64 is fixed by the source executor. Other r values are available solely
    to check this algebraic construction on finite component tests.
    All padded packets, including empty ones, are represented.
    """
    if type(a) is not int or a<1 or type(r) is not int or r<2:raise ValueError('packing parameters')
    budget.items(a*len(network.vertices),'vertex labels')
    budget.bits(2*a*r.bit_length(),'class count')
    M=network.wires;L=1 << a;D=r**(2*a)
    if not M:raise ValueError('empty network is a leaf')
    if network.maximum_degree>delta:raise ValueError('degree bound does not cover network')
    if require_bounds and not (M>=2*D*D*delta and M>=L*D and 2*L<=delta):
        raise ValueError('manuscript packing hypotheses do not hold')
    edges=network.edges();assigned={};labels={side:{} for side in ('row','column')}
    score=expected_sq_load_scaled(edges,assigned,r,a,budget)
    initial=score
    for vertex in sorted(network.vertices,key=lambda v:(v.side,v.identity)):
        tag='R' if vertex.side=='row' else 'C'
        if not vertex.ports:
            word=(0,)*a
        else:
            best=None
            for candidate in product(range(r),repeat=a):
                budget.tick()
                for j,value in enumerate(candidate):assigned[tag,vertex.identity,j]=value
                trial=expected_sq_load_scaled(edges,assigned,r,a,budget)
                if best is None or (trial,candidate)<best:best=trial,candidate
            next_score,word=best
            if next_score>score:raise ArithmeticError('conditional expectation increased')
            score=next_score
        for j,value in enumerate(word):assigned[tag,vertex.identity,j]=value
        labels[vertex.side][vertex.identity]=word
    buckets={}
    for e,(row,col) in enumerate(edges):
        buckets.setdefault((labels['row'][row],labels['column'][col]),[]).append(e)
    H=((max(map(len,buckets.values()))+L-1)//L)*L
    actual_score=D*sum(len(es)**2 for es in buckets.values())
    if actual_score!=score or score>initial or score-M*M>2*M*delta*D:
        raise ArithmeticError('directed-class variance bound failed')
    packet_count=D*H//L;budget.items(packet_count,'complete padded packet inventory')
    occupied={}
    for (row,col),es in buckets.items():
        for offset,e in enumerate(es):
            address=encode_class_offset(row,col,offset,radix=r,width=a,padded_height=H)
            occupied.setdefault((address.pattern,address.packet),[]).append((address.slot,e))
    pairs=tuple((lo,hi) for lo in range(r) for hi in range(lo,r));packets=[]
    for pattern in product(pairs,repeat=a):
        equal=sum(lo==hi for lo,hi in pattern)
        for index in range(H >> equal):
            budget.tick()
            packets.append(Packet(pattern,index,tuple(sorted(occupied.get((pattern,index),())))))
    if len(packets)!=packet_count:raise ArithmeticError('padded packet bijection count failed')
    loads=Counter((v.side,j,labels[v.side][v.identity][j]) for v in network.vertices for _ in v.ports for j in range(a))
    if require_bounds and (D*H>3*M or r*max(loads.values(),default=0)>3*M):
        raise ArithmeticError('manuscript packet count or group-load bound failed')
    return Layout(a,r,MappingProxyType(labels['row']),MappingProxyType(labels['column']),
                  tuple(packets),H,score-M*M)
