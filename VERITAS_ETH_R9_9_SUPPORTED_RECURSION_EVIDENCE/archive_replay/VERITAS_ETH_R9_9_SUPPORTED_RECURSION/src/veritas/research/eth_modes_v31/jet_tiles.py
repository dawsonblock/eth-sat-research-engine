"""Finite geometric-tile D.4.4 *reference* over truncated 2-adic extension jets.

A Cauchy cross-group entry W[x,y](t+2L V), with y=y0+j*B, equals
  sum_{b >= 0} A[x,y0,b](V) * j**b,
  A = W[x,y0](t+2L V) * (B/(t+2L V-y0+x))**b.

The discarded tail has valuation >=p only when every mode coefficient's
minimum valuation is at least its certified weight. This implementation
*measures* valuations of every coefficient, and uses them as weights; it
never assumes a divisibility bound where it was not checked. A group-wise
exact scalar contraction factors the mode-polynomial coefficient into
independent symbol groups. Children here are brute-force finite scalar
oracles, NOT the recursive child networks of the manuscript's theorem.
"""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction
from itertools import product
from math import comb
from time import monotonic

from veritas.research.eth_packing_v26.checker import verify_d3_packing
from veritas.research.eth_packing_v26.implicit import (check_implicit_mode_source,
                                                       real_packet_slots)
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_interpolation.shifted_cauchy import (
    shift_cauchy_entry, shifted_fraction_coefficients, fraction_to_ring)
from veritas.research.eth_packing.cauchy import cauchy_matrix_polynomials
from veritas.research.eth_modes_v27.enumeration import weighted_tuples, count_tuples
from veritas.research.eth_recursion_v30.implicit_children import (
    make_bipartite_edges, _check_inputs, _direct_oracle, Limits)
from veritas.research.tensor import TensorNetwork, Factor

SCOPE = {'geometric_tile_extension_jets':True,
         'mode_indexed_finite_children':True,
         'manuscript_recursive_child_networks':False,
         'subexponential_runtime_proven':False}


def _v2(n):
    if not n: raise ValueError('node must be nonzero')
    n=abs(n)
    return (n & -n).bit_length()-1


def _coefficients(L, node, x, y0, b, length):
    """Rational formal series, reduced to integral 2-adic coefficients later.

    Calculate W[x,y0](t+2L V) times (B/(d+2L V))**b.
    We never invert an even integer in the finite ring.
    """
    a=L.bit_length()-1
    scale=2*L
    B=1<<(_v2(node)+1)
    d=node-y0+x
    if d == 0: raise ValueError('cross-group singular expansion: d=0')
    raw=cauchy_matrix_polynomials(L)[x][y0]
    w=shifted_fraction_coefficients(raw,node,scale)
    out=[]
    for k in range(length):
        value=Fraction()
        for j in range(min(k,len(w)-1)+1):
            rem=k-j
            if b==0:
                if rem:continue
                inv=Fraction(1)
            else:
                inv=Fraction(B**b, d**b) * (-1)**rem * comb(b+rem-1,rem) * Fraction(scale,d)**rem
            value+=w[j]*inv
        out.append(value)
    return out


def _validate(d3,node,p,e,length,_budget=None):
    if _budget is not None: _budget.tick()
    if not isinstance(d3,dict):
        raise ValueError('invalid D.3 packet source')
    schema=d3.get('schema')
    if schema in ('VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1',
                  'VERITAS_ETH_D3_IMPLICIT_SPARSE_ACTIVE_V1'):
        source_check=check_implicit_mode_source(d3)
    else:
        source_check=verify_d3_packing(d3,check_trace=True,_budget=_budget)
    if not source_check['valid']:
        raise ValueError('invalid D.3 packet certificate')
    if any(type(x) is not int for x in (node,p,e,length)):
        raise ValueError('integer parameters required')
    L=d3['L']
    if not (1<=d3['M']<=6 and L in (2,4) and d3['r']<=4):
        raise ValueError('bounded reference supports 1..6 wires, packets L=2/4, r<=4')
    if schema in ('VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1',
                  'VERITAS_ETH_D3_IMPLICIT_SPARSE_ACTIVE_V1') and len(d3['packets'])>d3['M']:
        raise ValueError('active packet view exceeds the edge-count bound')
    if not (2<=p<=10 and 1<=e<=8 and 1<=length<=min(4,2*L)):
        raise ValueError('finite precision/extension/jet length budget exceeded')
    if not(-L<=node<L and node!=0 and _v2(node)<d3['a']):
        raise ValueError('invalid active interpolation node')


def make_jet_tile_modes(d3,*,node=1,precision=5,extension_degree=3,
                        jet_length=2,max_modes=240,max_tuples=6000,_budget=None):
    _validate(d3,node,precision,extension_degree,jet_length,_budget)
    L=d3['L'];i=_v2(node);B=1<<(i+1)
    ring=ExtensionRing(precision,first_irreducible(extension_degree))
    mode=[];local=[];cross=[];ignored=0
    for pid,packet in enumerate(d3['packets']):
        if _budget is not None: _budget.tick()
        real=list(real_packet_slots(packet,L))
        if not real: continue
        tiles=defaultdict(list)
        for y,cid in real:
            y0=y % B;j=(y-y0)//B
            tiles[y0].append((cid,j))
        for x,rid in real:
            rg=d3['row_labels'][str(d3['edges'][rid][0])][i]
            for y,cid in real:
                if _budget is not None: _budget.tick()
                cg=d3['column_labels'][str(d3['edges'][cid][1])][i]
                if rg==cg:
                    jet=shift_cauchy_entry(L,node,ring,x,y)[:jet_length]
                    if any(c!=ring.zero for c in jet):
                        local.append([rid,cid,[list(c) for c in jet]])
                else:cross.append([rid,cid])
        for y0,cols in sorted(tiles.items()):
            sources={d3['column_labels'][str(d3['edges'][cid][1])][i] for cid,j in cols}
            if len(sources)!=1:raise ArithmeticError('mixed source labels within a tile')
            src=next(iter(sources))
            for target in range(d3['r']):
                if target==src:continue
                targets=[(x,rid) for x,rid in real if d3['row_labels'][str(d3['edges'][rid][0])][i]==target]
                if not targets:continue
                # Each omitted b>=precision mode is certified via the
                # coefficient-valuation bound, checked for every kept b.
                for b in range(precision):
                    if _budget is not None: _budget.tick()
                    rows=[];weights=[]
                    for x,rid in targets:
                        if _budget is not None: _budget.tick()
                        coeffs=_coefficients(L,node,x,y0,b,jet_length)
                        jet=tuple(fraction_to_ring(ring,v) for v in coeffs)
                        weight=min(ring.valuation(c) for c in jet)
                        if weight<precision:
                            rows.append([rid,[list(c) for c in jet]])
                            weights.append(weight)
                    if not rows:
                        ignored+=1
                        continue
                    weight=min(weights)
                    if weight < b+1:
                        raise ArithmeticError('geometric mode does not meet required 2-adic divisibility')
                    column_terms=[[cid,j**b] for cid,j in cols if j**b]
                    if not column_terms:continue
                    if len(mode)>=max_modes:raise ValueError('mode budget exhausted')
                    mode.append({'packet':pid,'tile_residue':y0,'exponent':b,
                       'weight':weight,'source_group':src,'target_group':target,
                       'rows':rows,'column_terms':column_terms})
    weights=[m['weight'] for m in mode]
    total=count_tuples(weights,precision,cap=max_tuples)
    return {'schema':'VERITAS_ETH_GEOMETRIC_JET_MODES_V31',
            'claim':'FINITE_EXACT_GEOMETRIC_JET_MODES_ONLY',
            'd3_certificate':d3,'node':node,'precision':precision,
            'extension_degree':extension_degree,'jet_length':jet_length,
            'irreducible_polynomial':ring.f,'local':local,'cross_pairs':sorted(cross),
            'modes':mode,'fully_vanishing_modes':ignored,'mode_tuple_count':total,
            'scope':dict(SCOPE)}


def check_jet_tile_modes(cert, *, _budget=None):
    """Reconstruct all Cauchy jets and check identities independently of claimed result."""
    try:
        if not isinstance(cert,dict) or cert.get('schema')!='VERITAS_ETH_GEOMETRIC_JET_MODES_V31' or cert.get('claim')!='FINITE_EXACT_GEOMETRIC_JET_MODES_ONLY' or cert.get('scope')!=SCOPE:
            raise ValueError('unsupported certificate schema/scope')
        d3=cert['d3_certificate'];t=cert['node'];p=cert['precision'];e=cert['extension_degree'];n=cert['jet_length']
        _validate(d3,t,p,e,n,_budget)
        ring=ExtensionRing(p,first_irreducible(e));L=d3['L'];i=_v2(t)
        if cert['irreducible_polynomial']!=ring.f:raise ValueError('extension polynomial mismatch')
        ref={}
        groups={}
        for packet in d3['packets']:
            if _budget is not None: _budget.tick()
            real=list(real_packet_slots(packet,L))
            for x,rid in real:
                rg=d3['row_labels'][str(d3['edges'][rid][0])][i]
                for y,cid in real:
                    if _budget is not None: _budget.tick()
                    ref[rid,cid]=shift_cauchy_entry(L,t,ring,x,y)[:n]
                    groups[rid,cid]=(rg,d3['column_labels'][str(d3['edges'][cid][1])][i])
        local={}
        for rid,cid,coefs in cert['local']:
            if _budget is not None: _budget.tick()
            key=(rid,cid)
            if key in local or key not in ref or groups[key][0]!=groups[key][1]:raise ValueError('invalid local pair')
            local[key]=tuple(tuple(v) for v in coefs)
        if local!={k:v for k,v in ref.items() if groups[k][0]==groups[k][1] and any(c!=ring.zero for c in v)}:
            raise ValueError('local jet mismatch')
        crosses={k for k in ref if groups[k][0]!=groups[k][1]}
        if cert['cross_pairs']!=[list(k) for k in sorted(crosses)]:raise ValueError('cross-pair mismatch')
        reconstructed={k:[ring.zero for _ in range(n)] for k in crosses}
        for m in cert['modes']:
            if _budget is not None: _budget.tick()
            pid=m['packet'];b=m['exponent'];w=m['weight'];src=m['source_group'];dst=m['target_group']
            if any(type(v) is not int for v in (pid,b,w,src,dst)) or not 0<=pid<len(d3['packets']) or not 0<=b<p or not b+1<=w<p or not 0<=src<d3['r'] or not 0<=dst<d3['r'] or src==dst:
                raise ValueError('invalid mode label or valuation')
            B=1<<(i+1);y0=m['tile_residue']
            if type(y0) is not int or not 0<=y0<B:raise ValueError('invalid tile residue')
            real={eid:slot for slot,eid in real_packet_slots(d3['packets'][pid],L)}
            cols=[[cid, ((slot-y0)//B)**b] for cid,slot in sorted(real.items(),key=lambda kv:kv[1]) if slot%B==y0 and ((slot-y0)//B)**b and d3['column_labels'][str(d3['edges'][cid][1])][i]==src]
            if cols!=m['column_terms'] or not cols:raise ValueError('column-tile identity mismatch')
            if not isinstance(m['rows'],list) or not m['rows']:raise ValueError('empty mode rows')
            seen=set(); actual=[]
            for rid,encoded in m['rows']:
                if _budget is not None: _budget.tick()
                if rid in seen or rid not in real or d3['row_labels'][str(d3['edges'][rid][0])][i]!=dst or len(encoded)!=n:
                    raise ValueError('invalid target row')
                seen.add(rid)
                coeffs=tuple(tuple(c) for c in encoded)
                if any(len(c)!=e or any(type(x) is not int or not 0<=x<ring.modulus for x in c) for c in coeffs):
                    raise ValueError('invalid coefficient representation')
                expected=tuple(fraction_to_ring(ring,v) for v in _coefficients(L,t,real[rid],y0,b,n))
                if expected!=coeffs:raise ValueError('geometric coefficient mismatch')
                actual.extend(ring.valuation(c) for c in coeffs)
                for cid,jpower in cols:
                    key=rid,cid
                    if key not in crosses:raise ValueError('mode touches local/nonexistent pair')
                    for k,c in enumerate(coeffs):
                        reconstructed[key][k]=ring.add(reconstructed[key][k],ring.mul(c,ring.elem([jpower])))
            if min(actual)!=w:raise ValueError('valuation mismatch')
        if any(tuple(reconstructed[k])!=ref[k] for k in crosses):raise ValueError('cross Cauchy matrix jets not reconstructed')
        # Canonical certificate recomputation also rejects missing, duplicated,
        # unneeded or otherwise bogus zero-net-effect mode descriptions.
        computed=make_jet_tile_modes(d3,node=t,precision=p,extension_degree=e,jet_length=n,
                                     max_modes=240,max_tuples=6000,_budget=_budget)
        if computed!=cert:raise ValueError('certificate differs from canonical construction')
        return {'valid':True,'status':'FINITE_GEOMETRIC_EXTENSION_JETS_VERIFIED',
                'mode_count':len(cert['modes']),'mode_tuple_count':cert['mode_tuple_count'],
                'subexponential_runtime_proven':False}
    except (ValueError,TypeError,IndexError,KeyError,OverflowError,ArithmeticError,ZeroDivisionError) as exc:
        return {'valid':False,'status':'INVALID_GEOMETRIC_JET_CERTIFICATE','reason':str(exc)}


def _serialize_net(net):
    return {'edges':net.edges,'factors':[{'ports':list(f.ports),'table':list(f.table),'label':f.label} for f in net.factors]}


def _deserialize_net(obj):
    return TensorNetwork(obj['edges'],tuple(Factor(tuple(f['ports']),tuple(f['table']),f['label']) for f in obj['factors']))


def contract_mode_children(net:TensorNetwork,mode_cert:dict,*,max_work=150_000,timeout_s=12):
    """Mode-indexed group-local scalar children, compared against a direct oracle.

    This is an exact *finite expansion* and deliberately does not construct the
    recursively shrinking D.4.4 packet tensor networks.
    """
    verdict=check_jet_tile_modes(mode_cert)
    if not verdict['valid']:raise ValueError('invalid geometric jet modes: '+verdict['reason'])
    d3=mode_cert['d3_certificate'];t=mode_cert['node'];p=mode_cert['precision'];e=mode_cert['extension_degree'];n=mode_cert['jet_length']
    if d3.get('schema')=='VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1':
        if net.edges < 1 or net.edges > 6 or len(net.factors)>20:
            raise ValueError('finite independent oracle supports 1..6 edges and <=20 factors')
        if make_bipartite_edges(net)!=d3['edges']:
            raise ValueError('network endpoints do not match implicit D.3 source')
    else:
        _check_inputs(net,d3,t,p,e,n)
    if make_bipartite_edges(net)!=d3['edges']:raise ValueError('network endpoints do not match D.3 certificate')
    ring=ExtensionRing(p,first_irreducible(e));jr=JetRing(ring,n);m=net.edges;i=_v2(t)
    modes=mode_cert['modes'];K=len(modes)
    weights=[z['weight'] for z in modes]
    count=count_tuples(weights,p,cap=3000)
    if count>3000 or (1<<(2*m))*max(1,count)>max_work:
        raise ValueError('bounded mode-child evaluation work budget exceeded')
    rowgroups=[d3['row_labels'][str(u)][i] for u,v in d3['edges']]
    colgroups=[d3['column_labels'][str(v)][i] for u,v in d3['edges']]
    local=defaultdict(list)
    for rid,cid,c in mode_cert['local']:
        local[rid].append((cid,jr.elem(c)))
    row_modes=defaultdict(list)
    for mid,mode in enumerate(modes):
        for rid,c in mode['rows']:
            row_modes[rid].append((mid,jr.elem(c)))
    groups=sorted(set(rowgroups+colgroups+[d3['row_labels'].get(f.label.split(':',1)[1],[0])[i] if f.label.startswith(('clause:','row:')) else d3['column_labels'].get(f.label.split(':',1)[1],[0])[i] for f in net.factors]))
    zeros=(0,)*K
    start=monotonic()
    entries={};checks=0
    for group in groups:
        owned=tuple([rid for rid in range(m) if rowgroups[rid]==group]+[m+cid for cid in range(m) if colgroups[cid]==group])
        factors=[f for f in net.factors if (d3['row_labels'].get(f.label.split(':',1)[1],[0]*d3['a'])[i] if f.label.startswith(('row:','clause:')) else d3['column_labels'].get(f.label.split(':',1)[1],[0]*d3['a'])[i])==group]
        rows=[rid for rid in range(m) if rowgroups[rid]==group]
        states=[]
        for bits in product((0,1),repeat=len(owned)):
            if monotonic()-start>timeout_s:raise TimeoutError('bounded scalar child timeout')
            assignment=dict(zip(owned,bits));checks+=1
            factorprod=1
            for f in factors:
                offsets=tuple(port if f.label.startswith(('row:','clause:')) else m+port for port in f.ports)
                mask=sum(assignment[p]<<j for j,p in enumerate(offsets))
                factorprod*=f.table[mask]
            if not factorprod:continue
            poly={zeros:jr.elem([[factorprod]])}
            for rid in rows:
                s=jr.zero
                for cid,c in local[rid]:
                    if assignment[m+cid]:s=jr.add(s,c)
                is_one=assignment[rid]
                base=s if is_one else jr.sub(jr.one,s)
                sign=1 if is_one else -1
                nxt={}
                for beta,val in poly.items():
                    old=nxt.get(beta,jr.zero)
                    nxt[beta]=jr.add(old,jr.mul(val,base))
                    for mid,c in row_modes[rid]:
                        b=list(beta);b[mid]+=1;b=tuple(b)
                        if sum(v*w for v,w in zip(b,weights))>=p:continue
                        coeff=c if sign==1 else jr.neg(c)
                        nxt[b]=jr.add(nxt.get(b,jr.zero),jr.mul(val,coeff))
                poly={beta:v for beta,v in nxt.items() if v!=jr.zero}
            # Source linear forms depend only on this group's column halfbits.
            Lx={mid:sum(int(coeff)*assignment[m+cid] for cid,coeff in mode['column_terms']) for mid,mode in enumerate(modes) if mode['source_group']==group}
            states.append((poly,Lx))
        entries[group]=(owned,states)
    total=jr.zero
    child_caches={g:{} for g in groups}
    for beta in weighted_tuples(weights,p,max_tuples=3000):
        prod=jr.one
        for g in groups:
            # Each child only sees exponents of modes incident on that symbol group.
            key=tuple((idx,beta[idx]) for idx,mode in enumerate(modes) if beta[idx] and (mode['target_group']==g or mode['source_group']==g))
            cache=child_caches[g]
            if key in cache:
                val=cache[key]
            else:
                target_beta=tuple(beta[idx] if mode['target_group']==g else 0 for idx,mode in enumerate(modes))
                val=jr.zero
                for poly,Lx in entries[g][1]:
                    c=poly.get(target_beta,jr.zero)
                    if c==jr.zero:continue
                    for mid,xval in Lx.items():
                        if beta[mid] and xval:
                            c=jr.mul(c,jr.elem([[pow(xval,beta[mid])]]))
                        elif beta[mid]:
                            c=jr.zero;break
                    val=jr.add(val,c)
                    checks+=1
                    if checks>max_work or monotonic()-start>timeout_s:raise TimeoutError('finite child work budget exceeded')
                cache[key]=val
            prod=jr.mul(prod,val)
            if prod==jr.zero:break
        total=jr.add(total,prod)
    oracle_budget=Limits(max_assignments=min(max_work,2_000_000),timeout_s=min(20,timeout_s))
    oracle=_direct_oracle(net,d3,t,jr,oracle_budget)
    if oracle!=total:
        raise ArithmeticError('independent full half-edge Cauchy contraction disagrees with factorized mode children')
    return {'schema':'VERITAS_ETH_MODE_CHILD_SCALAR_V31',
            'claim':'FINITE_MODE_INDEXED_SCALAR_CHILDREN_ONLY',
            'network':_serialize_net(net),'mode_certificate':mode_cert,
            'result':[[int(c) for c in x] for x in total],
            'children':[{'group':g,'owned_halfbits':list(entries[g][0]),
              'assignments_evaluated':len(entries[g][1]),'cache_size':len(child_caches[g])} for g in groups],
            'mode_tuple_count':count,'direct_oracle_matches':True,
            'scope':dict(SCOPE)}


def check_mode_child_certificate(cert,*,max_work=150_000,timeout_s=12):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!='VERITAS_ETH_MODE_CHILD_SCALAR_V31' or cert.get('claim')!='FINITE_MODE_INDEXED_SCALAR_CHILDREN_ONLY' or cert.get('scope')!=SCOPE:
            raise ValueError('invalid certificate scope')
        net=_deserialize_net(cert['network'])
        recalculated=contract_mode_children(net,cert['mode_certificate'],max_work=max_work,timeout_s=timeout_s)
        if cert!=recalculated:raise ValueError('certificate replay mismatch')
        return {'valid':True,'status':'FINITE_MODE_CHILD_SCALAR_IDENTITY_VERIFIED',
                'mode_tuple_count':cert['mode_tuple_count'],'subexponential_runtime_proven':False}
    except (ValueError,TypeError,IndexError,KeyError,OverflowError,ArithmeticError,ZeroDivisionError,TimeoutError) as exc:
        return {'valid':False,'status':'INVALID_MODE_CHILD_CERTIFICATE','reason':str(exc)}
