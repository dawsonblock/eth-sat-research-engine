"""Independent finite D.4.4 checker.

Does NOT trust reported matrix entries, mode coefficients, membership,
valuation, tuple counts, or the embedded D.3 certificate.
"""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
from veritas.research.eth_packing_v26.checker import verify_d3_packing
from .enumeration import count_tuples


def _v2(n):
    if n==0: return 10**9
    n=abs(n)
    return (n & -n).bit_length()-1


def _decode(pair):
    if not isinstance(pair,list) or len(pair)!=2 or any(type(v) is not int for v in pair) or pair[1]<=0:
        raise ValueError('invalid exact rational encoding')
    return Fraction(pair[0],pair[1])


def _mod(value,p):
    if value.denominator%2==0:
        raise ValueError('nonintegral 2-adic coefficient')
    modulus=1<<p
    return (value.numerator * pow(value.denominator,-1,modulus))%modulus


def verify_tile_modes(cert, *, max_work=2_000_000):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!='VERITAS_ETH_D44_FINITE_MODE_V1':
            raise ValueError('unknown finite D.4.4 certificate schema')
        base=cert['d3_certificate']
        d3=verify_d3_packing(base,check_trace=True)
        if not d3['valid']:raise ValueError('embedded D.3 certificate invalid')
        a=base['a'];L=1<<a;p=cert['precision'];t=cert['node'];z=cert['zeta']
        if any(type(v) is not int for v in (p,t,z)) or not 2<=p<=24 or not(-L<=t<L) or not t or not 0<=z<=8:
            raise ValueError('invalid node/precision')
        i=_v2(t)
        if i>=a:raise ValueError('node valuation outside active coordinates')
        width=1<<(i+1);T=t+(1<<(a+1))*z
        if cert['tile_width']!=width or cert['evaluation_T']!=T:
            raise ValueError('forged interpolation metadata')
        if cert.get('claim')!='FINITE_SCALAR_D44_TILE_MODES_ONLY' or cert.get('scope')!={
            'extension_ring_taylor_jets':False,
            'implicit_recursive_child_tensors':False,
            'subexponential_runtime_proven':False,
            'packet_numeric_preconditions':bool(d3['d6_numeric_preconditions_satisfied'])}:
            raise ValueError('invalid scope claim')
        total_edges=base['M'];packs=base['packets'];edges=base['edges']
        if len(packs)>10000 or total_edges>4000 or len(cert['modes'])>20000:
            raise ValueError('resource limits exceeded')
        # Compute each Cauchy W directly via deleted factor polynomial.
        deriv=1
        for q in range(-L,L):
            if q:deriv *= -q
        direct={};local_expected=set();cross_expected=set()
        for pid,pack in enumerate(packs):
            real=[(slot,eid) for slot,eid in enumerate(pack['slots']) if eid is not None]
            for x,rid in real:
                rg=base['row_labels'][str(edges[rid][0])][i]
                for y,cid in real:
                    cg=base['column_labels'][str(edges[cid][1])][i]
                    numerator=1
                    for q in range(-L,L):
                        if q!=y-x:numerator*=T-q
                    exact=Fraction(numerator,deriv)
                    direct[(rid,cid)]=_mod(exact,p)
                    if rg==cg:
                        if exact:local_expected.add((rid,cid,exact))
                    else:cross_expected.add((rid,cid))
        # No implicit default values accepted for omitted local cells.
        seen=set()
        for rid,cid,frac in cert['local_entries']:
            exact=_decode(frac)
            if (rid,cid,exact) not in local_expected or (rid,cid) in seen:
                raise ValueError('wrong/duplicate local Cauchy entry')
            seen.add((rid,cid))
        if seen!={(r,c) for r,c,_ in local_expected}:
            raise ValueError('missing local entries')
        if {tuple(pair) for pair in cert['cross_pairs']}!=cross_expected or len(cert['cross_pairs'])!=len(cross_expected):
            raise ValueError('incorrect cross-group incidence set')
        reconstructed=defaultdict(int)
        # modes are indexed per packet/residue/weight and required to be unique
        seen_modes=set()
        counts=defaultdict(int)
        for mode in cert['modes']:
            pid=mode['packet'];y0=mode['tile_residue'];w=mode['weight']
            if any(type(v) is not int for v in (pid,y0,w)) or not 0<=pid<len(packs) or not 0<=y0<width or not 1<=w<p:
                raise ValueError('invalid tile/mode metadata')
            key=(pid,y0,w,mode['source_group'],mode['target_group'])
            if key in seen_modes:raise ValueError('duplicate mode')
            seen_modes.add(key)
            real=[(slot,eid) for slot,eid in enumerate(packs[pid]['slots']) if eid is not None]
            columns={eid:((y-y0)//width)**(w-1) for y,eid in real if y%width==y0}
            source_groups={base['column_labels'][str(edges[eid][1])][i] for eid in columns}
            if source_groups!={mode['source_group']} or mode['source_group']==mode['target_group']:
                raise ValueError('wrong mode source/target')
            expected_cols={(eid,j) for eid,j in columns.items() if j!=0}
            supplied_cols={(eid,j) for eid,j in mode['column_terms']}
            if len(supplied_cols)!=len(mode['column_terms']) or expected_cols!=supplied_cols:
                raise ValueError('forged tile column powers')
            expected_rows={}
            for x,rid in real:
                if base['row_labels'][str(edges[rid][0])][i]!=mode['target_group']:
                    continue
                denominator=T-y0+x
                if denominator==0:raise ValueError('cross denominator singular')
                C=1
                for q in range(-L,L):C*=T-q
                coefficient=Fraction(C,deriv*denominator)*Fraction(width,denominator)**(w-1)
                if coefficient:
                    expected_rows[rid]=coefficient
            given_rows={}
            for rid,representation in mode['row_coefficients']:
                if rid in given_rows:raise ValueError('duplicate row coefficient')
                given_rows[rid]=_decode(representation)
            if not expected_rows or not expected_cols or given_rows!=expected_rows:
                raise ValueError('row coefficient does not match geometric expansion')
            for rid,c in given_rows.items():
                if _v2(c.numerator)-_v2(c.denominator)<w:
                    raise ValueError('mode 2-adic valuation below declared weight')
                for eid,j in expected_cols:
                    reconstructed[(rid,eid)]+= _mod(c*j,p)
            counts[w]+=1
        # Stronger than merely matching the scalar result: every matrix entry.
        for key in cross_expected:
            if reconstructed[key] % (1<<p)!=direct[key]:
                raise ValueError('cross-group Cauchy reconstruction mismatch')
        max_allowed_per_weight=(6*total_edges // (L//(1<<i))) if total_edges else 0
        # The manuscript bound is a numerical *conditional* bound, not mandatory
        # at scaled parameters lacking its D.3 hypotheses.
        count=count_tuples([m['weight'] for m in cert['modes']],p,cap=1_000_000)
        if cert['mode_tuple_count']!=count:
            raise ValueError('incorrect weighted tuple count')
        if max_work < (len(cross_expected)+len(cert['modes']))*p:
            raise ValueError('explicit verification budget exceeded')
        return {'valid':True,'status':'FINITE_D44_SCALAR_MODE_IDENTITY_VERIFIED',
                'modes':len(cert['modes']),'cross_entries':len(cross_expected),
                'tuple_count':count,'mode_multiplicity':dict(counts),
                'manuscript_multiplicity_bound':max_allowed_per_weight,
                'multiplicity_bound_satisfied':all(c<=max_allowed_per_weight for c in counts.values()),
                'manuscript_preconditions_satisfied':bool(d3['d6_numeric_preconditions_satisfied']),
                'full_recursion_verified':False,'subexponential_claim':False}
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,ZeroDivisionError) as exc:
        return {'valid':False,'status':'INVALID_MODE_CERTIFICATE','reason':str(exc)}
