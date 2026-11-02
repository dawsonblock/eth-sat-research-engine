"""Exact *finite* extension-ring coefficient-jet decomposition of cross-group W.

This is a genuine ring-valued decomposition: cross-group columns are grouped
when their row-jet signatures coincide, yielding rank-one components over
R_p[V]/V^k. Every coefficient carries an independently checkable 2-adic
valuation. Modes whose *entire* coefficient vector vanishes mod 2**p are
omitted. It is NOT the manuscript's geometric-tile low-weight enumerator,
and makes NO mode-count or subexponential runtime claim.
"""
from __future__ import annotations
from collections import defaultdict
from veritas.research.eth_packing_v26.checker import verify_d3_packing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_packing_v26.implicit import real_packet_slots


def _check_base(base):
    result=verify_d3_packing(base,check_trace=True)
    if not result['valid']:
        raise ValueError('D3 certificate rejected: '+result.get('reason','invalid'))
    if base['M']>32 or base['L']>8:
        raise ValueError('finite mode reference budget exceeded')
    return result


def _val2(n):
    if n==0:raise ValueError('zero node')
    n=abs(n)
    return (n&-n).bit_length()-1


def _raw_coeffs(base,ring,node,length):
    L=base['L'];i=_val2(node)
    if i>=base['a'] or not -L<=node<L:
        raise ValueError('unsupported interpolation node')
    cache={}
    for pid,packet in enumerate(base['packets']):
        real=list(real_packet_slots(packet,base['L']))
        for x,rid in real:
            for y,cid in real:
                cache[(rid,cid)]=shift_cauchy_entry(L,node,ring,x,y)[:length]
    return cache


def make_extension_modes(d3_certificate,*,node=1,precision=8,extension_degree=4,jet_length=3):
    _check_base(d3_certificate)
    if any(type(x) is not int for x in (node,precision,extension_degree,jet_length)):
        raise ValueError('all parameters must be integers')
    if not 2<=precision<=64 or not 1<=extension_degree<=8 or not 1<=jet_length<=16:
        raise ValueError('finite extension mode budget exceeded')
    L=d3_certificate['L']
    if jet_length>2*L:
        raise ValueError('jet length exceeds Cauchy polynomial degree+1')
    ring=ExtensionRing(precision,first_irreducible(extension_degree))
    base=d3_certificate;raw=_raw_coeffs(base,ring,node,jet_length)
    i=_val2(node)
    local=[];modes=[];cross_keys=set();pruned=0
    for pid,packet in enumerate(base['packets']):
        real=list(real_packet_slots(packet,base['L']))
        # Local contributions are not factorized.
        for x,rid in real:
            row_group=base['row_labels'][str(base['edges'][rid][0])][i]
            for y,cid in real:
                col_group=base['column_labels'][str(base['edges'][cid][1])][i]
                if row_group==col_group:
                    if any(any(c) for c in raw[(rid,cid)]):
                        local.append([rid,cid,[list(v) for v in raw[(rid,cid)]]])
                else:cross_keys.add((rid,cid))
        # Each rank-one mode has the SAME row-vector for every selected
        # column. Grouping identical vectors is an exact factorization.
        groups=defaultdict(list)
        for y,cid in real:
            col_group=base['column_labels'][str(base['edges'][cid][1])][i]
            for target in range(base['r']):
                if target==col_group:continue
                rows=tuple((rid,tuple(raw[(rid,cid)])) for x,rid in real
                           if base['row_labels'][str(base['edges'][rid][0])][i]==target)
                if not rows:continue
                signature=(pid,col_group,target,rows)
                groups[signature].append(cid)
        for (packet_id,source,target,rows),columns in groups.items():
            vals=[ring.valuation(c) for _,jet in rows for c in jet]
            weight=min(vals,default=precision)
            if weight>=precision:
                pruned+=1
                continue
            modes.append({'packet':packet_id,'source_group':source,
                          'target_group':target,'weight':weight,
                          'columns':sorted(columns),
                          'rows':[[rid,[list(c) for c in jet]] for rid,jet in rows]})
    return {'schema':'VERITAS_ETH_EXTENSION_MODES_V29','claim':'FINITE_EXTENSION_RING_RANK_ONE_MODES_ONLY',
        'd3_certificate':d3_certificate,'node':node,'precision':precision,
        'extension_degree':extension_degree,'irreducible_polynomial':ring.f,
        'jet_length':jet_length,'modes':modes,'local':local,
        'cross_pairs':[list(v) for v in sorted(cross_keys)],
        'fully_vanishing_modes_removed':pruned,
        'scope':{'geometric_tile_mode_enumerator':False,
                 'recursive_child_tensors':False,'subexponential_runtime_proven':False}}


def check_extension_modes(cert):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!='VERITAS_ETH_EXTENSION_MODES_V29' \
           or cert.get('claim')!='FINITE_EXTENSION_RING_RANK_ONE_MODES_ONLY':
            raise ValueError('incorrect certificate schema or mathematical claim')
        if cert.get('scope')!={'geometric_tile_mode_enumerator':False,
                 'recursive_child_tensors':False,'subexponential_runtime_proven':False}:
            raise ValueError('invalid scope')
        base=cert['d3_certificate'];_check_base(base)
        node=cert['node'];p=cert['precision'];e=cert['extension_degree'];length=cert['jet_length']
        if any(type(x) is not int for x in (node,p,e,length)) or not 2<=p<=64 or not 1<=e<=8 or not 1<=length<=min(16,2*base['L']):
            raise ValueError('malformed ring parameters')
        ring=ExtensionRing(p,first_irreducible(e))
        if cert['irreducible_polynomial']!=ring.f:
            raise ValueError('incorrect extension polynomial')
        raw=_raw_coeffs(base,ring,node,length);i=_val2(node)
        zero=(ring.zero,)*length
        local_expected={};cross=set()
        for packet in base['packets']:
            real=list(real_packet_slots(packet,base['L']))
            for x,rid in real:
                row_group=base['row_labels'][str(base['edges'][rid][0])][i]
                for y,cid in real:
                    col_group=base['column_labels'][str(base['edges'][cid][1])][i]
                    if row_group==col_group:
                        if raw[(rid,cid)]!=zero:local_expected[(rid,cid)]=raw[(rid,cid)]
                    else:cross.add((rid,cid))
        supplied={}
        for rid,cid,jet in cert['local']:
            key=(rid,cid)
            if key in supplied:raise ValueError('duplicated local pair')
            supplied[key]=tuple(tuple(x) for x in jet)
        if supplied!=local_expected:raise ValueError('local coefficient mismatch')
        reported=[tuple(x) for x in cert['cross_pairs']]
        if len(reported)!=len(cross) or set(reported)!=cross:
            raise ValueError('cross incidence mismatch')
        reconstructed={key:[ring.zero for _ in range(length)] for key in cross}
        seen=set()
        for mode in cert['modes']:
            pid=mode['packet'];source=mode['source_group'];target=mode['target_group'];weight=mode['weight']
            if any(type(x) is not int for x in (pid,source,target,weight)) or not 0<=pid<len(base['packets']) or not 0<=source<base['r'] or not 0<=target<base['r'] or source==target:
                raise ValueError('invalid mode metadata')
            columns=mode['columns']
            if not columns or len(set(columns))!=len(columns) or columns!=sorted(columns):
                raise ValueError('noncanonical mode columns')
            real={eid for _,eid in real_packet_slots(base['packets'][pid],base['L'])}
            rows={}
            for rid,jet in mode['rows']:
                if rid in rows or rid not in real or len(jet)!=length:
                    raise ValueError('invalid row coefficient list')
                new=[]
                for coeff in jet:
                    if len(coeff)!=e or any(type(x) is not int or x<0 or x>=ring.modulus for x in coeff):
                        raise ValueError('invalid ring coefficient')
                    new.append(tuple(coeff))
                rows[rid]=tuple(new)
            if not rows:raise ValueError('empty mode')
            minval=min(ring.valuation(v) for jet in rows.values() for v in jet)
            if minval!=weight or weight>=p:
                raise ValueError('invalid or nonminimal 2-adic weight')
            for cid in columns:
                if cid not in real or base['column_labels'][str(base['edges'][cid][1])][i]!=source:
                    raise ValueError('source mode incidence invalid')
                for rid,jet in rows.items():
                    if base['row_labels'][str(base['edges'][rid][0])][i]!=target or (rid,cid) not in cross:
                        raise ValueError('target mode incidence invalid')
                    if jet!=raw[(rid,cid)]:
                        raise ValueError('rank-one row profile is not direct Cauchy jet')
                    if (rid,cid) in seen:raise ValueError('overlapping modes')
                    seen.add((rid,cid))
                    for k,v in enumerate(jet):
                        reconstructed[(rid,cid)][k]=ring.add(reconstructed[(rid,cid)][k],v)
        for key in cross:
            if tuple(reconstructed[key])!=raw[key]:
                raise ValueError('cross Cauchy jet not reconstructed')
        return {'valid':True,'status':'FINITE_EXTENSION_RING_MODE_IDENTITY_VERIFIED',
                'modes':len(cert['modes']),'cross_pairs':len(cross),
                'precision':p,'extension_degree':e,'jet_length':length,
                'manuscript_geometric_modes':False,'recursive_child_networks':False,
                'subexponential_runtime_proven':False}
    except (ValueError,TypeError,IndexError,KeyError,OverflowError,ZeroDivisionError) as err:
        return {'valid':False,'status':'INVALID_EXTENSION_MODE_CERTIFICATE','reason':str(err)}
