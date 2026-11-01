"""v3.6 exact finite Cauchy packet tensors in the Boolean multilinear basis.

For a D.3 packet with k real edges and fixed row-halfbit assignment Y,
P_Y(X) = product_i ((1-Y_i)+(2Y_i-1)*sum_j W_ij(t+2L*V)*X_j).
There is a unique Boolean multilinear representation:
P_Y(X) = sum_{S subseteq [k]} A_Y(S) product_{j in S} X_j,
where X_j^2=X_j on Boolean inputs. We construct A_Y by sparse,
subset-union polynomial multiplication, and independently verify it by
Boolean Moebius inversion of directly evaluated P_Y(X).

Each packet tensor is checked against the original Cauchy half-edge network.
All arithmetic is exact in a truncated 2-adic extension-jet ring. This is a
*finite reference packet-tensor construction*, NOT the paper's specialized
recursive D.4.4 child packet tensors or its M/8/complexity theorem.
"""
from __future__ import annotations
from copy import deepcopy
from itertools import product
from time import monotonic

from veritas.research.eth_modes_v31.jet_tiles import check_jet_tile_modes, _v2
from veritas.research.eth_packing_v26.implicit import check_implicit_mode_source
from veritas.research.eth_recursion_v30.implicit_children import (
    _check_inputs, make_bipartite_edges, _direct_oracle, _deserialize_net, Limits)
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry

SCHEMA='VERITAS_ETH_EXACT_FINITE_PACKET_COEFFICIENT_TENSORS_V36'
CLAIM='FINITE_BOOLEAN_MULTILINEAR_CAUCHY_PACKET_TENSORS_ONLY'
SCOPE={
  'exact_finite_cauchy_packet_coefficients':True,
  'boolean_idempotent_polynomial_multiplication':True,
  'independent_moebius_coefficient_oracle':True,
  'independent_global_halfedge_contraction_oracle':True,
  'verified_d3_packing_and_geometric_mode_inputs':True,
  'manuscript_recursive_D44_packet_tensors':False,
  'manuscript_M_over_8_full_child_bound':False,
  'subexponential_runtime_proven':False,
}

class PacketTensorBudgetExceeded(RuntimeError):pass

class Meter:
    def __init__(self,max_work,timeout_s):
        if type(max_work) is not int or not 100<=max_work<=2_000_000:
            raise ValueError('max_work must be an integer in 100..2000000')
        if type(timeout_s) not in (int,float) or not 0<timeout_s<=30:
            raise ValueError('timeout_s must be in (0,30]')
        self.max_work=max_work; self.deadline=monotonic()+timeout_s;self.used=0
    def tick(self,amount=1):
        self.used+=amount
        if self.used>self.max_work or monotonic()>self.deadline:
            raise PacketTensorBudgetExceeded('packet reference work/time budget exhausted')


def _plus(table,mask,v,jr):
    if v==jr.zero:return
    z=jr.add(table.get(mask,jr.zero),v)
    if z==jr.zero:table.pop(mask,None)
    else:table[mask]=z


def _encode_jet(jet):
    return [list(component) for component in jet]


def _coefficients_by_expansion(real,L,t,jr,meter):
    """Explicit sparse Boolean-idempotent coefficient tables for all Y masks."""
    k=len(real)
    grid=[[jr.elem(shift_cauchy_entry(L,t,jr.base,x,y)[:jr.length])
           for y,_ in real] for x,_ in real]
    tables=[];max_nonzero=0
    for ymask in range(1<<k):
        poly={0:jr.one}
        for i in range(k):
            y=(ymask>>i)&1
            base=jr.zero if y else jr.one
            sign=1 if y else -1
            out={}
            for support,val in poly.items():
                meter.tick()
                _plus(out,support,jr.mul(val,base),jr)
                for j in range(k):
                    meter.tick()
                    coefficient=grid[i][j] if sign==1 else jr.neg(grid[i][j])
                    _plus(out,support|(1<<j),jr.mul(val,coefficient),jr)
            poly=out
        max_nonzero=max(max_nonzero,len(poly))
        tables.append(poly)
    return tables,grid,max_nonzero


def _evaluate_direct(ymask,xmask,grid,jr,meter):
    k=len(grid); z=jr.one
    for i in range(k):
        meter.tick()
        inner=jr.zero
        for j in range(k):
            if xmask>>j&1:inner=jr.add(inner,grid[i][j])
        h=inner if ymask>>i&1 else jr.sub(jr.one,inner)
        z=jr.mul(z,h)
    return z


def _independent_moebius_check(tables,grid,jr,meter):
    """Rebuild coefficients using direct evaluations + Boolean inversion."""
    k=len(grid);tested=0
    for ymask in range(1<<k):
        direct=[]
        for xmask in range(1<<k):
            direct.append(_evaluate_direct(ymask,xmask,grid,jr,meter));tested+=1
        # In place subset lattice transform: f(X)=sum_{S subseteq X} A(S).
        inverse=list(direct)
        for bit in range(k):
            for mask in range(1<<k):
                if mask>>bit&1:
                    meter.tick()
                    inverse[mask]=jr.sub(inverse[mask],inverse[mask^(1<<bit)])
        expected={s:v for s,v in enumerate(inverse) if v!=jr.zero}
        if expected!=tables[ymask]:
            raise ArithmeticError('packet polynomial differs from independent Boolean Moebius oracle')
    return tested


def _original_factor_value(net,xbits,ybits):
    out=1;M=net.edges
    for factor in net.factors:
        row=factor.label.startswith(('row:','clause:'))
        bits=ybits if row else xbits
        mask=sum(((bits>>e)&1)<<j for j,e in enumerate(factor.ports))
        out*=factor.table[mask]
        if not out:break
    return out


def _from_coefficients(packet_models,net,jr,meter):
    """Independently contract packet coefficient tensors and original factors."""
    M=net.edges; total=jr.zero
    for xb in range(1<<M):
        for yb in range(1<<M):
            meter.tick()
            factor_value=_original_factor_value(net,xb,yb)
            if not factor_value:continue
            result=jr.elem([[factor_value]])
            for packet in packet_models:
                edges=packet['edges']
                ym=sum(((yb>>edge)&1)<<j for j,edge in enumerate(edges))
                xm=sum(((xb>>edge)&1)<<j for j,edge in enumerate(edges))
                value=jr.zero
                for subset,coeff in packet['_tables'][ym].items():
                    meter.tick()
                    if subset & xm == subset:value=jr.add(value,coeff)
                result=jr.mul(result,value)
                if result==jr.zero:break
            total=jr.add(total,result)
    return total


def _prepare(net,mode_certificate,max_work,timeout_s):
    if not isinstance(mode_certificate,dict) or check_jet_tile_modes(mode_certificate).get('valid') is not True:
        raise ValueError('geometric mode prerequisite did not verify')
    d3=mode_certificate['d3_certificate'];t=mode_certificate['node']
    p=mode_certificate['precision'];e=mode_certificate['extension_degree'];length=mode_certificate['jet_length']
    if d3.get('schema')=='VERITAS_ETH_D3_IMPLICIT_ACTIVE_V1':
        if check_implicit_mode_source(d3).get('valid') is not True:
            raise ValueError('implicit D.3 packet source did not verify')
        if net.edges < 1 or net.edges > 6 or len(net.factors)>20:
            raise ValueError('finite packet tensor oracle supports 1..6 edges and <=20 factors')
    else:
        _check_inputs(net,d3,t,p,e,length)
    if make_bipartite_edges(net)!=d3['edges']:
        raise ValueError('tensor network endpoints differ from packet packing')
    meter=Meter(max_work,timeout_s)
    jr=JetRing(ExtensionRing(p,first_irreducible(e)),length)
    return d3,t,jr,meter


def construct_packet_tensor_certificate(net,mode_certificate,*,max_work=350000,timeout_s=12):
    d3,t,jr,meter=_prepare(net,mode_certificate,max_work,timeout_s)
    coordinate=_v2(t)
    packet_models=[];checked=0;max_nonzero=0
    for pid,packet in enumerate(d3['packets']):
        real=[(slot,eid) for slot,eid in enumerate(packet['slots']) if eid is not None]
        if len(real)>8:raise ValueError('finite packet capacity exceeds 8')
        tables,grid,nz=_coefficients_by_expansion(real,d3['L'],t,jr,meter)
        checked+=_independent_moebius_check(tables,grid,jr,meter)
        max_nonzero=max(max_nonzero,nz)
        rowgroups=[d3['row_labels'][str(d3['edges'][eid][0])][coordinate] for _,eid in real]
        colgroups=[d3['column_labels'][str(d3['edges'][eid][1])][coordinate] for _,eid in real]
        packet_models.append({
            'packet_id':pid,'edges':[eid for _,eid in real],
            'slots':[slot for slot,_ in real],
            'row_groups':rowgroups,'column_groups':colgroups,
            'cross_group_pairs':sum(r!=c for r in rowgroups for c in colgroups),
            'coefficient_rows':[
                {'row_bit_mask':ymask,
                 'monomials':[[mask,_encode_jet(val)] for mask,val in sorted(poly.items())]}
                 for ymask,poly in enumerate(tables)],
            '_tables':tables,
        })
    expected_edges=sorted(eid for packet in packet_models for eid in packet['edges'])
    if expected_edges!=list(range(net.edges)):
        raise ArithmeticError('packet tensors do not cover each original wire exactly once')
    computed=_from_coefficients(packet_models,net,jr,meter)
    # Independent direct half-edge contraction uses original W-entries, not packet coefficient tables.
    direct_budget=Limits(max_assignments=min(2_000_000,max_work),timeout_s=min(timeout_s,20))
    oracle=_direct_oracle(net,d3,t,jr,direct_budget)
    if computed!=oracle:raise ArithmeticError('global packet contraction disagrees with direct half-edge oracle')
    clean=[{k:v for k,v in pkt.items() if k!='_tables'} for pkt in packet_models]
    return {
        'schema':SCHEMA,'claim':CLAIM,'scope':deepcopy(SCOPE),
        'network':{'edges':net.edges,'factors':[{'ports':list(f.ports),'table':list(f.table),'label':f.label} for f in net.factors]},
        'mode_certificate':deepcopy(mode_certificate),
        'packets':clean,'result':_encode_jet(computed),
        'stats':{'packets':len(clean),'original_wires':net.edges,
            'coefficient_rows':sum(len(pkt['coefficient_rows']) for pkt in clean),
            'moebius_assignments_checked':checked,
            'max_nonzero_packet_coefficients':max_nonzero,
            'work_units':meter.used,'direct_oracle_assignments':direct_budget.used},
        'manuscript_M_over_8_child_bound_verified':False,
        'subexponential_runtime_proven':False,
    }


def check_packet_tensor_certificate(cert,*,max_work=350000,timeout_s=12):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!=SCHEMA or cert.get('claim')!=CLAIM or cert.get('scope')!=SCOPE:
            raise ValueError('unrecognized schema or mathematical claim')
        expected=construct_packet_tensor_certificate(
            _deserialize_net(cert['network']),cert['mode_certificate'],
            max_work=max_work,timeout_s=timeout_s)
        # Statistics include work counts computed from deterministic control flow.
        if expected!=cert:raise ValueError('certificate differs from complete independent source replay')
        return {'valid':True,'status':'EXACT_FINITE_CAUCHY_PACKET_COEFFICIENTS_REPLAYED',
                'independent_coefficient_oracle':True,'independent_global_oracle':True,
                'manuscript_recursive_D44_packet_tensors':False,
                'manuscript_M_over_8_child_bound':False,'subexponential_runtime_proven':False}
    except (ValueError,KeyError,IndexError,TypeError,OverflowError,ArithmeticError,
            RuntimeError,TimeoutError,ZeroDivisionError) as exc:
        return {'valid':False,'status':'INVALID_V36_PACKET_TENSOR_CERTIFICATE','reason':str(exc)}
