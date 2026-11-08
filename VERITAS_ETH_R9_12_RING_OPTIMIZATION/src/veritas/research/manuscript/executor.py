"""Depth-first executor for the quantitative manuscript construction.

The paper schedule, source leaf rule, full padded packing, full weighted mode
domain, implicit packet entries and tapered recovery are connected here.
Operational limits may stop execution without a result; they never replace a
mathematical parameter. No formal executable or complexity qualification is
inferred from this implementation.
"""
from veritas.research.eth_arithmetic.gf2 import is_irreducible
from .parameters import Schedule,natural
from .resources import Budget,Limits,ResourceLimit
from .ring import Ring,choose_polynomial
from .model import Network,direct,OriginalTensor,DenseTensor,EqualityTensor,ClauseTensor
from .packing import construct
from .cauchy import Point
from .modes import Domain
from .children import point_contraction
from .recovery import recover


def contract(network,*,s,precision,ell=1,size_constant=1,defining_polynomial=None,
             limits=Limits(),event_sink=None,budget=None):
    return _contract(network,s=s,precision=precision,ell=ell,size_constant=size_constant,
        defining_polynomial=defining_polynomial,limits=limits,event_sink=event_sink,budget=budget)


def _contract(network,*,s,precision,ell=1,size_constant=1,defining_polynomial=None,
              limits=Limits(),event_sink=None,budget=None,experiment=None):
    """Shared traversal. Only contract_scaled supplies an explicit experiment."""
    budget=Budget(limits) if budget is None else budget
    try:
        if type(network) is not Network:raise TypeError('manuscript Network required')
        schedule=Schedule(s,size_constant)
        natural(precision,'root precision',1);natural(ell,'jet length',1)
        if max(network.wires,precision,ell)>size_constant*s:raise ValueError('root bounds exceed C*s')
        if network.maximum_degree>schedule.delta:raise ValueError('network exceeds source degree bound')
        if any(v.tensor.creation_precision!=precision for v in network.vertices):
            raise ValueError('original entries must be tagged with root creation precision')
        if any(type(v.tensor) not in (OriginalTensor,DenseTensor,EqualityTensor,ClauseTensor) for v in network.vertices):
            raise ValueError('root entries require an explicit base-ring tensor description')
        budget.items(schedule.extension_degree*ell,'source coefficient vector')
        budget.bits(precision,'root coefficient')
        f=choose_polynomial(schedule.extension_degree,budget) if defining_polynomial is None else defining_polynomial
        if type(f) is not int or f.bit_length()!=schedule.extension_degree+1 or not is_irreducible(f):
            raise ValueError('root requires irreducible polynomial of degree 4*ceil(log2(s))')
        recursive_regime=schedule.admits_recursive_regime() if experiment is None else True

        def emit(record):
            if event_sink is not None:event_sink(record)

        def visit(graph,p,depth):
            budget.tick();budget.calls+=1;budget.max_depth=max(budget.max_depth,depth)
            if experiment is None and graph.wires*(8**depth)>size_constant*s:raise ArithmeticError('recursive size invariant failed')
            if experiment is None and graph.maximum_degree>schedule.delta:raise ArithmeticError('recursive degree invariant failed')
            ring=Ring(p,f,ell,budget)
            leaf=(graph.wires<=schedule.leaf_wires or not recursive_regime) if experiment is None else (
                graph.wires==0 or depth>=experiment.active_depth)
            if leaf:
                answer=direct(graph,ring)
                emit(dict(kind='leaf',depth=depth,wires=graph.wires,precision=p,
                          reason=(('EMPTY_NETWORK' if graph.wires==0 else 'EXPERIMENT_DEPTH_LIMIT') if experiment is not None else
                                  'SOURCE_LEAF' if graph.wires<=schedule.leaf_wires else 'FINITE_SIZE_RANGE'),result=answer))
                return answer
            a,u=schedule.at(depth) if experiment is None else (experiment.a,experiment.u)
            if experiment is None and not schedule.active_preconditions(graph.wires,depth):raise ArithmeticError('active source preconditions failed')
            layout=construct(graph,a,schedule.delta,budget) if experiment is None else experiment.layout(graph,budget)
            record=dict(kind='active',depth=depth,wires=graph.wires,precision=p,a=a,u=u,
                        padded_packets=len(layout.packets),leaf_threshold=schedule.leaf_wires,
                        experiment_scaled=experiment is not None)
            if experiment is not None and event_sink is not None:
                record.update(defining_polynomial=f,radix=layout.r,
                    packets=[dict(pattern=packet.pattern,index=packet.index,slots=packet.slots)
                             for packet in layout.packets])
            if experiment is not None and experiment.certified_support and event_sink is not None:
                record.update(padded_height=layout.padded_height,variance_scaled=layout.variance_scaled,
                    labels=[dict(side=v.side,identity=v.identity,word=layout.labels(v.side)[v.identity]) for v in graph.vertices])
            emit(record)
            def point_value(node,zeta,node_ring):
                budget.points+=1
                point=Point(layout.L,node.t,zeta,node.precision,f,ell)
                domain=Domain(layout,point,budget) if experiment is None else experiment.domain(graph,layout,point,budget)
                value=point_contraction(graph,layout,domain,node_ring,
                    lambda descendant,child_p:visit(descendant,child_p,depth+1),delta=schedule.delta,
                    require_bounds=experiment is None)
                record=dict(kind='point',depth=depth,wires=graph.wires,t=node.t,
                            multiplicity=node.multiplicity,precision=node.precision,zeta=zeta,result=value)
                if experiment is not None and experiment.certified_support:
                    record['zero_certificate']=domain.certificate()
                emit(record)
                return value
            answer=recover(graph.wires,a,u,ring,point_value,
                           experimental_precision=experiment is not None)
            emit(dict(kind='recovered',depth=depth,wires=graph.wires,result=answer))
            return answer

        result=visit(network,precision,0)
        if any(any(row[1:]) for row in result):raise ArithmeticError('root contraction left the base coefficient subring')
        prefix='EXPERIMENTAL_CERTIFIED' if experiment is not None and experiment.certified_support else 'EXPERIMENTAL_SCALED'
        return dict(status=('PASS_MANUSCRIPT_CONSTRUCTION_EXECUTION' if experiment is None else
                            ('PASS_'+prefix+'_RECURSION' if network.wires else 'PASS_'+prefix+'_LEAF')),result=result,
                    experimental_scaling=None if experiment is None else experiment.description(),
                    route=((prefix+'_RECURSION' if network.wires else prefix+'_DIRECT_LEAF') if experiment is not None else
                           'SOURCE_RECURSION' if recursive_regime and network.wires>schedule.leaf_wires else 'SOURCE_DIRECT_RANGE'),
                    parameters=dict(s=s,C=size_constant,lambda_value=schedule.lam,
                                    extension_degree=schedule.extension_degree,leaf_threshold=schedule.leaf_wires,
                                    degree_limit=schedule.delta),ledger=budget.report(),
                    source_qualified=False,executable_refinement_proven=False,complexity_proven=False)
    except ResourceLimit as exc:
        return dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),
                    source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
                    experimental_scaling=None if experiment is None else experiment.description())
