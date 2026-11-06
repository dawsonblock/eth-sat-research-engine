"""Finite reference construction for the *group-local* child networks in D.4.4.

Fix a global weighted mode exponent tuple beta. For each (packet, group),
extract target-mode coefficients from the product of row factors, then
substitute source-mode linear forms raised to beta. The resulting packet
vertex has ONLY the original half-port wires owned by this group. Modes
are no longer tensor-network edges; beta is immutable metadata.

This module checks finite instances by exhaustive contraction, not the
manuscript's subexponential running-time or universal M/8 theorem.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import product
from time import monotonic
from copy import deepcopy

from veritas.research.eth_modes_v31.jet_tiles import (
    check_jet_tile_modes, _v2, _serialize_net, _deserialize_net)
from veritas.research.eth_modes_v27.enumeration import weighted_tuples, count_tuples
from veritas.research.eth_recursion_v30.implicit_children import (
    make_bipartite_edges, _check_inputs, _direct_oracle, Limits)
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing

SCHEMA = 'VERITAS_D44_EXACT_GROUP_LOCAL_CHILD_REFERENCE_V1'
CLAIM = 'FINITE_GROUP_LOCAL_PACKET_TENSORS_AND_EXACT_IDENTITY_ONLY'
SCOPE = {
    'fixed_beta_not_an_edge': True,
    'group_local_packet_coefficient_extraction': True,
    'source_mode_substitution': True,
    'original_halfports_become_child_wires': True,
    'independent_direct_cauchy_oracle': True,
    'complete_manuscript_M_over_8_theorem_proven': False,
    'subexponential_complexity_proven': False,
}
class ResourceLimit(RuntimeError):
    pass

class Meter:
    def __init__(self, work: int, seconds: float):
        if type(work) is not int or not 100 <= work <= 3_000_000:
            raise ValueError('max_work must be integer in 100..3_000_000')
        if type(seconds) not in (float,int) or not 0 < seconds <= 60:
            raise ValueError('timeout must be 0..60 seconds')
        self.work=work
        self.used=0
        self.end=monotonic()+seconds
    def tick(self,n=1):
        self.used+=n
        if self.used>self.work or monotonic()>self.end:
            raise ResourceLimit('finite reference computation budget exceeded')

def _pow(jr, a, k):
    if k < 0: raise ValueError('negative exponent')
    z=jr.one
    while k:
        if k & 1: z=jr.mul(z,a)
        k >>= 1
        if k: a=jr.mul(a,a)
    return z


def _data(net,mode_cert):
    d3=mode_cert['d3_certificate']; i=_v2(mode_cert['node']); M=net.edges
    rowgroups={rid:d3['row_labels'][str(u)][i] for rid,(u,v) in enumerate(d3['edges'])}
    colgroups={cid:d3['column_labels'][str(v)][i] for cid,(u,v) in enumerate(d3['edges'])}
    original=defaultdict(list)
    for f in net.factors:
        kind,ident=f.label.split(':',1)
        if kind in ('row','clause'):
            grp=d3['row_labels'].get(ident,[0]*d3['a'])[i]
        elif kind in ('col','variable'):
            grp=d3['column_labels'].get(ident,[0]*d3['a'])[i]
        else: raise ValueError('invalid original factor side')
        original[grp].append(f)
    local=defaultdict(list)
    for rid,cid,coeffs in mode_cert['local']:
        local[rid].append((cid,coeffs))
    targeted=defaultdict(list)
    for mid,m in enumerate(mode_cert['modes']):
        for rid,coeffs in m['rows']:
            targeted[rid].append((mid,coeffs))
    packets=[]
    for packet in d3['packets']:
        entries=[eid for eid in packet['slots'] if eid is not None]
        packets.append(entries)
    return d3,rowgroups,colgroups,original,local,targeted,packets


def _packet_value(pid,g,beta,assignment,mode_cert,data,jr,meter):
    """Exact entry of manuscript-style packet tensor K[P,g,beta]."""
    d3,rowgroups,colgroups,original,local,targeted,packets=data
    modes=mode_cert['modes']
    rows=[eid for eid in packets[pid] if rowgroups[eid]==g]
    target_indices=tuple(mid for mid,m in enumerate(modes)
                         if m['packet']==pid and m['target_group']==g)
    source_indices=tuple(mid for mid,m in enumerate(modes)
                         if m['packet']==pid and m['source_group']==g)
    position={mid:j for j,mid in enumerate(target_indices)}
    goal=tuple(beta[mid] for mid in target_indices)
    zeros=(0,)*len(target_indices)
    poly={zeros:jr.one}
    M=d3['M']
    for rid in rows:
        meter.tick()
        s=jr.zero
        for cid,encoded in local[rid]:
            if assignment[M+cid]:
                s=jr.add(s,jr.elem(encoded))
        value=assignment[rid]
        constant=s if value else jr.sub(jr.one,s)
        sign=1 if value else -1
        nxt={}
        for key,coeff in poly.items():
            c=jr.mul(coeff,constant)
            nxt[key]=jr.add(nxt.get(key,jr.zero),c)
            for mid,encoded in targeted[rid]:
                if mid not in position: raise ArithmeticError('target mode in wrong packet')
                j=position[mid]
                if key[j]>=goal[j]: continue
                newkey=key[:j]+(key[j]+1,)+key[j+1:]
                t=jr.mul(coeff,jr.elem(encoded))
                if sign<0: t=jr.neg(t)
                nxt[newkey]=jr.add(nxt.get(newkey,jr.zero),t)
        poly={k:v for k,v in nxt.items() if v!=jr.zero}
    result=poly.get(goal,jr.zero)
    # Every source-mode is now a LOCAL scalar function of column bits.
    for mid in source_indices:
        exponent=beta[mid]
        if not exponent: continue
        m=modes[mid]
        lx=sum(int(jpow)*int(assignment[M+cid]) for cid,jpow in m['column_terms'])
        result=jr.mul(result,_pow(jr,jr.elem([[lx]]),exponent))
    return result


def _group_value(g,beta,net,mode_cert,data,jr,meter):
    d3,rowgroups,colgroups,original,local,targeted,packets=data
    M=net.edges
    owned=tuple([rid for rid in range(M) if rowgroups[rid]==g]
                 +[M+cid for cid in range(M) if colgroups[cid]==g])
    packet_ids=tuple(pid for pid,eds in enumerate(packets)
                     if any(rowgroups[e]==g or colgroups[e]==g for e in eds))
    value=jr.zero
    for bits in product((0,1),repeat=len(owned)):
        meter.tick()
        assignment=dict(zip(owned,bits))
        original_product=1
        for f in original[g]:
            isrow=f.label.startswith(('row:','clause:'))
            mask=sum(int(assignment[e if isrow else M+e])<<j
                     for j,e in enumerate(f.ports))
            original_product*=f.table[mask]
            if not original_product: break
        if not original_product: continue
        prod=jr.elem([[original_product]])
        for pid in packet_ids:
            prod=jr.mul(prod,_packet_value(pid,g,beta,assignment,mode_cert,data,jr,meter))
            if prod==jr.zero: break
        value=jr.add(value,prod)
    return value,owned,packet_ids


def construct_child_reference(net,mode_cert,*,max_work=600_000,
                              timeout_s=20.0,max_tuples=3000,max_owned=12,
                              _shared_meter=None):
    if _shared_meter is not None:
        _shared_meter.tick()
    valid=check_jet_tile_modes(mode_cert, _budget=_shared_meter)
    if _shared_meter is not None:
        _shared_meter.tick()
    if valid.get('valid') is not True: raise ValueError('invalid mode certificate: '+str(valid))
    d3=mode_cert['d3_certificate'];t=mode_cert['node'];p=mode_cert['precision']
    e=mode_cert['extension_degree'];length=mode_cert['jet_length']
    _check_inputs(net,d3,t,p,e,length,_budget=_shared_meter)
    if make_bipartite_edges(net)!=d3['edges']:
        raise ValueError('network and packing incidence mismatch')
    if type(max_owned) is not int or not 1<=max_owned<=20:
        raise ValueError('invalid max_owned')
    if type(max_tuples) is not int or not 1<=max_tuples<=3000:
        raise ValueError('invalid max_tuples')
    data=_data(net,mode_cert)
    rowgroups,colgroups=data[1],data[2]
    M=net.edges
    groups=tuple(range(d3['r']))
    owned_counts={g:sum(grp==g for grp in rowgroups.values())
                      +sum(grp==g for grp in colgroups.values()) for g in groups}
    if max(owned_counts.values(),default=0)>max_owned:
        raise ResourceLimit('group too large for exhaustive finite oracle')
    count=count_tuples([m['weight'] for m in mode_cert['modes']],p,cap=max_tuples)
    meter = _shared_meter if _shared_meter is not None else Meter(max_work,timeout_s)
    if _shared_meter is not None:
        meter.tick()
    jr=JetRing(ExtensionRing(p,first_irreducible(e)),length)
    total=jr.zero
    per_group_records={g:{'group':g,'child_wires':owned_counts[g],
                          'original_halfports':owned_counts[g],
                          'extra_mode_bond_wires':0,
                          'packet_vertices':sum(any(data[1][k]==g or data[2][k]==g for k in pkt)
                                                 for pkt in data[6]),
                          'numeric_bound_6M_over_r':(owned_counts[g]*d3['r']<=6*M),
                          'numeric_bound_strict_M_over_8':(owned_counts[g]*8<M)}
                       for g in groups}
    checksum=0
    for beta in weighted_tuples([m['weight'] for m in mode_cert['modes']],p,max_tuples=max_tuples):
        prod=jr.one
        for g in groups:
            val,owned,ids=_group_value(g,beta,net,mode_cert,data,jr,meter)
            prod=jr.mul(prod,val)
        total=jr.add(total,prod)
        checksum+=1
    reference=_direct_oracle(net,d3,t,jr,
                             meter if _shared_meter is not None else
                             Limits(max_assignments=max_work,timeout_s=timeout_s))
    if _shared_meter is not None:
        meter.tick()
    if total!=reference:
        raise ArithmeticError('group-local child networks disagree with direct half-edge oracle')
    return {'schema':SCHEMA,'claim':CLAIM,'scope':dict(SCOPE),
            'network':_serialize_net(net),'mode_certificate':deepcopy(mode_cert),
            'result':[list(x) for x in total],
            'children':list(per_group_records.values()),'mode_tuple_count':count,
            'mode_tuples_evaluated':checksum,'work':meter.used,
            'exact_direct_reference_matches':True,
            'full_manuscript_preconditions_verified':False,
            'manuscript_M_over_8_theorem_proven':False,
            'subexponential_runtime_proven':False}


def verify_child_reference(cert,*,max_work=600_000,timeout_s=20.0):
    """Reconstruct from immutable claimed inputs; never trust reported verdicts."""
    try:
        if not isinstance(cert,dict) or cert.get('schema')!=SCHEMA or cert.get('claim')!=CLAIM or cert.get('scope')!=SCOPE:
            raise ValueError('unsupported claim or schema')
        network=_deserialize_net(cert['network'])
        expected=construct_child_reference(network,cert['mode_certificate'],
                                           max_work=max_work,timeout_s=timeout_s)
        if cert!=expected:
            raise ValueError('certificate replay mismatch')
        return {'valid':True,'status':'FINITE_GROUP_LOCAL_CHILD_IDENTITY_VERIFIED',
                'subexponential_runtime_proven':False}
    except (ValueError,KeyError,IndexError,TypeError,ArithmeticError,OverflowError,
            ResourceLimit,TimeoutError,ZeroDivisionError) as exc:
        return {'valid':False,'status':'INVALID_OR_INCONCLUSIVE',
                'reason':str(exc),'subexponential_runtime_proven':False}
