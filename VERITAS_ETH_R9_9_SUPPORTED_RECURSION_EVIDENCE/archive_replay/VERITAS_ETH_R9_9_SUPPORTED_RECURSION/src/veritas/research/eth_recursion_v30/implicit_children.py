"""Finite implicit extension-ring Taylor-jet child tensors (v3.0 reference).

At a nonzero Cauchy interpolation node, every original wire e is split into
row half-bit Y_e and column half-bit X_e. A row's Cauchy factor is
  H_e(Y_e, X) = (sum_j W_{e,j}(t+2L V) X_j) if Y_e else
                   1 - (sum_j W_{e,j}(t+2L V) X_j).
Original row and column factors evaluate on their respective half-bits.

Assign factors to their *verified D.3 symbol groups*. For each group, define
an implicit boundary tensor by summing over only its internal variables.
The product of these child tensors summed over shared boundary assignments
is EXACT, without making large explicit child tables.

This is a conventional exact separator identity using D.3 group labels.
It deliberately does NOT use v2.9 rank-one modes to make D.4.4 children;
its runtime can be exponential, and it has no M/8 or complexity guarantee.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import product
from time import monotonic
from collections import defaultdict
from typing import Callable

from veritas.research.tensor import TensorNetwork, Factor
from veritas.research.eth_packing_v26.checker import verify_d3_packing
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_interpolation.shifted_cauchy import shift_cauchy_entry
from veritas.research.eth_modes_v29.extension_modes import check_extension_modes
from veritas.research.eth_packing_v26.implicit import real_packet_slots


class ImplicitBudgetExceeded(RuntimeError):
    """Fail closed: a capped exact reference cannot certify a partial result."""


@dataclass
class Limits:
    max_assignments: int = 250_000
    timeout_s: float = 12.0
    used: int = 0
    deadline: float = field(init=False)

    def __post_init__(self):
        if type(self.max_assignments) is not int or not 1 <= self.max_assignments <= 2_000_000:
            raise ValueError('invalid assignment budget')
        if type(self.timeout_s) not in (int, float) or not 0 < self.timeout_s <= 30:
            raise ValueError('invalid timeout')
        self.deadline = monotonic() + self.timeout_s

    def tick(self):
        self.used += 1
        if self.used > self.max_assignments or monotonic() > self.deadline:
            raise ImplicitBudgetExceeded('finite reference assignment/time budget exhausted')


@dataclass(frozen=True)
class LazyFactor:
    label: str
    group: int
    ports: tuple[int, ...]
    eval_at: Callable[[dict[int, int]], tuple]


@dataclass
class LazyChild:
    group: int
    factors: tuple[LazyFactor, ...]
    boundary: tuple[int, ...]
    internal: tuple[int, ...]
    jets: JetRing
    budget: Limits
    cache: dict[tuple[int,...], tuple] = field(default_factory=dict)

    def evaluate(self, boundary_assignment: dict[int, int]):
        key=tuple(boundary_assignment[i] for i in self.boundary)
        if key in self.cache:
            return self.cache[key]
        result=self.jets.zero
        for bits in product((0,1),repeat=len(self.internal)):
            self.budget.tick()
            assignment=dict(boundary_assignment)
            assignment.update(zip(self.internal,bits))
            val=self.jets.one
            for factor in self.factors:
                val=self.jets.mul(val,factor.eval_at(assignment))
                if val==self.jets.zero:break
            result=self.jets.add(result,val)
        self.cache[key]=result
        return result


def make_bipartite_edges(net: TensorNetwork) -> list[list[int]]:
    """Return edges in exactly the port order required by D.3 packets."""
    owners=[[] for _ in range(net.edges)]
    for f in net.factors:
        if f.label.startswith('clause:') or f.label.startswith('row:'):
            role=0
        elif f.label.startswith('variable:') or f.label.startswith('col:'):
            role=1
        else:raise ValueError('only clause/variable or row/col bipartite labels supported')
        try:vid=int(f.label.split(':',1)[1])
        except (IndexError,ValueError) as exc:raise ValueError('invalid vertex label') from exc
        if vid<0:raise ValueError('negative vertex ID')
        for e in f.ports: owners[e].append((role,vid))
    if any(len(x)!=2 or {role for role,_ in x}!={0,1} for x in owners):
        raise ValueError('each edge must have one row and one column endpoint')
    return [[dict(o)[0],dict(o)[1]] for o in owners]


def _check_inputs(net, base, node, precision, e, length, _budget=None):
    if net.edges < 1 or net.edges > 6 or len(net.factors)>20:
        raise ValueError('finite independent oracle supports 1..6 edges and <=20 factors')
    if any(type(v) is not int for v in (node,precision,e,length)) or not 2<=precision<=32 or not 1<=e<=8 or not 1<=length<=6:
        raise ValueError('out of bounds ring parameters')
    if not isinstance(base,dict) or verify_d3_packing(base,check_trace=True,_budget=_budget).get('valid') is not True:
        raise ValueError('D.3 certificate did not verify')
    if base['edges'] != make_bipartite_edges(net):
        raise ValueError('D.3 edges differ from tensor network endpoints')
    if not -base['L'] <= node < base['L'] or node==0:
        raise ValueError('require a nonzero Cauchy interpolation node')
    valuation=(abs(node)&-abs(node)).bit_length()-1
    if valuation>=base['a']:
        raise ValueError('node valuation has no packing coordinate')
    if length>2*base['L']:
        raise ValueError('Cauchy jet length exceeds degree bound')
    return valuation


def _build_factors(net, base, node, jets, coordinate):
    ring=jets.base; m=net.edges; factors=[]
    for f in net.factors:
        row=f.label.startswith(('row:','clause:'))
        tag=f.label.split(':',1)[1]
        labels=base['row_labels'] if row else base['column_labels']
        group=labels.get(tag,[0]*base['a'])[coordinate]
        offsets=tuple(e if row else m+e for e in f.ports)
        # Capture table and ports by value (not the mutable for-loop variable).
        table=f.table
        def eval_original(assign, ports=offsets, tab=table, jr=jets):
            mask=sum((assign[p]&1)<<i for i,p in enumerate(ports))
            return jr.elem([[tab[mask]]])
        factors.append(LazyFactor(f.label,group,offsets,eval_original))
    for packet_id, packet in enumerate(base['packets']):
        real=list(real_packet_slots(packet,base['L']))
        for x,rid in real:
            group=base['row_labels'][str(base['edges'][rid][0])][coordinate]
            columns=tuple((m+cid,shift_cauchy_entry(base['L'],node,ring,x,y)[:jets.length])
                          for y,cid in real)
            ports=(rid,)+tuple(col for col,_ in columns)
            def eval_h(assign, y_index=rid, coeffs=columns, jr=jets):
                z=jr.zero
                for col,coeff in coeffs:
                    if assign[col]:z=jr.add(z,coeff)
                return z if assign[y_index] else jr.sub(jr.one,z)
            factors.append(LazyFactor(f'cauchy-row:{rid}:packet:{packet_id}',group,ports,eval_h))
    return tuple(factors)


def _children(factors,jets,budget):
    groups=defaultdict(list); owners=defaultdict(set)
    for f in factors:
        groups[f.group].append(f)
        for p in f.ports:owners[p].add(f.group)
    shared={p for p,gs in owners.items() if len(gs)>1}
    children=[]
    for group,fs in sorted(groups.items()):
        support=set(p for f in fs for p in f.ports)
        boundary=tuple(sorted(support & shared))
        internal=tuple(sorted(support - shared))
        if len(internal)>16 or len(boundary)>12:
            raise ImplicitBudgetExceeded('implicit child internal/boundary cap exceeded')
        children.append(LazyChild(group,tuple(fs),boundary,internal,jets,budget))
    if len(shared)>12:
        raise ImplicitBudgetExceeded('global boundary width cap exceeded')
    return tuple(children),tuple(sorted(shared))


def _grouped_contract(factors,jets,budget):
    children,boundary=_children(factors,jets,budget)
    total=jets.zero
    for bits in product((0,1),repeat=len(boundary)):
        budget.tick()
        assign=dict(zip(boundary,bits))
        prod=jets.one
        for child in children:
            prod=jets.mul(prod,child.evaluate(assign))
            if prod==jets.zero:break
        total=jets.add(total,prod)
    summary=[{'group':c.group,'boundary':list(c.boundary),'internal':list(c.internal),
              'factors':[f.label for f in c.factors], 'cache_entries':len(c.cache)} for c in children]
    return total,summary,list(boundary)


def _direct_oracle(net,base,node,jets,budget):
    """Independent half-edge enumeration, without partitioned children.

    Full direct formula: sum_{X,Y} A(Y) B(X) prod_i H_i(Y_i, X).
    """
    m=net.edges;ring=jets.base
    packet_rows=[]
    for packet in base['packets']:
        real=list(real_packet_slots(packet,base['L']))
        for x,rid in real:
            packet_rows.append((rid,tuple((cid,shift_cauchy_entry(base['L'],node,ring,x,y)[:jets.length])
                                          for y,cid in real)))
    rows=[f for f in net.factors if f.label.startswith(('row:','clause:'))]
    cols=[f for f in net.factors if f.label.startswith(('col:','variable:'))]
    total=jets.zero
    for xbits in range(1<<m):
        cval=1
        for f in cols:
            mask=sum(((xbits>>e)&1)<<i for i,e in enumerate(f.ports))
            cval*=f.table[mask]
        if cval==0:continue
        for ybits in range(1<<m):
            budget.tick()
            rval=cval
            for f in rows:
                mask=sum(((ybits>>e)&1)<<i for i,e in enumerate(f.ports))
                rval*=f.table[mask]
            if rval==0:continue
            prod=jets.elem([[rval]])
            for rid,entries in packet_rows:
                z=jets.zero
                for cid,coeff in entries:
                    if (xbits>>cid)&1:z=jets.add(z,coeff)
                h=z if (ybits>>rid)&1 else jets.sub(jets.one,z)
                prod=jets.mul(prod,h)
                if prod==jets.zero:break
            total=jets.add(total,prod)
    return total


def _serialized_net(net):
    return {'edges':net.edges,'factors':[{'ports':list(f.ports),'table':list(f.table),'label':f.label} for f in net.factors]}


def _deserialize_net(raw):
    if not isinstance(raw,dict) or type(raw.get('edges')) is not int or not 1<=raw['edges']<=6:
        raise ValueError('invalid stored tensor network')
    if not isinstance(raw.get('factors'),list) or len(raw['factors'])>20:
        raise ValueError('invalid factor collection')
    fs=[]
    for f in raw['factors']:
        if not isinstance(f,dict) or set(f)!={'ports','table','label'}:
            raise ValueError('malformed factor')
        if not isinstance(f['label'],str) or len(f['label'])>120:
            raise ValueError('invalid factor label')
        fs.append(Factor(tuple(f['ports']),tuple(f['table']),f['label']))
    return TensorNetwork(raw['edges'],tuple(fs))


def _run(net,base,node,precision,e,length,max_assignments,timeout_s):
    coord=_check_inputs(net,base,node,precision,e,length)
    jets=JetRing(ExtensionRing(precision,first_irreducible(e)),length)
    factors=_build_factors(net,base,node,jets,coord)
    budget=Limits(max_assignments,timeout_s)
    result,children,boundary=_grouped_contract(factors,jets,budget)
    grouped_work=budget.used
    oracle=_direct_oracle(net,base,node,jets,budget)
    if result!=oracle:
        raise ArithmeticError('independent direct Cauchy half-edge oracle mismatch')
    # A second, independent specialization at T=0 checks the count-preserving
    # identity W(0)=I against the original un-deformed Boolean contraction.
    from veritas.research.tensor import brute_contract
    origin=_direct_oracle(net,base,0,jets,budget)
    count=brute_contract(net,max_edges=6)
    if origin[0][0] != count % jets.base.modulus or any(origin[0][1:]):
        raise ArithmeticError('Cauchy origin identity does not match original count')
    return {'result':[[int(x) for x in coeff] for coeff in result],
            'children':children,'boundary':boundary,
            'grouped_assignments':grouped_work,'total_assignments_including_oracle':budget.used,
            'independent_oracle_matches':True, 'origin_count_mod_2p': count % jets.base.modulus}


def make_child_certificate(net:TensorNetwork,base:dict,*,node:int=1,precision:int=8,
                           extension_degree:int=4,jet_length:int=3,
                           mode_certificate:dict|None=None,
                           max_assignments:int=250_000,timeout_s:float=12.0):
    """Construct and independently cross-check finite *implicit* children."""
    if mode_certificate is not None:
        check=check_extension_modes(mode_certificate)
        if not check.get('valid') or mode_certificate['d3_certificate']!=base or \
           any((mode_certificate['node']!=node,mode_certificate['precision']!=precision,
                mode_certificate['extension_degree']!=extension_degree,
                mode_certificate['jet_length']!=jet_length)):
            raise ValueError('v2.9 modes do not match verified D.3 input/parameters')
    out=_run(net,base,node,precision,extension_degree,jet_length,max_assignments,timeout_s)
    return {'schema':'VERITAS_ETH_IMPLICIT_CHILDREN_V30',
            'claim':'FINITE_IMPLICIT_SEPARATOR_REFERENCE_ONLY',
            'network':_serialized_net(net),'d3_certificate':base,
            'node':node,'precision':precision,'extension_degree':extension_degree,
            'jet_length':jet_length,'result':out['result'],
            'children':out['children'],'boundary':out['boundary'],
            'independent_oracle_matches':True,
            'origin_count_mod_2p':out['origin_count_mod_2p'],
            'manuscript_numeric_preconditions':bool(base.get('verification',{}).get('d6_numeric_preconditions_satisfied',False)),
            'scope':{'manuscript_D44_child_tensors':False,
                     'geometric_tile_modes_used':False,
                     'subexponential_runtime_proven':False}}


def check_child_certificate(cert,*,max_assignments=250_000,timeout_s=12.0):
    """Rebuild implicit children and cross-check against independent enumeration."""
    try:
        if not isinstance(cert,dict) or cert.get('schema')!='VERITAS_ETH_IMPLICIT_CHILDREN_V30' or \
           cert.get('claim')!='FINITE_IMPLICIT_SEPARATOR_REFERENCE_ONLY' or \
           cert.get('scope')!={'manuscript_D44_child_tensors':False,
                              'geometric_tile_modes_used':False,
                              'subexponential_runtime_proven':False}:
            raise ValueError('unsupported or overstated research claim')
        net=_deserialize_net(cert['network'])
        out=_run(net,cert['d3_certificate'],cert['node'],cert['precision'],
                 cert['extension_degree'],cert['jet_length'],max_assignments,timeout_s)
        if (out['result']!=cert['result'] or out['children']!=cert['children'] or
            out['boundary']!=cert['boundary'] or cert['independent_oracle_matches'] is not True or
            out['origin_count_mod_2p']!=cert['origin_count_mod_2p'] or
            cert['manuscript_numeric_preconditions'] is not bool(cert['d3_certificate'].get('verification',{}).get('d6_numeric_preconditions_satisfied',False))):
            raise ValueError('certificate result or child metadata differs from independent replay')
        return {'valid':True,'status':'BOUNDED_CHILD_AND_ORACLE_IDENTITY_CHECKED',
                'child_count':len(out['children']), 'boundary_width':len(out['boundary']),
                'jet_length':cert['jet_length'], 'origin_count_mod_2p':out['origin_count_mod_2p'],
                'manuscript_numeric_preconditions':cert['manuscript_numeric_preconditions'], 'claim':cert['claim'],
                'subexponential_runtime_proven':False}
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,ZeroDivisionError,
            ImplicitBudgetExceeded,ArithmeticError) as exc:
        return {'valid':False,'status':'INVALID_FINITE_CHILD_CERTIFICATE','reason':str(exc)}
