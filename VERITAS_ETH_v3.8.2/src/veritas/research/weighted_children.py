"""Exact weighted grouped Cauchy modes -> explicit polynomial child tensors.

Small research reference for (Z/2**p Z)[z]/(z**q). Cross-group
coefficient matrices are reconstructed from rational rank-one modes and
modes with provably vanishing 2-adic valuation are omitted. Each row
interpolation factor is represented as a polynomial-valued Boolean table.
We then form the complete half-edge factor graph and recursively construct
child tensors on the *actual external boundary variables* of each subtree.

This is a conventional variable-boundary recursion; complexity is
exponential in boundary size and DOES NOT implement D.4.4 packing,
weighted-mode child network theorem or subexponential complexity.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from fractions import Fraction
from itertools import combinations
from time import monotonic

from veritas.research.grouped_cauchy import group_cauchy_modes
from veritas.research.hermite_ring import modular_fraction
from veritas.research.tensor import TensorNetwork


class ChildTensorLimit(Exception):
    """Fail closed when a specified exact-computation budget is exhausted."""


@dataclass(frozen=True)
class WeightedMode:
    row_group: int
    column_group: int
    degree: int
    rank_one_index: int
    v2_lower_bound: int
    discarded_mod_precision: bool


@dataclass(frozen=True)
class JetTable:
    ports: tuple[int, ...]
    values: tuple[tuple[int, ...], ...]
    name: str


@dataclass(frozen=True)
class ChildTensor:
    factor_ids: tuple[int, ...]
    boundary: tuple[int, ...]
    values: tuple[tuple[int, ...], ...]


@dataclass
class ChildStats:
    algorithm: str = 'exact_boundary_tensor_recursive_v1'
    recursion_calls: int = 0
    leaf_tensors: int = 0
    internal_tensors: int = 0
    max_depth: int = 0
    max_boundary_variables: int = 0
    max_join_variables: int = 0
    largest_child_entries: int = 0
    work_assignments: int = 0
    polynomial_products: int = 0
    products_zero_by_z_degree: int = 0
    products_zero_by_valuation: int = 0
    raw_rank_one_modes: int = 0
    kept_rank_one_modes: int = 0
    dropped_rank_one_modes: int = 0
    partition_candidates: int = 0


def _v2_fraction(f: Fraction) -> int:
    def v2(x: int) -> int:
        a = abs(x)
        return (a & -a).bit_length() - 1
    return v2(f.numerator) - v2(f.denominator)


def _v2_poly(x: tuple[int,...], p: int) -> int:
    return min(((v & -v).bit_length() - 1 for v in x if v), default=p)


def _mul(a: tuple[int,...], b: tuple[int,...], p:int, q:int, st: ChildStats) -> tuple[int,...]:
    st.polynomial_products += 1
    zero=(0,)*q
    if not any(a) or not any(b):
        return zero
    za=next(i for i,v in enumerate(a) if v)
    zb=next(i for i,v in enumerate(b) if v)
    if za+zb>=q:
        st.products_zero_by_z_degree+=1
        return zero
    if _v2_poly(a,p)+_v2_poly(b,p)>=p:
        st.products_zero_by_valuation+=1
        return zero
    mask=(1<<p)-1
    result=[0]*q
    for i,x in enumerate(a):
        if x:
            for j,y in enumerate(b[:q-i]):
                if y:
                    result[i+j]=(result[i+j]+x*y)&mask
    return tuple(result)


def _min_mode_valuation(u: tuple[Fraction,...],v: tuple[Fraction,...]) -> int:
    a=min((_v2_fraction(q) for q in u if q),default=None)
    b=min((_v2_fraction(q) for q in v if q),default=None)
    if a is None or b is None:
        raise AssertionError('zero rank-one mode was provided')
    return a+b


def reconstruct_weighted_kernel(*, edges: int, packet_size:int, node:int,
                                 group_span:int, precision_bits:int, jet_order:int
                                 ) -> tuple[tuple[tuple[tuple[int,...],...],...], tuple[WeightedMode,...]]:
    """Certified modular reconstruction of coefficient-wise rank-one modes.

    Dropping a *whole* rank-one mode is safe only if its minimum possible
    2-adic valuation across ALL entries is >= the requested precision.
    The final matrix is independently compared with the unpruned kernel.
    """
    full,modes,summary=group_cauchy_modes(edges=edges,packet_size=packet_size,
                                         node=node,jet_order=jet_order,group_span=group_span)
    rows=summary.row_groups
    cols=summary.column_groups
    rec=[[[full[i][j][k] if rows[i]==cols[j] else Fraction(0)
           for k in range(jet_order)] for j in range(edges)] for i in range(edges)]
    descriptors=[]
    for mid, mode in enumerate(modes):
        bound=_min_mode_valuation(mode.u,mode.v)
        omit=bound>=precision_bits
        descriptors.append(WeightedMode(mode.row_group,mode.column_group,
                                        mode.coefficient_degree,mid,bound,omit))
        if omit:continue
        rr=[i for i,g in enumerate(rows) if g==mode.row_group]
        cc=[j for j,g in enumerate(cols) if g==mode.column_group]
        for ri,i in enumerate(rr):
            for cj,j in enumerate(cc):
                rec[i][j][mode.coefficient_degree]+=mode.u[ri]*mode.v[cj]
    out=[]
    for i in range(edges):
        rr=[]
        for j in range(edges):
            result=tuple(modular_fraction(f,precision_bits) for f in rec[i][j])
            original=tuple(modular_fraction(f,precision_bits) for f in full[i][j])
            if result!=original:
                raise AssertionError('weighted rank-one mode reconstruction failed modulo 2**p')
            rr.append(result)
        out.append(tuple(rr))
    return tuple(out),tuple(descriptors)


def _factor_tables(net: TensorNetwork, kernel:tuple, precision_bits:int, order:int) -> tuple[JetTable,...]:
    m=net.edges
    mask=(1<<precision_bits)-1
    one=(1,)+(0,)*(order-1)
    tables=[]
    for f in net.factors:
        isrow=f.label.startswith('clause:')
        iscol=f.label.startswith('variable:')
        if isrow==iscol:
            raise ValueError('Cauchy half-edge model needs clause/variable-labelled factors')
        ports=tuple(i if isrow else m+i for i in f.ports)
        tables.append(JetTable(ports,tuple((v&mask,)+(0,)*(order-1) for v in f.table),f.label))
    for i in range(m):
        # Factor H_i(Y_i,X_packet) with one row half-wire and packet columns.
        # packet boundary is inferred from nonzero entries of the entire
        # kernel matrix. All coefficients outside its packet are zero.
        js=tuple(j for j in range(m) if any(kernel[i][j]))
        ports=(i,)+tuple(m+j for j in js)
        entries=[]
        for assignment in range(1<<len(ports)):
            y=assignment&1
            value=[0]*order
            for jindex,j in enumerate(js):
                if assignment & (1<<(jindex+1)):
                    for k,c in enumerate(kernel[i][j]):
                        value[k]=(value[k]+c)&mask
            if not y:
                value=[(one[k]-value[k])&mask for k in range(order)]
            entries.append(tuple(value))
        tables.append(JetTable(ports,tuple(entries),f'cauchy-row:{i}'))
    return tuple(tables)


def recursive_weighted_jet(net: TensorNetwork, *, packet_size:int=2,node:int=1,
                            group_span:int=1,precision_bits:int=12,jet_order:int=5,
                            max_edges:int=6,max_boundary_vars:int=12,
                            max_table_entries:int=4096,max_work_assignments:int=250_000,
                            timeout_s:float=10.0
                            ) -> tuple[tuple[int,...],tuple[WeightedMode,...],ChildStats]:
    """Return exact modular Cauchy jet via explicit recursive child tensors.

    An internal child tensor is a function of its boundary half-wire bits.
    Two child tensors are multiplied on their shared/interface assignment,
    then their private interface bits are summed out. No early projection
    is permitted. The construction runs only within strict resource limits.
    """
    if type(packet_size) is not int or packet_size not in (1,2,4,8):
        raise ValueError('invalid Cauchy packet size')
    if type(node) is not int or not -packet_size<=node<packet_size:
        raise ValueError('node outside interpolation grid')
    if type(group_span) is not int or not 1<=group_span<=packet_size:
        raise ValueError('invalid group span')
    if type(precision_bits) is not int or not 1<=precision_bits<=128:
        raise ValueError('invalid precision')
    if type(jet_order) is not int or not 1<=jet_order<=20:
        raise ValueError('invalid jet order')
    if type(max_edges) is not int or not 0<=max_edges<=8 or net.edges>max_edges:
        raise ValueError('wire budget exceeded')
    if type(max_boundary_vars) is not int or not 0<=max_boundary_vars<=16:
        raise ValueError('invalid boundary variable limit')
    if type(max_table_entries) is not int or not 1<=max_table_entries<=65536:
        raise ValueError('invalid child tensor entry limit')
    if type(max_work_assignments) is not int or not 1<=max_work_assignments<=2_000_000:
        raise ValueError('invalid work limit')
    if type(timeout_s) not in (int,float) or not 0<timeout_s<=30:
        raise ValueError('invalid timeout')
    kernel,modes=reconstruct_weighted_kernel(edges=net.edges,packet_size=packet_size,
           node=node,group_span=group_span,precision_bits=precision_bits,jet_order=jet_order)
    tables=_factor_tables(net,kernel,precision_bits,jet_order)
    stats=ChildStats(raw_rank_one_modes=len(modes),
        kept_rank_one_modes=sum(not m.discarded_mod_precision for m in modes),
        dropped_rank_one_modes=sum(m.discarded_mod_precision for m in modes))
    deadline=monotonic()+timeout_s
    mask=(1<<precision_bits)-1
    zero=(0,)*jet_order
    owners={v: set() for v in range(2*net.edges)}
    for fid,factor in enumerate(tables):
        for v in factor.ports: owners[v].add(fid)
    all_ids=tuple(range(len(tables)))
    if not all_ids:
        return (1,)+(0,)*(jet_order-1),modes,stats
    boundary_cache={}

    def boundary(ids:tuple[int,...])->tuple[int,...]:
        if ids not in boundary_cache:
            inside=set(ids)
            boundary_cache[ids]=tuple(sorted(v for v,who in owners.items()
                         if who&inside and who-inside))
        return boundary_cache[ids]

    def check(work:int=0)->None:
        stats.work_assignments+=work
        if stats.work_assignments>max_work_assignments:
            raise ChildTensorLimit('total join/leaf assignment budget exceeded')
        if monotonic()>deadline:
            raise ChildTensorLimit('child tensor recursion deadline exceeded')

    def tensor_size(bound:tuple[int,...])->int:
        if len(bound)>max_boundary_vars or (1<<len(bound))>max_table_entries:
            raise ChildTensorLimit('child boundary table budget exhausted')
        stats.max_boundary_variables=max(stats.max_boundary_variables,len(bound))
        stats.largest_child_entries=max(stats.largest_child_entries,1<<len(bound))
        return 1<<len(bound)

    def choose_split(ids:tuple[int,...])->tuple[tuple[int,...],tuple[int,...]]:
        n=len(ids);half=n//2
        # Exact balanced separator search on small factor sets; bounded
        # deterministic candidates otherwise. Not the paper's packing.
        best=None
        if n<=12:
            choices=combinations(ids,half)
        else:
            choices=(tuple(ids[(i+j)%n] for j in range(half)) for i in range(min(n,12)))
        for subset in choices:
            if n%2==0 and n<=12 and ids[0] not in subset:continue
            left=tuple(sorted(subset))
            right=tuple(x for x in ids if x not in set(left))
            stats.partition_candidates+=1
            # Cut width, then max child boundary size, then stable IDs.
            bl=boundary(left);br=boundary(right)
            score=(len(set(bl)|set(br)),max(len(bl),len(br)),left)
            if best is None or score<best[0]:best=(score,left,right)
        assert best is not None
        return best[1],best[2]

    def go(ids:tuple[int,...],depth:int)->ChildTensor:
        check()
        stats.recursion_calls+=1
        stats.max_depth=max(stats.max_depth,depth)
        out_boundary=boundary(ids)
        nentries=tensor_size(out_boundary)
        if len(ids)==1:
            stats.leaf_tensors+=1
            t=tables[ids[0]]
            # A leaf's ports are its complete boundary unless no other
            # factor uses a port (then sum out that variable).
            result=[zero]*nentries
            pos={v:i for i,v in enumerate(t.ports)}
            for assignment,val in enumerate(t.values):
                check(1)
                projected=sum(1<<i for i,v in enumerate(out_boundary)
                              if assignment & (1<<pos[v]))
                result[projected]=tuple((a+b)&mask for a,b in zip(result[projected],val))
            return ChildTensor(ids,out_boundary,tuple(result))
        leftids,rightids=choose_split(ids)
        left=go(leftids,depth+1)
        right=go(rightids,depth+1)
        union=tuple(sorted(set(left.boundary)|set(right.boundary)))
        stats.max_join_variables=max(stats.max_join_variables,len(union))
        if len(union)>max_boundary_vars or (1<<len(union))>max_table_entries:
            raise ChildTensorLimit('join table budget exceeded')
        result=[[0]*jet_order for _ in range(nentries)]
        indices={v:i for i,v in enumerate(union)}
        lm=tuple(sum(1<<k for k,v in enumerate(left.boundary)
                     if assignment&(1<<indices[v])) for assignment in range(1<<len(union)))
        rm=tuple(sum(1<<k for k,v in enumerate(right.boundary)
                     if assignment&(1<<indices[v])) for assignment in range(1<<len(union)))
        om=tuple(sum(1<<k for k,v in enumerate(out_boundary)
                     if assignment&(1<<indices[v])) for assignment in range(1<<len(union)))
        for assignment in range(1<<len(union)):
            if (assignment&127)==0:check()
            check(1)
            v=_mul(left.values[lm[assignment]],right.values[rm[assignment]],
                   precision_bits,jet_order,stats)
            slot=result[om[assignment]]
            for k,x in enumerate(v):slot[k]=(slot[k]+x)&mask
        stats.internal_tensors+=1
        return ChildTensor(ids,out_boundary,tuple(tuple(x) for x in result))

    root=go(all_ids,0)
    if root.boundary or len(root.values)!=1:
        raise AssertionError('top-level child tensor has uncontracted variables')
    return root.values[0],modes,stats
