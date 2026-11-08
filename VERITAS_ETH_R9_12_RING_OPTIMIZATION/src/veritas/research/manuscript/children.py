"""Implicit packet entries and sequential children of eq:tensor-recursion-identity."""
from dataclasses import dataclass
from itertools import product
from .cauchy import Kernel
from .model import Network,Vertex
from .ring import Ring


@dataclass(frozen=True)
class PacketTensor:
    domain: object
    beta: tuple[int, ...]
    packet: int
    group: int
    rows: tuple[tuple[int,int], ...]
    columns: tuple[tuple[int,int], ...]

    @property
    def arity(self):return len(self.rows)+len(self.columns)
    @property
    def creation_precision(self):return self.domain.point.precision

    def entry(self,bits,target_ring):
        point=self.domain.point
        if (len(bits)!=self.arity or target_ring.p<point.precision or
            (target_ring.f,target_ring.ell)!=(point.f,point.ell)):
            raise ValueError('packet creation-time entry metadata mismatch')
        # Recompute at creation precision, then use those canonical integers.
        # Evaluating this recipe directly at target_ring.p would be incorrect.
        r=Ring(point.precision,point.f,point.ell,target_ring.budget)
        ys=bits[:len(self.rows)];xs=bits[len(self.rows):]
        targeted=[];sourced=[]
        for mode,power in self.domain.packet_modes(self.packet,self.beta,r.budget):
            if mode.target==self.group:targeted.append((mode,power))
            if mode.source==self.group:sourced.append((mode,power))
        if sum(power for _,power in targeted)>len(self.rows):return target_ring.zero
        source_factor=r.one_scalar
        for mode,power in sourced:
            linear=0
            for (slot,_),bit in zip(self.columns,xs):
                if slot%self.domain.B==mode.tile:
                    j=(slot-mode.tile)//self.domain.B
                    linear=(linear+pow(j,mode.exponent,1 << r.p)*bit)&r.mask
            source_factor=r.scalar_mul(source_factor,r.scalar_pow(r.scalar(linear),power))
        if source_factor==r.zero_scalar:return target_ring.zero
        r.budget.items(r.e*len(self.rows)*(len(targeted)+1),'packet affine factors')
        kernel_factory=getattr(self.domain,'packet_kernel',None)
        kernel=Kernel(point,r) if kernel_factory is None else kernel_factory(r)
        factors=[]
        for (slot,_),bit in zip(self.rows,ys):
            local=r.zero_scalar
            for (col,_),x in zip(self.columns,xs):
                if x:local=r.scalar_add(local,kernel.value(slot,col))
            constant=local if bit else r.scalar_sub(r.one_scalar,local)
            row=[constant]
            for mode,_ in targeted:
                coefficient=kernel.mode_coefficient(slot,mode.tile,mode.exponent)
                row.append(coefficient if bit else r.scalar_neg(coefficient))
            factors.append(row)
        wanted=tuple(power for _,power in targeted);coefficient=r.zero_scalar
        # Expand one choice per affine row factor, with only a choice vector
        # and exponent counter live. No coefficient-support dictionary grows.
        for choices in product(range(len(targeted)+1),repeat=len(self.rows)):
            r.budget.tick();counts=[0]*len(targeted)
            for choice in choices:
                if choice:counts[choice-1]+=1
            if tuple(counts)!=wanted:continue
            term=r.one_scalar
            for row,choice in zip(factors,choices):term=r.scalar_mul(term,row[choice])
            coefficient=r.scalar_add(coefficient,term)
        return r.embed(r.scalar_mul(coefficient,source_factor))


def child(network,layout,domain,beta,group,*,require_bounds=True,delta=None):
    if len(beta)!=domain.size or any(type(n) is not int or n<0 for n in beta):raise ValueError('invalid exponent vector')
    if sum(n*domain.weight(j) for j,n in enumerate(beta))>=domain.point.precision:
        raise ValueError('exponent vector exceeds valuation budget')
    coordinate=domain.point.coordinate
    groups={(v.side,v.identity):layout.labels(v.side)[v.identity][coordinate] for v in network.vertices}
    owners={(v.side,e):v.identity for v in network.vertices for e in v.ports}
    variables=tuple((side,e) for side in ('row','column') for e in range(network.wires)
                    if groups[side,owners[side,e]]==group)
    edge_ids={key:i for i,key in enumerate(variables)};vertices=[]
    for vertex in network.vertices:
        if groups[vertex.side,vertex.identity]==group:
            vertices.append(Vertex('row',len(vertices),tuple(edge_ids[vertex.side,e] for e in vertex.ports),vertex.tensor))
    for pid,packet in enumerate(layout.packets):
        rows=tuple((slot,e) for slot,e in packet.slots if ('row',e) in edge_ids)
        cols=tuple((slot,e) for slot,e in packet.slots if ('column',e) in edge_ids)
        ports=tuple(edge_ids['row',e] for _,e in rows)+tuple(edge_ids['column',e] for _,e in cols)
        # Empty packet vertices are significant: a positive exponent with an
        # empty source or no target rows contributes zero, not the empty unit.
        recipe=PacketTensor(domain,beta,pid,group,rows,cols)
        vertices.append(Vertex('column',pid,ports,recipe))
    result=Network(len(variables),tuple(vertices))
    if require_bounds:
        if layout.r!=64 or 64*result.wires>6*network.wires or 8*result.wires>network.wires:
            raise ArithmeticError('paper child wire bound failed')
        if delta is None or result.maximum_degree>delta:raise ArithmeticError('paper child degree bound failed')
    return result


def point_contraction(network,layout,domain,ring,solve_child,*,require_bounds=True,delta=None):
    """One tuple sum and one group product live; child calls are sequential."""
    if require_bounds:
        D=layout.L >> domain.point.coordinate
        if domain.per_weight*D>6*network.wires:raise ArithmeticError('mode multiplicity bound failed')
    total=ring.zero
    for beta in domain.tuples():
        term=ring.one
        for group in range(layout.r):
            ring.budget.tick()
            descendant=child(network,layout,domain,beta,group,
                             require_bounds=require_bounds,delta=delta)
            term=ring.mul(term,solve_child(descendant,ring.p))
        total=ring.add(total,term)
    return total
