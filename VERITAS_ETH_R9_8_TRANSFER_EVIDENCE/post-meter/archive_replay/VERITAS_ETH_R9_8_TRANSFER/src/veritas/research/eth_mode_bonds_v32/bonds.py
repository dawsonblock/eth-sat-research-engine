"""Exact finite group tensors joined on mode-exponent bonds (v3.2).

A genuine, inspectable *finite mode-bond network*: each group tensor carries a
mode exponent index on every source/target incident geometric mode. The
contraction identifies equal exponents at the two endpoints and sums them.
The method is an exact bounded algebraic identity over truncated extension
jets, NOT the manuscript's shrinking recursive packet-tensor construction.

Independent replay checks D.3 packing, mode decomposition, every child tensor
entry, bond contraction and the original 4**M half-edge oracle.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import product
from time import monotonic

from veritas.research.eth_modes_v27.enumeration import weighted_tuples, count_tuples
from veritas.research.eth_modes_v31.jet_tiles import (check_jet_tile_modes, _v2,
    _serialize_net, _deserialize_net)
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursion_v30.implicit_children import (
    make_bipartite_edges, _check_inputs, _direct_oracle, Limits)

SCOPE = {
    'finite_group_mode_bond_tensors': True,
    'exact_sparse_mode_index_contraction': True,
    'manuscript_recursive_packet_tensors': False,
    'manuscript_m_over_8_guarantee': False,
    'subexponential_runtime_proven': False,
}
SCHEMA = 'VERITAS_ETH_MODE_BOND_NETWORK_V32'
CLAIM = 'FINITE_EXACT_SPARSE_MODE_BONDS_ONLY'

class BondBudgetExceeded(RuntimeError):
    pass

class WorkMeter:
    def __init__(self, max_work, timeout_s):
        if type(max_work) is not int or not 1 <= max_work <= 1_000_000:
            raise ValueError('work cap must be an integer 1..1000000')
        if type(timeout_s) not in (int,float) or not 0 < timeout_s <= 30:
            raise ValueError('timeout must be positive and <=30 seconds')
        self.max_work=max_work
        self.deadline=monotonic()+timeout_s
        self.used=0
        self.peak_entries=0
        self.joins=0
    def tick(self,units=1):
        self.used+=units
        if self.used>self.max_work or monotonic()>self.deadline:
            raise BondBudgetExceeded('exact mode bond work or time budget exceeded')


def _sparse_add(table,key,val,jr):
    if val == jr.zero:return
    summed=jr.add(table.get(key,jr.zero),val)
    if summed==jr.zero:table.pop(key,None)
    else:table[key]=summed


def _group_tensors(net,cert,jr,meter,max_entries):
    """Build actual source/target mode-indexed group transfer tensors.

    A target mode contributes a coefficient to the row polynomial; a source
    mode contributes a column linear-form moment. Both refer to the SAME
    exponent bond, later contracted (summed) across the two groups.
    """
    d3=cert['d3_certificate'];m=net.edges;i=_v2(cert['node']);p=cert['precision']
    modes=cert['modes'];weights=[z['weight'] for z in modes];K=len(modes)
    rowgroups=[d3['row_labels'][str(u)][i] for u,v in d3['edges']]
    colgroups=[d3['column_labels'][str(v)][i] for u,v in d3['edges']]
    byrow=defaultdict(list); local=defaultdict(list)
    for rid,cid,coef in cert['local']: local[rid].append((cid,jr.elem(coef)))
    for mid,mode in enumerate(modes):
        for rid,coef in mode['rows']:byrow[rid].append((mid,jr.elem(coef)))
    factors=defaultdict(list)
    for f in net.factors:
        k=f.label.split(':',1)
        if len(k)!=2:raise ValueError('invalid factor label')
        role=k[0]
        if role in ('row','clause'):
            group=d3['row_labels'].get(k[1],[0]*d3['a'])[i]
            offsets=tuple(f.ports)
        elif role in ('col','variable'):
            group=d3['column_labels'].get(k[1],[0]*d3['a'])[i]
            offsets=tuple(m+e for e in f.ports)
        else:raise ValueError('unexpected factor role')
        factors[group].append((offsets,f.table))
    groups=sorted(set(rowgroups+colgroups+list(factors)))
    tensors=[]; zero_beta=(0,)*K
    for group in groups:
        owned=tuple([rid for rid in range(m) if rowgroups[rid]==group]+[m+cid for cid in range(m) if colgroups[cid]==group])
        incident=tuple(mid for mid,mode in enumerate(modes) if group in (mode['source_group'],mode['target_group']))
        if count_tuples([weights[j] for j in incident],p,cap=max_entries)>max_entries:
            raise BondBudgetExceeded('local tensor mode-index domain exceeds cap')
        local_indices=tuple(weighted_tuples([weights[j] for j in incident],p,max_tuples=max_entries))
        rows=[rid for rid in range(m) if rowgroups[rid]==group]
        # Correct even if there are no modes: the sole key is the empty tuple.
        tensor={};assignments=0
        for bits in product((0,1),repeat=len(owned)):
            meter.tick();assignments+=1
            assign=dict(zip(owned,bits))
            prod_original=1
            for ports,table in factors[group]:
                address=sum(assign[q]<<j for j,q in enumerate(ports))
                prod_original*=table[address]
            if not prod_original:continue
            poly={zero_beta:jr.elem([[prod_original]])}
            for rid in rows:
                local_value=jr.zero
                for cid,c in local[rid]:
                    if assign[m+cid]:local_value=jr.add(local_value,c)
                base=local_value if assign[rid] else jr.sub(jr.one,local_value)
                sign=1 if assign[rid] else -1
                nxt={}
                for alpha,value in poly.items():
                    meter.tick()
                    _sparse_add(nxt,alpha,jr.mul(value,base),jr)
                    for mid,c in byrow[rid]:
                        updated=list(alpha);updated[mid]+=1;updated=tuple(updated)
                        if sum(updated[j]*weights[j] for j in range(K))>=p:continue
                        _sparse_add(nxt,updated,jr.mul(value,c if sign==1 else jr.neg(c)),jr)
                poly=nxt
                if len(poly)>max_entries:raise BondBudgetExceeded('local polynomial state cap exceeded')
            source_moments={mid:sum(coef*assign[m+cid] for cid,coef in mode['column_terms'])
                            for mid,mode in enumerate(modes) if mode['source_group']==group}
            for key in local_indices:
                meter.tick()
                target_beta=tuple(key[incident.index(j)] if j in incident and modes[j]['target_group']==group else 0 for j in range(K))
                coeff=poly.get(target_beta,jr.zero)
                if coeff==jr.zero:continue
                for mid,x in source_moments.items():
                    if mid not in incident:continue
                    power=key[incident.index(mid)]
                    if not power:continue
                    if not x:
                        coeff=jr.zero;break
                    coeff=jr.mul(coeff,jr.elem([[pow(x,power)]]))
                _sparse_add(tensor,key,coeff,jr)
            if len(tensor)>max_entries:raise BondBudgetExceeded('child tensor entry cap exceeded')
        meter.peak_entries=max(meter.peak_entries,len(tensor))
        tensors.append({'group':group,'modes':incident,'owned_halfbits':owned,
                        'assignments_evaluated':assignments,'table':tensor})
    return tensors


def _join(a,b,jr,meter,max_entries):
    keys=tuple(sorted(set(a['modes']) | set(b['modes'])))
    common=tuple(sorted(set(a['modes']) & set(b['modes'])))
    ai={mode:i for i,mode in enumerate(a['modes'])}
    bi={mode:i for i,mode in enumerate(b['modes'])}
    # Index the right tensor by common exponents; do not loop over all pairs.
    index=defaultdict(list)
    for kb,vb in b['table'].items():
        index[tuple(kb[bi[m]] for m in common)].append((kb,vb))
    out={}
    for ka,va in a['table'].items():
        compatible=index.get(tuple(ka[ai[m]] for m in common),())
        for kb,vb in compatible:
            meter.tick();meter.joins+=1
            kt=tuple(ka[ai[m]] if m in ai else kb[bi[m]] for m in keys)
            _sparse_add(out,kt,jr.mul(va,vb),jr)
            if len(out)>max_entries:raise BondBudgetExceeded('join table cap exceeded')
    meter.peak_entries=max(meter.peak_entries,len(out))
    return {'modes':keys,'table':out}


def _contract(tensors,jr,meter,max_entries):
    factors=[{'modes':t['modes'],'table':t['table']} for t in tensors]
    # Every mode is a bond touching precisely two symbol-group tensors.
    mode_ids=sorted(set(mode for f in factors for mode in f['modes']))
    for mid in mode_ids:
        bucket=[f for f in factors if mid in f['modes']]
        factors=[f for f in factors if mid not in f['modes']]
        if not bucket:continue
        merged=bucket[0]
        for f in bucket[1:]:merged=_join(merged,f,jr,meter,max_entries)
        idx=merged['modes'].index(mid)
        reduced_modes=tuple(k for k in merged['modes'] if k!=mid)
        reduced={}
        for key,value in merged['table'].items():
            meter.tick()
            reduced_key=key[:idx]+key[idx+1:]
            _sparse_add(reduced,reduced_key,value,jr)
            if len(reduced)>max_entries:raise BondBudgetExceeded('marginalized table cap exceeded')
        factors.append({'modes':reduced_modes,'table':reduced})
    total=jr.one
    for f in factors:
        if f['modes']:raise ArithmeticError('unsummed bond index remains')
        total=jr.mul(total,f['table'].get((),jr.zero))
    return total


def construct_bond_certificate(net,mode_certificate,*,max_work=180000,
                               max_entries=3000,timeout_s=12):
    if not check_jet_tile_modes(mode_certificate)['valid']:
        raise ValueError('invalid v3.1 geometric mode certificate')
    d3=mode_certificate['d3_certificate'];t=mode_certificate['node'];p=mode_certificate['precision']
    e=mode_certificate['extension_degree'];length=mode_certificate['jet_length']
    _check_inputs(net,d3,t,p,e,length)
    if make_bipartite_edges(net)!=d3['edges']:
        raise ValueError('tensor network endpoints do not match packing')
    if type(max_entries) is not int or not 1<=max_entries<=10000:
        raise ValueError('invalid entry budget')
    meter=WorkMeter(max_work,timeout_s)
    jr=JetRing(ExtensionRing(p,first_irreducible(e)),length)
    children=_group_tensors(net,mode_certificate,jr,meter,max_entries)
    total=_contract(children,jr,meter,max_entries)
    budget=Limits(max_assignments=min(2_000_000,max_work),timeout_s=min(20,timeout_s))
    oracle=_direct_oracle(net,d3,t,jr,budget)
    if total!=oracle:
        raise ArithmeticError('exact mode-bond contraction disagrees with independent half-edge oracle')
    # Serialize all child entries, not only hashes, to make the finite tensor
    # network inspectable. Independent verifier regenerates entries from source.
    described=[]
    for child in children:
        described.append({'group':child['group'],'mode_indices':list(child['modes']),
          'owned_halfbits':list(child['owned_halfbits']),
          'assignments_evaluated':child['assignments_evaluated'],
          'entries':[[list(key),[list(x) for x in value]]
                     for key,value in sorted(child['table'].items())]})
    return {'schema':SCHEMA,'claim':CLAIM,'scope':dict(SCOPE),
            'network':{'edges':net.edges,'factors':[{'ports':list(f.ports),
                       'table':list(f.table),'label':f.label} for f in net.factors]},
            'mode_certificate':mode_certificate,
            'children':described,'result':[list(x) for x in total],
            'direct_half_edge_match':True,
            'stats':{'work_units':meter.used,'joined_entries':meter.joins,
                     'peak_sparse_entries':meter.peak_entries,
                     'oracle_assignment_checks':budget.used,
                     'child_count':len(children),
                     'mode_count':len(mode_certificate['modes'])}}


def check_bond_certificate(cert,*,max_work=180000,max_entries=3000,timeout_s=12):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!=SCHEMA or cert.get('claim')!=CLAIM or cert.get('scope')!=SCOPE:
            raise ValueError('unsupported claim/scope/schema')
        net=_deserialize_net(cert['network'])
        result=construct_bond_certificate(net,cert['mode_certificate'],max_work=max_work,
                                         max_entries=max_entries,timeout_s=timeout_s)
        if cert!=result:raise ValueError('certificate does not match independent source replay')
        return {'valid':True,'status':'FINITE_SPARSE_MODE_BOND_NETWORK_VERIFIED',
                'subexponential_runtime_proven':False,
                'manuscript_recursive_packet_tensors':False}
    except (ValueError,KeyError,TypeError,IndexError,OverflowError,ArithmeticError,
            ZeroDivisionError,RuntimeError,TimeoutError) as exc:
        return {'valid':False,'status':'INVALID_V32_MODE_BOND_CERTIFICATE','reason':str(exc)}
