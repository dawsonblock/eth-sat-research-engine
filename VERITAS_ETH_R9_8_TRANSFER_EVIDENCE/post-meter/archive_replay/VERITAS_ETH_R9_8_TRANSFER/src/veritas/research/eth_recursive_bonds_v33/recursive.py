"""v3.3 finite exact recursive mode-bond contraction with checked source replay.

The recursion is an exact sum-product algorithm over sparse mode-index factors.
It decomposes disconnected components, conditions on selected mode bonds,
reuses identical residual subproblems, and multiplies component results.
There is no manuscript D.4.4 packet-tensor construction or M/8 theorem here.
"""
from __future__ import annotations
from collections import defaultdict
from time import monotonic
from veritas.research.eth_mode_bonds_v32.bonds import (
    _group_tensors, _contract, WorkMeter, BondBudgetExceeded)
from veritas.research.eth_modes_v31.jet_tiles import check_jet_tile_modes, _deserialize_net
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.jets import JetRing
from veritas.research.eth_recursion_v30.implicit_children import (
    _check_inputs, make_bipartite_edges, _direct_oracle, Limits)

SCHEMA='VERITAS_ETH_RECURSIVE_MODE_BONDS_V33'
CLAIM='FINITE_EXACT_RECURSIVE_MODE_BOND_SUM_PRODUCT_ONLY'
SCOPE={
    'exact_recursive_sparse_sum_product':True,
    'disconnected_component_factorization':True,
    'separator_conditioning_and_memoization':True,
    'independent_v32_and_half_edge_oracles':True,
    'manuscript_recursive_packet_tensors':False,
    'manuscript_m_over_8_guarantee':False,
    'subexponential_runtime_proven':False,
}
class RecursiveBudgetExceeded(RuntimeError):
    pass

class RecursiveContractor:
    def __init__(self,jr,*,max_work=150000,max_cache=10000,max_depth=64,timeout_s=10):
        if type(max_work) is not int or not 1 <= max_work <= 1000000:
            raise ValueError('max_work out of range')
        if type(max_cache) is not int or not 1<=max_cache<=100000:
            raise ValueError('max_cache out of range')
        if type(max_depth) is not int or not 1<=max_depth<=128:
            raise ValueError('max_depth out of range')
        if type(timeout_s) not in (int,float) or not 0<timeout_s<=30:
            raise ValueError('timeout_s out of range')
        self.jr=jr;self.max_work=max_work;self.max_cache=max_cache;self.max_depth=max_depth
        self.deadline=monotonic()+timeout_s
        self.work=0;self.calls=0;self.cache_hits=0;self.branches=0;self.splits=0
        self.peak_depth=0;self.peak_live_entries=0;self.cache={};self.trace=[]

    def tick(self,n=1):
        self.work+=n
        if self.work>self.max_work or monotonic()>self.deadline:
            raise RecursiveBudgetExceeded('recursive work/time budget exhausted')

    def _components(self,factors):
        # Union factors sharing an open exponent bond; singleton factors form components.
        owner=defaultdict(list)
        for i,f in enumerate(factors):
            for mode in f[0]:owner[mode].append(i)
        adj=[set() for _ in factors]
        for inds in owner.values():
            for i in inds:
                adj[i].update(inds)
        seen=set();out=[]
        for seed in range(len(factors)):
            if seed in seen:continue
            stack=[seed];seen.add(seed);c=[]
            while stack:
                i=stack.pop();c.append(factors[i])
                for j in sorted(adj[i]):
                    if j not in seen:seen.add(j);stack.append(j)
            out.append(tuple(c))
        return tuple(out)

    def _fingerprint(self,factors):
        # Canonical exact state, not a probabilistic or truncated hash.
        return tuple(sorted(((m,tuple(sorted(t.items()))) for m,t in factors),key=repr))

    def _contract(self,factors,depth):
        self.tick();self.calls+=1
        if depth>self.max_depth:raise RecursiveBudgetExceeded('max recursion depth exceeded')
        self.peak_depth=max(self.peak_depth,depth)
        live=sum(len(t) for _,t in factors)
        self.peak_live_entries=max(self.peak_live_entries,live)
        if any(not t for _,t in factors):return self.jr.zero
        if not factors:return self.jr.one
        # Product of scalar factors, without treating their multiplicity as bond choices.
        scalars=[t.get((),self.jr.zero) for m,t in factors if not m]
        outer=self.jr.one
        for v in scalars:
            self.tick();outer=self.jr.mul(outer,v)
        if outer==self.jr.zero:return outer
        factors=tuple((m,t) for m,t in factors if m)
        if not factors:return outer
        key=self._fingerprint(factors)
        if key in self.cache:
            self.cache_hits+=1
            return self.jr.mul(outer,self.cache[key])
        parts=self._components(factors)
        if len(parts)>1:
            self.splits+=1
            val=self.jr.one
            for component in parts:
                val=self.jr.mul(val,self._contract(component,depth+1))
                if val==self.jr.zero:break
        else:
            # Exact intersection of nonzero supports provides a sound, finite
            # domain for each bond, even when a mode has one endpoint in a group.
            indices=defaultdict(list)
            for fi,(m,t) in enumerate(factors):
                for pos,mode in enumerate(m):
                    domain={entry[pos] for entry in t}
                    indices[mode].append((fi,pos,domain))
            choices=[]
            for mode,occ in indices.items():
                allowed=set.intersection(*(o[2] for o in occ))
                if not allowed:
                    val=self.jr.zero;break
                estimated=sum(len(factors[fi][1]) for fi,_,_ in occ)*len(allowed)
                choices.append((estimated,len(allowed),mode,tuple(sorted(allowed))))
            else:
                _,_,pivot,domain=min(choices)
                self.trace.append({'depth':depth,'remaining_bonds':len(indices),
                                   'pivot':pivot,'domain_size':len(domain),
                                   'factor_count':len(factors)})
                if len(self.trace)>self.max_work:
                    raise RecursiveBudgetExceeded('trace budget exceeded')
                val=self.jr.zero
                for exponent in domain:
                    self.tick();self.branches+=1
                    residual=[]
                    for modes,table in factors:
                        if pivot not in modes:
                            residual.append((modes,table));continue
                        pos=modes.index(pivot);new_modes=modes[:pos]+modes[pos+1:]
                        sliced={}
                        for k,v in table.items():
                            self.tick()
                            if k[pos]==exponent:
                                sliced[k[:pos]+k[pos+1:]]=v
                        if not sliced:break
                        residual.append((new_modes,sliced))
                    else:
                        term=self._contract(tuple(residual),depth+1)
                        val=self.jr.add(val,term)
        if len(self.cache)>=self.max_cache:
            raise RecursiveBudgetExceeded('recursive cache capacity exceeded')
        self.cache[key]=val
        return self.jr.mul(outer,val)

    def run(self,children):
        factors=tuple((tuple(child['modes']),dict(child['table'])) for child in children)
        result=self._contract(factors,0)
        return result,{'calls':self.calls,'branches':self.branches,
            'component_splits':self.splits,'cache_hits':self.cache_hits,
            'peak_depth':self.peak_depth,'work_units':self.work,
            'peak_live_sparse_entries':self.peak_live_entries,
            'cache_entries':len(self.cache),'trace':self.trace}


def construct_recursive_certificate(net,mode_certificate,*,max_work=150000,
                                    max_entries=3000,max_cache=10000,
                                    max_depth=64,timeout_s=10):
    if not check_jet_tile_modes(mode_certificate).get('valid'):
        raise ValueError('unverified geometric mode certificate')
    d3=mode_certificate['d3_certificate'];t=mode_certificate['node']
    p=mode_certificate['precision'];e=mode_certificate['extension_degree']
    length=mode_certificate['jet_length']
    _check_inputs(net,d3,t,p,e,length)
    if make_bipartite_edges(net)!=d3['edges']:
        raise ValueError('network and packet certificate disagree')
    if type(max_entries) is not int or not 1<=max_entries<=10000:
        raise ValueError('max_entries out of range')
    jr=JetRing(ExtensionRing(p,first_irreducible(e)),length)
    meter=WorkMeter(max_work,timeout_s)
    children=_group_tensors(net,mode_certificate,jr,meter,max_entries)
    rec=RecursiveContractor(jr,max_work=max_work,max_cache=max_cache,
                            max_depth=max_depth,timeout_s=timeout_s)
    total,stats=rec.run(children)
    # Algorithmically independent (different elimination strategy) finite
    # sparse contraction plus 4**M half-edge enumeration.  No theorem claim.
    independent=_contract(children,jr,WorkMeter(max_work,timeout_s),max_entries)
    if total!=independent:raise ArithmeticError('recursive value differs from v3.2 elimination')
    oracle_meter=Limits(max_assignments=min(max_work,2_000_000),timeout_s=min(20,timeout_s))
    oracle=_direct_oracle(net,d3,t,jr,oracle_meter)
    if total!=oracle:raise ArithmeticError('recursive value differs from direct half-edge oracle')
    return {'schema':SCHEMA,'claim':CLAIM,'scope':dict(SCOPE),
       'network':{'edges':net.edges,'factors':[{'ports':list(f.ports),
          'table':list(f.table),'label':f.label} for f in net.factors]},
       'mode_certificate':mode_certificate,
       'result':[list(x) for x in total],
       'child_descriptions':[{'group':c['group'],'mode_indices':list(c['modes']),
          'owned_halfbits':list(c['owned_halfbits']),
          'entries':[[list(k),[list(x) for x in v]] for k,v in sorted(c['table'].items())]}
          for c in children],
       'stats':{'group_tensor_work':meter.used,'oracle_work':oracle_meter.used,**stats},
       'three_way_exact_agreement':True}


def check_recursive_certificate(cert,*,max_work=150000,max_entries=3000,
                                max_cache=10000,max_depth=64,timeout_s=10):
    try:
        if not isinstance(cert,dict) or cert.get('schema')!=SCHEMA or cert.get('claim')!=CLAIM or cert.get('scope')!=SCOPE:
            raise ValueError('unsupported schema/claim/scope')
        net=_deserialize_net(cert['network'])
        expected=construct_recursive_certificate(net,cert['mode_certificate'],
            max_work=max_work,max_entries=max_entries,max_cache=max_cache,
            max_depth=max_depth,timeout_s=timeout_s)
        if cert!=expected:raise ValueError('source replay differs from certificate')
        return {'valid':True,'status':'FINITE_RECURSIVE_MODE_BOND_CHECKED',
                'manuscript_m_over_8_guarantee':False,'subexponential_runtime_proven':False}
    except (ValueError,KeyError,TypeError,IndexError,OverflowError,ArithmeticError,
            ZeroDivisionError,RuntimeError,TimeoutError) as exc:
        return {'valid':False,'status':'INVALID_V33_CERTIFICATE','reason':str(exc)}
