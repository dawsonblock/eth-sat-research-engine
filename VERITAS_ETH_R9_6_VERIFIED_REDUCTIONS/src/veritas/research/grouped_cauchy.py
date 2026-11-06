"""Exact grouped coefficient modes for the manuscript's local Cauchy kernel.

At an interpolation node t, matched (row i, col j=i+t) ports must
share a group. The *cross-group* kernel coefficients have zero constant
term. For every Taylor order the cross-group coefficient matrix is
factored into rank-one rational outer products by exact elimination.

These are bounded coefficient-wise low-rank modes, NOT the manuscript's
D.4.4 symbol-grouped weighted factorization or asymptotic packing proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from veritas.research.cauchy_deformation import shifted_integral_kernel, _contract_with_kernel
from veritas.research.hermite_ring import modular_fraction
from veritas.research.tensor import TensorNetwork


@dataclass(frozen=True)
class GroupMode:
    row_group: int
    column_group: int
    coefficient_degree: int
    u: tuple[Fraction,...]
    v: tuple[Fraction,...]


@dataclass(frozen=True)
class GroupSummary:
    row_groups: tuple[int,...]
    column_groups: tuple[int,...]
    cross_coefficients: int
    rank_one_modes: int
    max_coefficient_rank: int
    zero_constant_cross_checked: bool
    node: int
    group_span: int


def _outer_modes(matrix: tuple[tuple[Fraction,...],...]) -> tuple[tuple[tuple[Fraction,...],tuple[Fraction,...]], ...]:
    """Exact pivoted rank decomposition M=sum u_k v_k^T over Q."""
    if not matrix:return ()
    nrows=len(matrix);ncols=len(matrix[0])
    if any(len(row)!=ncols for row in matrix):raise ValueError('ragged matrix')
    remainder=[list(row) for row in matrix]
    terms=[]
    while True:
        pivot=next(((i,j) for i in range(nrows) for j in range(ncols) if remainder[i][j]),None)
        if pivot is None:break
        i,j=pivot
        x=remainder[i][j]
        u=tuple(remainder[k][j] for k in range(nrows))
        v=tuple(remainder[i][k]/x for k in range(ncols))
        terms.append((u,v))
        for k in range(nrows):
            for ell in range(ncols):
                remainder[k][ell]-=u[k]*v[ell]
    assert all(not x for row in remainder for x in row)
    return tuple(terms)


def group_cauchy_modes(*, edges: int, packet_size: int=2, node: int=1,
                        jet_order: int=5, group_span: int=1
                        ) -> tuple[tuple[tuple[tuple[Fraction,...],...],...], tuple[GroupMode,...],GroupSummary]:
    if type(edges) is not int or not 0<=edges<=8:
        raise ValueError('edges must be 0..8')
    if type(packet_size) is not int or packet_size not in (1,2,4,8):
        raise ValueError('packet_size must be a power of two <=8')
    if type(node) is not int or not -packet_size<=node<packet_size:
        raise ValueError('node outside interpolation grid')
    if type(jet_order) is not int or not 1<=jet_order<=20:
        raise ValueError('jet_order must be 1..20')
    if type(group_span) is not int or not 1<=group_span<=packet_size:
        raise ValueError('group_span must be in 1..packet_size')
    mat=shifted_integral_kernel(packet_size,node,max_order=jet_order)
    row_groups=tuple(i//packet_size*(packet_size//group_span+1)+(i%packet_size)//group_span for i in range(edges))
    col_groups=[]
    for j in range(edges):
        candidate=j-node
        if candidate>=0 and candidate<edges and candidate//packet_size==j//packet_size:
            col_groups.append(row_groups[candidate])
        else:
            col_groups.append(row_groups[j])
    modes=[]
    coefficients=0
    max_rank=0
    reconstruction={}
    for rg in sorted(set(row_groups)):
        ris=[i for i in range(edges) if row_groups[i]==rg]
        for cg in sorted(set(col_groups)):
            if rg==cg:continue
            cjs=[j for j in range(edges) if col_groups[j]==cg]
            for degree in range(jet_order):
                block=tuple(tuple(mat[i%packet_size][j%packet_size][degree]
                                  if i//packet_size==j//packet_size and degree<len(mat[i%packet_size][j%packet_size])
                                  else Fraction(0) for j in cjs) for i in ris)
                if degree==0 and any(v for row in block for v in row):
                    raise AssertionError('nonzero cross coefficient at interpolation node')
                pieces=_outer_modes(block)
                max_rank=max(max_rank,len(pieces))
                coefficients+=sum(bool(x) for row in block for x in row)
                for u,v in pieces:
                    modes.append(GroupMode(rg,cg,degree,u,v))
                # Independent exact recomposition, including zeros.
                for ii,i in enumerate(ris):
                    for jj,j in enumerate(cjs):
                        value=sum((u[ii]*v[jj] for u,v in pieces),Fraction(0))
                        assert value==block[ii][jj]
                        reconstruction[(i,j,degree)]=value
    # Recompose all slots: local entries are taken directly, cross entries
    # come exclusively from exact rational low-rank terms above.
    full=[]
    for i in range(edges):
        columns=[]
        for j in range(edges):
            if i//packet_size!=j//packet_size:
                columns.append((Fraction(0),)*jet_order)
            elif row_groups[i]==col_groups[j]:
                p=mat[i%packet_size][j%packet_size]
                columns.append(tuple(p[k] if k<len(p) else Fraction(0) for k in range(jet_order)))
            else:
                columns.append(tuple(reconstruction[(i,j,k)] for k in range(jet_order)))
            if i//packet_size==j//packet_size:
                ref=mat[i%packet_size][j%packet_size]
                if columns[-1]!=tuple(ref[k] if k<len(ref) else Fraction(0) for k in range(jet_order)):
                    raise AssertionError('grouped kernel reconstruction failed')
        full.append(tuple(columns))
    return tuple(full),tuple(modes),GroupSummary(row_groups,tuple(col_groups),coefficients,len(modes),max_rank,True,node,group_span)


def grouped_cauchy_jet_mod(net: TensorNetwork, *, packet_size: int=2, node: int=1,
                             group_span:int=1,precision_bits:int=8,jet_order:int=5,
                             timeout_s:float=10.0) -> tuple[tuple[int,...],tuple[GroupMode,...],GroupSummary]:
    if net.edges>6:raise ValueError('grouped reference supports at most 6 edges')
    if type(precision_bits) is not int or not 1<=precision_bits<=128:
        raise ValueError('precision_bits must be 1..128')
    matrix,modes,summary=group_cauchy_modes(edges=net.edges,packet_size=packet_size,
                    node=node,jet_order=jet_order,group_span=group_span)
    # Feed the exact grouped representation back into a COMPLETE, independent
    # contraction. This is still 4**edges in the worst case; honest about it.
    # _contract_with_kernel expects packet-local indexing; we instead use a
    # small exact duplicated implementation for the general grouped matrix.
    M=net.edges
    from veritas.research.cauchy_deformation import _factor_product, _mul
    from time import monotonic
    deadline=monotonic()+timeout_s
    out=[Fraction(0)]*jet_order
    for X in range(1<<M):
        B=_factor_product(net,X,'col')
        if not B:continue
        z=[]
        for i in range(M):
            zz=[Fraction(0)]*jet_order
            for j in range(M):
                if X&(1<<j):
                    for k,v in enumerate(matrix[i][j]):zz[k]+=v
            z.append(tuple(zz))
        for Y in range(1<<M):
            if monotonic()>deadline:raise TimeoutError('grouped jet contraction timed out')
            A=_factor_product(net,Y,'row')
            if not A:continue
            cur=(Fraction(A*B),)
            for i in range(M):
                term=z[i] if Y&(1<<i) else tuple((Fraction(1) if k==0 else Fraction(0))-v for k,v in enumerate(z[i]))
                cur=_mul(cur,term,jet_order)
            for k,v in enumerate(cur):out[k]+=v
    return tuple(modular_fraction(q,precision_bits) for q in out),modes,summary
