"""Small exact full-contraction oracle for the finite weighted-mode identity.

Reference enumerates both half-wire Boolean assignments. The weighted path
expands row factors in formal tile modes, drops terms of total 2-adic
weight >= precision, then substitutes their source-side column forms.
It checks a full network scalar, NOT the paper's recursive child tensors.
"""
from __future__ import annotations
from collections import defaultdict
from .constructor import cauchy_element, frac_mod
from .checker import verify_tile_modes
from veritas.research.eth_packing_v26.implicit import real_packet_slots


def network_edges(network):
    """Return D.3 endpoint pairs using zero-based row and column factor IDs."""
    rows=[f for f in network.factors if f.label.startswith('clause:')]
    cols=[f for f in network.factors if f.label.startswith('variable:')]
    if len(rows)+len(cols)!=len(network.factors):
        raise ValueError('reference requires clause/variable-labelled tensor factors')
    row_map={e:u for u,f in enumerate(rows) for e in f.ports}
    col_map={e:v for v,f in enumerate(cols) for e in f.ports}
    if set(row_map)!=set(range(network.edges)) or set(col_map)!=set(range(network.edges)):
        raise ValueError('network is not bipartite on row/column factor labels')
    return [[row_map[e],col_map[e]] for e in range(network.edges)]


def check_full_scalar_identity(network, certificate, *, max_edges=5, max_assignments=1024):
    checked=verify_tile_modes(certificate)
    if not checked['valid']:
        raise ValueError('mode certificate rejected: '+str(checked))
    m=network.edges;p=certificate['precision'];mod=1<<p
    if m>max_edges or (1<<(2*m))>max_assignments:
        raise ValueError('exact reference assignment cap exceeded')
    if certificate['d3_certificate']['edges']!=network_edges(network):
        raise ValueError('D.3 edge endpoints do not match source tensor network')
    L=1<<certificate['d3_certificate']['a'];T=certificate['evaluation_T']
    local=defaultdict(list)
    for r,c,frac in certificate['local_entries']:
        local[r].append((c,frac_mod(__import__('fractions').Fraction(*frac),p)))
    modes=certificate['modes'];weights=[z['weight'] for z in modes]
    by_row=defaultdict(list)
    for idx,mode in enumerate(modes):
        for row,coefficient in mode['row_coefficients']:
            by_row[row].append((idx,frac_mod(__import__('fractions').Fraction(*coefficient),p)))
    direct=0;expanded=0; terms=0
    zero=(0,)*len(modes)
    for xm in range(1<<m):
        xx={e:bool(xm>>e&1) for e in range(m)}
        col_product=1
        for f in network.factors:
            if f.label.startswith('variable:'):
                col_product=(col_product*f.value(xx))%mod
        if not col_product:continue
        Lx=[]
        for mode in modes:
            Lx.append(sum(j for e,j in mode['column_terms'] if xm>>e&1)%mod)
        for ym in range(1<<m):
            yy={e:bool(ym>>e&1) for e in range(m)}
            row_product=1
            for f in network.factors:
                if f.label.startswith('clause:'):
                    row_product=(row_product*f.value(yy))%mod
            if not row_product:continue
            # Direct, independently evaluated W via deleted-factor product.
            row_sums=[0]*m
            for packet in certificate['d3_certificate']['packets']:
                real=list(real_packet_slots(packet,L))
                for x,e in real:
                    for y,ce in real:
                        if xm>>ce&1:
                            row_sums[e]=(row_sums[e]+frac_mod(cauchy_element(L,T,x,y),p))%mod
            val=row_product*col_product
            for e,s in enumerate(row_sums):
                val=(val*(s if ym>>e&1 else (1-s)))%mod
            direct=(direct+val)%mod
            # Formal-mode expansion, with the weight cap imposed at EACH step.
            poly={zero:1}
            for e in range(m):
                s=sum(v for ce,v in local[e] if xm>>ce&1)%mod
                base=s if ym>>e&1 else (1-s)%mod
                sign=1 if ym>>e&1 else -1
                nxt=defaultdict(int)
                for beta,c in poly.items():
                    nxt[beta]=(nxt[beta]+c*base)%mod
                    for mid,coef in by_row[e]:
                        if sum(w*v for w,v in zip(weights,beta))+weights[mid]>=p:continue
                        b=list(beta);b[mid]+=1;b=tuple(b)
                        nxt[b]=(nxt[b]+c*sign*coef)%mod
                poly={b:c for b,c in nxt.items() if c}
            total=0
            for beta,coefficient in poly.items():
                value=coefficient
                for mid,exponent in enumerate(beta):
                    if exponent:
                        value=value*pow(Lx[mid],exponent,mod)%mod
                total=(total+value)%mod
            expanded=(expanded+total*row_product*col_product)%mod
            terms+=len(poly)
    if direct!=expanded:
        raise AssertionError(f'full finite D.4.4 scalar identity mismatch: {direct} != {expanded}')
    return {'status':'FINITE_DEFORMED_SCALAR_IDENTITY_VERIFIED',
            'direct_contraction_mod_2p':direct,'mode_contraction_mod_2p':expanded,
            'edge_count':m,'precision':p,'expanded_monomial_instances':terms,
            'manuscript_recursive_child_network':False}
