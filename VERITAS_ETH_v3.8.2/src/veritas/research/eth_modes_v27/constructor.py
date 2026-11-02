"""Exact finite D.4.4 column-tile geometric mode reference.

Input is the *validated* D.3 certificate. For one nonzero interpolation
node t, integer zeta and precision p, factor cross-group Cauchy entries
as row coefficient times the j**b tile-column form, weight b+1.

This performs scalar-integer evaluations of t+2**(a+1)*zeta, NOT
full extension-ring Taylor jets or child-tensor recursion. Fail closed.
"""
from __future__ import annotations
from fractions import Fraction
from collections import defaultdict, Counter
from .enumeration import count_tuples, ModeBudgetExceeded
from veritas.research.eth_packing_v26.checker import verify_d3_packing
from veritas.research.eth_packing_v26.implicit import real_packet_slots


def v2(n):
    if not n:
        return 10**9
    n=abs(n)
    return (n & -n).bit_length()-1


def v2_fraction(x):
    x=Fraction(x)
    return v2(x.numerator)-v2(x.denominator) if x else 10**9


def encoded(x):
    x=Fraction(x)
    return [x.numerator,x.denominator]


def frac_mod(x,p):
    x=Fraction(x)
    d=x.denominator
    if d%2==0:
        raise ValueError('nonintegral 2-adic rational encountered')
    return (x.numerator * pow(d,-1,1<<p)) % (1<<p)


def cauchy_element(L,T,x,y):
    s=range(-L,L)
    q=y-x
    deriv=1
    for k in s:
        if k: deriv *= -k
    result=Fraction(1,deriv)
    for k in s:
        if k != q:
            result *= T-k
    return result


def construct_tile_modes(d3_certificate, *, node=1, zeta=1, precision=6,
                         max_modes=8000,max_tuple_count=100_000):
    status=verify_d3_packing(d3_certificate, check_trace=True)
    if not status['valid']:
        raise ValueError('invalid D.3 packing certificate: '+status.get('reason',''))
    a=d3_certificate['a'];L=1<<a
    if type(node) is not int or not (-L<=node<L) or node==0 or v2(node)>=a:
        raise ValueError('node must be nonzero with valuation less than a')
    if type(zeta) is not int or not 0<=zeta<=8:
        raise ValueError('bounded nonnegative integer zeta required')
    if type(precision) is not int or not 2<=precision<=24:
        raise ValueError('precision must be 2..24')
    if type(max_modes) is not int or not 1<=max_modes<=20000:
        raise ValueError('invalid mode count limit')
    i=v2(node);tile_width=1<<(i+1)
    T=node+(1<<(a+1))*zeta
    row_labels=d3_certificate['row_labels']; col_labels=d3_certificate['column_labels']
    edges=d3_certificate['edges']
    modes=[];local=[];cross_pairs=[]
    for pid,packet in enumerate(d3_certificate['packets']):
        real=list(real_packet_slots(packet,L))
        if not real: continue
        by_tile=defaultdict(list)
        for y,eid in real:
            by_tile[y%tile_width].append((y,eid,(y-y%tile_width)//tile_width))
        for x,row_edge in real:
            u=edges[row_edge][0]
            row_group=row_labels[str(u)][i]
            for y,col_edge in real:
                v=edges[col_edge][1]
                col_group=col_labels[str(v)][i]
                if row_group==col_group:
                    w=cauchy_element(L,T,x,y)
                    if w:
                        local.append([row_edge,col_edge,encoded(w)])
                else:
                    cross_pairs.append([row_edge,col_edge])
        for y0,cols in sorted(by_tile.items()):
            src_groups={col_labels[str(edges[eid][1])][i] for _,eid,_ in cols}
            if len(src_groups)!=1:
                raise AssertionError('tile source group inconsistent with D.3 alignment')
            source=next(iter(src_groups))
            target_groups={row_labels[str(edges[eid][0])][i] for _,eid in real}
            for target in sorted(target_groups-{source}):
                targets=[(x,eid) for x,eid in real if row_labels[str(edges[eid][0])][i]==target]
                if not targets: continue
                for b in range(precision-1):
                    row_coefs=[]
                    for x,eid in targets:
                        den=Fraction(T-y0+x)
                        if not den:
                            raise AssertionError('cross denominator zero')
                        deriv=Fraction(1)
                        for k in range(-L,L):
                            if k: deriv *= -k
                        C=1
                        for k in range(-L,L): C*=T-k
                        A=Fraction(C,1)/(deriv*den)
                        coef=A*(Fraction(tile_width,1)/den)**b
                        if coef:
                            if v2_fraction(coef)<b+1:
                                raise AssertionError('D.4.4 coefficient valuation bound failed')
                            row_coefs.append([eid,encoded(coef)])
                    col_terms=[[eid,j**b] for y,eid,j in cols if (j**b)!=0]
                    if row_coefs and col_terms:
                        if len(modes)>=max_modes:
                            raise ModeBudgetExceeded('mode construction cap exceeded')
                        modes.append({'packet':pid,'tile_residue':y0,'weight':b+1,
                            'source_group':source,'target_group':target,
                            'row_coefficients':row_coefs,'column_terms':col_terms})
    weights=[m['weight'] for m in modes]
    count=count_tuples(weights,precision,cap=max_tuple_count)
    certificate={
        'schema':'VERITAS_ETH_D44_FINITE_MODE_V1',
        'claim':'FINITE_SCALAR_D44_TILE_MODES_ONLY',
        'd3_certificate':d3_certificate,
        'node':node,'zeta':zeta,'precision':precision,
        'tile_width':tile_width,'evaluation_T':T,
        'local_entries':local,'cross_pairs':cross_pairs,'modes':modes,
        'mode_tuple_count':count,
        'scope':{'extension_ring_taylor_jets':False,
                 'implicit_recursive_child_tensors':False,
                 'subexponential_runtime_proven':False,
                 'packet_numeric_preconditions':bool(status['d6_numeric_preconditions_satisfied'])}
    }
    return certificate
