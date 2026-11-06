"""Small-instance valuation-certified expansion of Cauchy cross-group modes.

At an interpolation node t, W_ij(t) != 0 only when j-i=t.
We give each matched row/column pair one group; unmatched columns are
isolated groups. All cross-group W_ij(t+2L*z) vanish at z=0.

Expanding l_y(local + sum cross) into a local term or one cross mode
per row is an exact identity. Terms can be omitted only when a product
has z-order >= jet_order or its *certified* 2-adic valuation >=p.

This IS NOT the manuscript's low-rank, collision-packed D.4.4 modes,
its bounded mode-count theorem, or recursive child-network algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from time import monotonic

from veritas.research.tensor import TensorNetwork
from veritas.research.cauchy_deformation import shifted_integral_kernel, _factor_product
from veritas.research.hermite_ring import modular_fraction


def _trim_zeros(v: tuple[int,...]) -> tuple[int,...]:
    while v and v[-1] == 0:
        v=v[:-1]
    return v


def _add_mod(a: tuple[int,...], b: tuple[int,...], p: int, order: int) -> tuple[int,...]:
    mod=(1<<p)-1
    return tuple(((a[i] if i<len(a) else 0)+(b[i] if i<len(b) else 0)) & mod for i in range(order))


def _mul_mod(a: tuple[int,...], b: tuple[int,...], p: int, order: int) -> tuple[int,...]:
    out=[0]*order
    mask=(1<<p)-1
    for i,x in enumerate(a[:order]):
        if x:
            for j,y in enumerate(b[:order-i]):
                if y:
                    out[i+j]=(out[i+j]+x*y)&mask
    return tuple(out)


def _v2(x: int) -> int:
    x=abs(x)
    return (x & -x).bit_length()-1


def _min_v2_coeff(poly: tuple[Fraction,...]) -> int | None:
    if not any(poly): return None
    return min(_v2(q.numerator)-_v2(q.denominator)
               for q in poly if q)


@dataclass(frozen=True)
class CrossMode:
    row: int
    column: int
    source_group: int
    target_group: int
    min_valuation: int | None
    min_z_degree: int | None


@dataclass(frozen=True)
class ModeStats:
    evaluated_pairs: int
    expanded_terms: int
    dropped_by_valuation: int
    dropped_by_z_degree: int
    available_cross_modes: int
    active_node: int
    partition_rule: str = 'node-matching-single-slot-groups-v1'


def _node_groups(M: int, L: int, t: int) -> tuple[tuple[int,...],tuple[int,...]]:
    rows = tuple(range(M))
    cols=[]
    for j in range(M):
        candidate=j-t
        if 0<=candidate<M and candidate//L==j//L:
            cols.append(candidate)
        else:
            cols.append(M+j)
    return rows, tuple(cols)


def cauchy_modes_at_node(network: TensorNetwork, *, packet_size: int=2,
                         node: int=1, precision_bits: int=12, jet_order: int=6,
                         max_edges: int=6, timeout_s: float=10.0
                         ) -> tuple[tuple[int,...],tuple[CrossMode,...],ModeStats]:
    """Calculate an exact modular Cauchy jet by mode expansion, not full polynomial shift.

    Return (jet coefficients modulo 2**p, modes with *exact* lower-bound
    valuations, expansion statistics). Cross modes are independently
    certified to vanish at the chosen interpolation node.
    """
    if type(packet_size) is not int or packet_size not in (1,2,4,8):
        raise ValueError('packet_size must be 1,2,4,8')
    if type(node) is not int or not -packet_size<=node<packet_size:
        raise ValueError('node is outside the Cauchy grid')
    if type(precision_bits) is not int or not 1<=precision_bits<=128:
        raise ValueError('precision_bits must be 1..128')
    if type(jet_order) is not int or not 1<=jet_order<=24:
        raise ValueError('jet_order must be 1..24')
    if type(max_edges) is not int or not 0<=max_edges<=6 or network.edges>max_edges:
        raise ValueError('at most six network wires are supported')
    if not 0<timeout_s<=30:
        raise ValueError('timeout budget must be 0..30 seconds')
    M=network.edges
    rows,cols=_node_groups(M,packet_size,node)
    matrix=shifted_integral_kernel(packet_size,node,max_order=jet_order)
    zero=(0,)*jet_order
    one=(1,)+(0,)*(jet_order-1)
    mod=(1<<precision_bits)-1
    W={}
    modes=[]
    lower_bounds={}
    for i in range(M):
        for j in range((i//packet_size)*packet_size,min(M,(i//packet_size+1)*packet_size)):
            exact=matrix[i%packet_size][j%packet_size]
            W[i,j]=tuple(modular_fraction(c,precision_bits) for c in exact) + (0,)*max(0,jet_order-len(exact))
            W[i,j]=W[i,j][:jet_order]
            if rows[i]!=cols[j]:
                if exact[0]:
                    raise AssertionError('cross-mode did not vanish at interpolation node')
                valuation=_min_v2_coeff(tuple(exact))
                degree=next((k for k,c in enumerate(exact) if c),None)
                if valuation is not None and valuation < 0:
                    raise AssertionError('cross-mode is not 2-adically integral')
                modes.append(CrossMode(i,j,cols[j],rows[i],valuation,degree))
                lower_bounds[i,j]=(valuation,degree)
    deadline=monotonic()+timeout_s
    total=[0]*jet_order
    pairs=0
    expanded=0
    drop_v=drop_z=0
    row_products=[(y,_factor_product(network,y,'row')) for y in range(1<<M)]
    col_products=[(x,_factor_product(network,x,'col')) for x in range(1<<M)]
    for X,B in col_products:
        if not B: continue
        local=[]
        cross=[]
        for i in range(M):
            value=zero
            other=[]
            for j in range((i//packet_size)*packet_size,min(M,(i//packet_size+1)*packet_size)):
                if not X & (1<<j): continue
                if rows[i] == cols[j]:
                    value=_add_mod(value,W[i,j],precision_bits,jet_order)
                else:
                    other.append((W[i,j],lower_bounds[i,j]))
            local.append(value)
            cross.append(other)
        for Y,A in row_products:
            if not A: continue
            pairs+=1
            if pairs%32 == 0 and monotonic()>deadline:
                raise TimeoutError('valuation-certified Cauchy expansion timed out')
            # Each branch represents an explicit choice of local factor or one
            # cross-mode per row. Exact unit factors carry valuation >= 0.
            def walk(i:int,coeff:tuple[int,...],lower_v:int,lower_z:int)->None:
                nonlocal expanded,drop_v,drop_z
                if lower_v>=precision_bits:
                    drop_v+=1
                    return
                if lower_z>=jet_order:
                    drop_z+=1
                    return
                if i==M:
                    expanded+=1
                    for k,val in enumerate(coeff):
                        total[k]=(total[k]+val*(A*B))&mod
                    return
                base=(local[i] if Y&(1<<i) else tuple((one[k]-local[i][k])&mod for k in range(jet_order)))
                walk(i+1,_mul_mod(coeff,base,precision_bits,jet_order),lower_v,lower_z)
                sign=1 if Y&(1<<i) else -1
                for cross_poly,(v,z) in cross[i]:
                    if v is None: continue
                    signed=tuple((sign*x)&mod for x in cross_poly)
                    walk(i+1,_mul_mod(coeff,signed,precision_bits,jet_order),lower_v+v,lower_z+z)
            walk(0,one,0,0)
    return tuple(total),tuple(modes),ModeStats(pairs,expanded,drop_v,drop_z,len(modes),node)
