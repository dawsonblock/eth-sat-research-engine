"""Explicitly scaled, finite integration of the production recursive traversal.

This is a test/research API, never a source-qualified algorithm. The same visit,
packing, full formal mode sum, sequential child calls, interpolation and Hermite
recovery execute here. The radix, depth stopping rule and provably sufficient
local precision differ from the manuscript. Children need not shrink.
"""
from dataclasses import dataclass
from types import MappingProxyType

from veritas.research.eth_packing_v26.packet_bijection import encode_class_offset
from .executor import _contract
from .packing import construct, Layout, Packet
from .parameters import natural
from .resources import Budget,Limits,ResourceLimit


@dataclass(frozen=True)
class ScaledExperiment:
    a: int = 1
    u: int = 1
    radix: int = 2
    active_depth: int = 1
    column_shift: int = 1
    certified_support: bool = False

    def __post_init__(self):
        if type(self.certified_support) is not bool:
            raise TypeError('certified_support must be a Boolean')
        for value,name in ((self.a,'a'),(self.u,'u'),(self.active_depth,'active depth')):
            natural(value,name,1)
        natural(self.radix,'radix',2)
        natural(self.column_shift,'column shift')
        if self.u>self.a or self.column_shift>=self.radix:
            raise ValueError('invalid finite experiment parameters')

    def description(self):
        return dict(a=self.a,u=self.u,radix=self.radix,active_depth=self.active_depth,
                    column_label_shift=self.column_shift,
                    precision_policy='EXACT_HERMITE_FUNCTIONAL_DENOMINATOR_LOSS',
                    stopping_rule='EXPLICIT_DEPTH_NOT_SOURCE_LEAF_THRESHOLD',
                    full_padded_inventory=True,full_weighted_mode_domain=not self.certified_support,
                    manuscript_packing_bounds_enforced=False,
                    shrinking_children_certified=False)

    def domain(self,network,layout,point,budget):
        if self.certified_support:
            from .certified_modes import DegreeCertifiedDomain
            return DegreeCertifiedDomain(network,layout,point,budget)
        from .modes import Domain
        return Domain(layout,point,budget)

    def layout(self,network,budget):
        layout=construct(network,self.a,network.maximum_degree,budget,
                         r=self.radix,require_bounds=False)
        if not self.column_shift:return layout
        # A fixed alphabet permutation retains class loads and padding. It
        # makes the one-wire fixture cross groups instead of taking only a
        # local kernel term, without omitting any formal zero modes/packets.
        columns={key:tuple((value+self.column_shift)%self.radix for value in word)
                 for key,word in layout.columns.items()}
        buckets={}
        for edge,(row,col) in enumerate(network.edges()):
            buckets.setdefault((layout.rows[row],columns[col]),[]).append(edge)
        occupied={}
        for (row,col),edges in buckets.items():
            for offset,edge in enumerate(edges):
                address=encode_class_offset(row,col,offset,radix=self.radix,
                                            width=self.a,padded_height=layout.padded_height)
                occupied.setdefault((address.pattern,address.packet),[]).append((address.slot,edge))
        packets=tuple(Packet(packet.pattern,packet.index,
                             tuple(sorted(occupied.get((packet.pattern,packet.index),()))))
                      for packet in layout.packets)
        return Layout(layout.a,layout.r,layout.rows,MappingProxyType(columns),packets,
                      layout.padded_height,layout.variance_scaled)


def contract_scaled(network,*,precision,ell=1,experiment=ScaledExperiment(),
                    limits=Limits(),event_sink=None,budget=None):
    """Run finite recursive control flow, with no source/theorem qualification."""
    if type(experiment) is not ScaledExperiment:
        raise TypeError('explicit ScaledExperiment required')
    # The square ensures ceil(s**0.9) covers the input degree. This is a
    # finite admission parameter, not a manuscript size or complexity claim.
    s=max(2,network.wires,precision,ell,network.maximum_degree**2)
    return _contract(network,s=s,precision=precision,ell=ell,limits=limits,
                     event_sink=event_sink,experiment=experiment,budget=budget)


def count_scaled_cnf(formula,*,experiment,ell=1,limits=Limits(),budget=None,event_sink=None):
    """Explicit finite recursion on the shared CNF encoding, never a fallback.

    Precision n+1 makes count recovery unambiguous. The finite admission size
    and extension degree are selected by contract_scaled, not by the source
    encoding's asymptotic parameters. One budget covers encoding and recursion.
    The inner_route, tensor_status and full_formal_domain_enumerated fields
    distinguish certified support from full enumeration. This research route
    has no source/refinement/complexity qualification.
    """
    from .cnf import Formula,encode
    from .model import ClauseTensor,EqualityTensor
    if type(formula) is not Formula:raise TypeError('manuscript Formula required')
    if type(experiment) is not ScaledExperiment:raise TypeError('explicit ScaledExperiment required')
    natural(ell,'jet length',1)
    budget=Budget(limits) if budget is None else budget
    flags=dict(source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
               experimental_scaled=True)
    try:
        formula=formula.normalize(budget)
        budget.bits(formula.n+1,'exact count precision')
        if not formula.clauses or () in formula.clauses:
            value=0 if formula.clauses else 1 << formula.n
            return dict(status='PASS_EXACT_COUNT',count=value,route='EXPERIMENTAL_TRIVIAL_CNF',
                        experimental_scaling=experiment.description(),ledger=budget.report(),**flags)
        encoded=encode(formula,budget)
        if event_sink is not None:
            vertices=[]
            for v in encoded.network.vertices:
                budget.tick()
                if type(v.tensor) is ClauseTensor:
                    tensor=dict(kind='clause',positive=list(v.tensor.positive),creation_precision=v.tensor.creation_precision)
                elif type(v.tensor) is EqualityTensor:
                    tensor=dict(kind='equality',arity=v.tensor.arity,creation_precision=v.tensor.creation_precision)
                else:raise TypeError('unexpected shared CNF tensor type')
                vertices.append(dict(side=v.side,identity=v.identity,ports=list(v.ports),tensor=tensor))
            budget.items(4*encoded.network.wires+6*len(vertices),'encoding event')
            event_sink(dict(kind='encoding',n=formula.n,clauses=[list(c) for c in formula.clauses],
                            wires=encoded.network.wires,unused_variables=encoded.unused,
                            precision=encoded.precision,vertices=vertices))
        receipt=contract_scaled(encoded.network,precision=encoded.precision,ell=ell,
            experiment=experiment,limits=limits,budget=budget,event_sink=event_sink)
        # Nontrivial normalized clauses have literals, so encode produces at
        # least two wires. A leaf or any other receipt is never promoted.
        expected='PASS_EXPERIMENTAL_CERTIFIED_RECURSION' if experiment.certified_support else 'PASS_EXPERIMENTAL_SCALED_RECURSION'
        if receipt['status']!=expected:return receipt
        if any(any(row) for row in receipt['result'][1:]):
            raise ArithmeticError('CNF count acquired a nonconstant V coefficient')
        budget.tick();budget.bits(formula.n+1,'exact count recovery')
        value=(receipt['result'][0][0] << encoded.unused) % (1 << encoded.precision)
        if value>1 << formula.n:raise ArithmeticError('exact count outside assignment range')
        return dict(status='PASS_EXACT_COUNT',count=value,route='EXPERIMENTAL_SCALED_CNF',
                    inner_route=receipt['route'],tensor_status=receipt['status'],
                    encoding='CLAUSE_EQUALITY_TREE_SUBDIVISION',encoded_wires=encoded.network.wires,
                    precision=encoded.precision,ell=ell,unused_variables=encoded.unused,
                    extension_degree=receipt['parameters']['extension_degree'],
                    finite_parameters=receipt['parameters'],experimental_scaling=experiment.description(),
                    full_formal_domain_enumerated=not experiment.certified_support,
                    budget_policy='SHARED_ENCODING_AND_CONTRACTION',ledger=budget.report(),**flags)
    except ResourceLimit as exc:
        return dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),route='EXPERIMENTAL_SCALED_CNF',
                    experimental_scaling=experiment.description(),ledger=budget.report(),**flags)
