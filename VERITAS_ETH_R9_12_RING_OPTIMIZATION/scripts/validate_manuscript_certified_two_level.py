"""Two-level finite recursion with independently checked zero-family omission.

This is a separate one-wire experiment, NOT the unpruned manuscript executor.
Only beta=0 and beta=e_0 survive the checked slot-zero/two-group geometry.
All other formal betas are covered by explicit, value-independent zero proofs.
Production packing, packet entries, child construction, interpolation and
recovery are retained; the independent replay imports no such constructors.
"""
import argparse
import json
from math import comb
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if '--installed' not in sys.argv:sys.path.insert(0,str(ROOT/'src'))
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.manuscript.cauchy import Point
from veritas.research.manuscript.children import point_contraction
from veritas.research.manuscript.experimental import ScaledExperiment
from veritas.research.manuscript.finite_replay import ReplayError
from veritas.research.manuscript.model import DenseTensor,Network,Vertex,direct
from veritas.research.manuscript.modes import Domain
from veritas.research.manuscript.recovery import recover
from veritas.research.manuscript.resources import Budget,Limits,ResourceLimit
from veritas.research.manuscript.ring import Ring


class ZeroCertificateError(ValueError):pass


PACKETS=[{'pattern':[[0,0]],'index':0,'slots':[]},
         {'pattern':[[0,1]],'index':0,'slots':[[0,0]]},
         {'pattern':[[0,1]],'index':1,'slots':[]},
         {'pattern':[[1,1]],'index':0,'slots':[]}]
FAMILIES=['NONZERO_OTHER_CHANNEL_HAS_EMPTY_SOURCE',
          'POSITIVE_GEOMETRIC_EXPONENT_AT_SLOT_ZERO',
          'TARGET_AFFINE_DEGREE_EXCEEDS_ONE']


def _packet_data(layout):
    return [dict(pattern=[list(pair) for pair in p.pattern],index=p.index,
                 slots=[list(slot) for slot in p.slots]) for p in layout.packets]


class CertifiedOneWireDomain(Domain):
    """Explicitly omit only the three fully covered, proven-zero families."""
    def __init__(self,network,layout,point,budget):
        if (network.wires!=1 or layout.a!=1 or layout.r!=2 or layout.padded_height!=2 or
            _packet_data(layout)!=PACKETS or
            any(word!=(0,) for word in layout.rows.values()) or
            any(word!=(1,) for word in layout.columns.values()) or
            set(layout.rows)!={v.identity for v in network.vertices if v.side=='row'} or
            set(layout.columns)!={v.identity for v in network.vertices if v.side=='column'} or
            (point.L,point.f,point.ell)!=(2,19,2) or point.t not in (-1,1) or
            point.coordinate!=0 or point.precision<2):
            raise ZeroCertificateError('one-wire slot-zero certificate preconditions fail')
        super().__init__(layout,point,budget)
        if self.per_weight!=4 or self.size!=4*(point.precision-1):
            raise ZeroCertificateError('complete formal domain does not match certificate')
        # This is an exact finite count, not a substitute for checking zeros.
        self.full_count=self.count()

    def certificate(self):
        return dict(schema='ONE_WIRE_ZERO_FAMILIES_V1',precision=self.point.precision,
                    formal_channels_per_weight=4,formal_mode_count=self.size,
                    formal_tuple_count=self.full_count,retained_tuple_count=2,
                    certified_zero_tuple_count=self.full_count-2,families=FAMILIES)

    def tuples(self):
        # Coverage proof: any nonzero channel other than occupied tile zero
        # has an empty source; any positive geometric exponent has source
        # j**b=0**b=0; power >=2 of the remaining mode exceeds one affine row.
        # No production constructor is called by the separate replay proof.
        for power in (0,1):
            self.budget.tick();self.budget.tuples+=1
            yield (power,)+(0,)*(self.size-1)


def run(network,*,limits=Limits(max_work=200_000_000,max_seconds=180)):
    budget=Budget(limits);events=[];configuration=ScaledExperiment()
    flags=dict(source_qualified=False,executable_refinement_proven=False,complexity_proven=False)
    try:
        if network.wires!=1:raise ZeroCertificateError('experiment requires exactly one wire')
        if any(v.tensor.creation_precision!=2 for v in network.vertices):
            raise ZeroCertificateError('root creation precision must be two')
        def visit(graph,p,depth):
            budget.tick();budget.calls+=1;budget.max_depth=max(budget.max_depth,depth)
            ring=Ring(p,19,2,budget)
            if graph.wires!=1:raise ZeroCertificateError('unexpected child topology')
            if depth==2:
                value=direct(graph,ring)
                events.append(dict(kind='leaf',depth=depth,precision=p,wires=1,result=value))
                return value
            layout=configuration.layout(graph,budget)
            events.append(dict(kind='active',depth=depth,precision=p,wires=1,a=1,u=1,radix=2,
                               defining_polynomial=19,packets=_packet_data(layout),
                               labels=[dict(vertex_index=i,side=v.side,word=list(layout.labels(v.side)[v.identity]))
                                       for i,v in enumerate(graph.vertices)]))
            def point_value(node,z,node_ring):
                budget.points+=1
                point=Point(2,node.t,z,node.precision,19,2)
                domain=CertifiedOneWireDomain(graph,layout,point,budget)
                value=point_contraction(graph,layout,domain,node_ring,
                    lambda child,child_p:visit(child,child_p,depth+1),require_bounds=False)
                events.append(dict(kind='point',depth=depth,precision=node.precision,
                    t=node.t,multiplicity=node.multiplicity,zeta=z,result=value,
                    zero_certificate=domain.certificate()))
                return value
            value=recover(1,1,1,ring,point_value,experimental_precision=True)
            events.append(dict(kind='recovered',depth=depth,precision=p,wires=1,result=value))
            return value
        answer=visit(network,2,0)
        if any(any(row[1:]) for row in answer):
            raise ZeroCertificateError('root result left the base coefficient subring')
        report=dict(status='PASS_EXPERIMENTAL_CERTIFIED_ZERO_TWO_LEVEL',result=answer,
                    route='EXPERIMENTAL_CERTIFIED_ZERO_FAMILIES',ledger=budget.report(),
                    full_formal_domain_enumerated=False,zero_families_certified=True,
                    active_levels=2,shrinking_children_certified=False,**flags)
    except ResourceLimit as exc:
        report=dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),**flags)
    except ZeroCertificateError as exc:
        report=dict(status='REFUSED_ZERO_CERTIFICATE',reason=str(exc),ledger=budget.report(),**flags)
    return report,events


def produce(fixture=None):
    if fixture is None:fixture=dict(precision=2,ell=2,row=[[1,2],[3,1]],column=[[2,1],[1,3]])
    vertices=[]
    for side in ('row','column'):
        vertices.append(Vertex(side,0,(0,),DenseTensor(1,2,tuple(map(tuple,fixture[side])))))
        if side+'_scalar' in fixture:
            vertices.append(Vertex(side,1,(),DenseTensor(0,2,(tuple(fixture[side+'_scalar']),))))
    network=Network(1,tuple(vertices))
    report,events=run(network)
    return dict(schema='VERITAS_CERTIFIED_ZERO_TWO_LEVEL_V1',fixture=fixture,report=report,events=events)


# Everything below is the independent replay. It uses only the older
# ExtensionRing and ordinary integer arithmetic, never production evaluators.
def _need(condition,message):
    if not condition:raise ReplayError(message)


def _formal_count(p):
    """Colored partitions by binomial convolution, not per-channel DP."""
    counts=[1]+[0]*(p-1)
    for weight in range(1,p):
        next_counts=[0]*p
        for total,value in enumerate(counts):
            for copies in range((p-1-total)//weight+1):
                next_counts[total+copies*weight]+=value*comb(copies+3,3)
        counts=next_counts
    return sum(counts)


def _jet_mul(a,b,ring):
    return (ring.mul(a[0],b[0]),ring.add(ring.mul(a[0],b[1]),ring.mul(a[1],b[0])))


def _canonical(value,p):
    _need(isinstance(value,(tuple,list)) and len(value)==2,'bad jet shape')
    _need(all(isinstance(row,(tuple,list)) and len(row)==4 and
              all(type(c) is int and 0<=c<2**p for c in row) for row in value),
          'noncanonical replay value')
    return tuple(tuple(row) for row in value)


def _exact(graph,p):
    ring=ExtensionRing(p,19);total=(ring.zero,ring.zero)
    for bit in (0,1):
        term=(ring.one,ring.zero)
        for vertex in graph:
            term=_jet_mul(term,vertex['table'][bit if vertex['arity'] else 0],ring)
        total=tuple(ring.add(a,b) for a,b in zip(total,term))
    return total


def _kernel(t,z,ring):
    # W_00(T)=-(T+2)(T+1)(T-1)/2. Expand after T=t+4z
    # in integer coefficients, independently of production factor cancellation.
    # The four shifted coefficients are integral for the two odd nodes.
    coefficients=((-t**3-2*t*t+t+2)//2, -6*t*t-8*t+2, -24*t-16, -32)
    value=ring.zero
    for c in reversed(coefficients):value=ring.add(ring.mul(value,z),ring.elem([c]))
    return value


def _point_exact(graph,p,kernel):
    ring=ExtensionRing(p,19);total=(ring.zero,ring.zero)
    for y in (0,1):
        for x in (0,1):
            term=(ring.one,ring.zero)
            for vertex in graph:
                bit=y if vertex['side']=='row' else x
                term=_jet_mul(term,vertex['table'][bit if vertex['arity'] else 0],ring)
            linear=kernel if x else ring.zero
            factor=linear if y else ring.sub(ring.one,linear)
            term=tuple(ring.mul(c,factor) for c in term)
            total=tuple(ring.add(a,b) for a,b in zip(total,term))
    return total


def _child(graph,p,kernel,beta,group):
    ring=ExtensionRing(p,19);one=(ring.one,ring.zero);zero=(ring.zero,ring.zero)
    # Copy the exact canonical integers of inherited tensors separately; do
    # not fold scalar factors modulo p and then lift that product later.
    inherited=[dict(side='row',arity=v['arity'],table=v['table'])
               for v in graph if v['side']==('row' if group==0 else 'column')]
    if group==0:
        table=(one,zero) if beta==0 else ((ring.neg(kernel),ring.zero),(kernel,ring.zero))
    else:table=(one,one) if beta==0 else (zero,one)
    for packet in range(4):
        inherited.append(dict(side='column',arity=int(packet==1),
                              table=table if packet==1 else (one,)))
    return inherited


def replay(certificate):
    _need(certificate.get('schema')=='VERITAS_CERTIFIED_ZERO_TWO_LEVEL_V1','unknown certificate schema')
    fixture=certificate['fixture'];report=certificate['report'];events=certificate['events']
    _need(isinstance(fixture,dict) and {'precision','ell','row','column'}<=set(fixture)<=
          {'precision','ell','row','column','row_scalar','column_scalar'} and
          type(fixture['precision']) is int and fixture['precision']==2 and
          type(fixture['ell']) is int and fixture['ell']==2,'unsupported fixture')
    for side in ('row','column'):
        _need(isinstance(fixture[side],(tuple,list)) and len(fixture[side])==2 and
              all(isinstance(row,(tuple,list)) and len(row)==2 and
                  all(type(c) is int and 0<=c<4 for c in row) for row in fixture[side]),
              'invalid canonical fixture entries')
        if side+'_scalar' in fixture:
            scalar=fixture[side+'_scalar']
            _need(isinstance(scalar,(tuple,list)) and len(scalar)==2 and
                  all(type(c) is int and 0<=c<4 for c in scalar),'invalid scalar entries')
    _need(report['status']=='PASS_EXPERIMENTAL_CERTIFIED_ZERO_TWO_LEVEL' and
          report['route']=='EXPERIMENTAL_CERTIFIED_ZERO_FAMILIES','not a completed certified-zero experiment')
    for flag in ('source_qualified','executable_refinement_proven','complexity_proven',
                 'full_formal_domain_enumerated','shrinking_children_certified'):
        _need(report.get(flag) is False,'unsupported qualification or enumeration claim')
    _need(report.get('zero_families_certified') is True and report.get('active_levels')==2,'bad experiment policy')
    _need(isinstance(events,list) and len(events)==1354,'incomplete or extra event stream')
    graph=[]
    for side in ('row','column'):
        graph.append(dict(side=side,arity=1,table=tuple(tuple((c,0,0,0) for c in row)
                                                       for row in fixture[side])))
        if side+'_scalar' in fixture:
            graph.append(dict(side=side,arity=0,
                              table=(tuple((c,0,0,0) for c in fixture[side+'_scalar']),)))
    # Independent literal geometry and coverage classes: do not reuse the
    # producer's PACKETS/FAMILIES objects when checking its certificate.
    expected_packets=[dict(pattern=[[0,0]],index=0,slots=[]),
                      dict(pattern=[[0,1]],index=0,slots=[[0,0]]),
                      dict(pattern=[[0,1]],index=1,slots=[]),
                      dict(pattern=[[1,1]],index=0,slots=[])]
    expected_families=['NONZERO_OTHER_CHANNEL_HAS_EMPTY_SOURCE',
                       'POSITIVE_GEOMETRIC_EXPONENT_AT_SLOT_ZERO',
                       'TARGET_AFFINE_DEGREE_EXCEEDS_ONE']
    cursor=0;calls=points=leaves=active=covered=0
    def take(kind):
        nonlocal cursor
        _need(cursor<len(events),'truncated replay')
        event=events[cursor];cursor+=1
        _need(event.get('kind')==kind,'unexpected event order')
        keys={'leaf':{'kind','depth','precision','wires','result'},
              'active':{'kind','depth','precision','wires','a','u','radix','defining_polynomial','packets','labels'},
              'point':{'kind','depth','precision','t','multiplicity','zeta','result','zero_certificate'},
              'recovered':{'kind','depth','precision','wires','result'}}
        _need(set(event)==keys[kind],'unexpected event fields')
        _need(all(type(event[key]) is int for key in ('depth','precision')),
              'non-integer event metadata')
        return event
    def visit(graph,p,depth):
        nonlocal calls,points,leaves,active,covered
        calls+=1
        if depth==2:
            event=take('leaf');leaves+=1
            _need(event['depth']==depth and event['precision']==p and event['wires']==1,'bad leaf metadata')
            _need(_canonical(event['result'],p)==_exact(graph,p),'independent leaf mismatch')
            return
        event=take('active');active+=1
        expected=dict(kind='active',depth=depth,precision=p,wires=1,a=1,u=1,radix=2,
                      defining_polynomial=19,packets=expected_packets,
                      labels=[dict(vertex_index=i,side=v['side'],word=[0 if v['side']=='row' else 1])
                              for i,v in enumerate(graph)])
        _need(event==expected,'active geometry/preconditions mismatch')
        for t in (-1,1):
            for index in range(4):
                q=p+7;ring=ExtensionRing(q,19);z=tuple((index>>j)&1 for j in range(4))
                kernel=_kernel(t,z,ring)
                for beta in (0,1):
                    for group in (0,1):visit(_child(graph,q,kernel,beta,group),q,depth+1)
                point=take('point');points+=1
                count=_formal_count(q);covered+=count-2
                _need(point['depth']==depth and point['precision']==q and point['t']==t and
                      point['multiplicity']==3 and tuple(point['zeta'])==z,'bad point metadata')
                expected_cert=dict(schema='ONE_WIRE_ZERO_FAMILIES_V1',precision=q,
                    formal_channels_per_weight=4,formal_mode_count=4*(q-1),formal_tuple_count=count,
                    retained_tuple_count=2,certified_zero_tuple_count=count-2,families=expected_families)
                _need(point['zero_certificate']==expected_cert,'zero-family coverage mismatch')
                _need(_canonical(point['result'],q)==_point_exact(graph,q,kernel),'independent point mismatch')
        recovered=take('recovered')
        _need(recovered['depth']==depth and recovered['precision']==p and recovered['wires']==1,'bad recovery metadata')
        _need(_canonical(recovered['result'],p)==_exact(graph,p),'independent recovered node mismatch')
    visit(graph,2,0)
    _need(cursor==len(events),'extra transcript events')
    _need(_canonical(report['result'],2)==_exact(graph,2),'root mismatch')
    ledger=report['ledger']
    _need((ledger['calls'],ledger['interpolation_points'],ledger['exponent_tuples'],ledger['maximum_depth'])==
          (1057,264,528,2),'execution counts mismatch')
    _need((calls,points,leaves,active)==(1057,264,1024,33),'independent tree counts mismatch')
    integer=[sum(fixture['row'][b][0]*fixture['column'][b][0] for b in (0,1)),
             sum(fixture['row'][b][0]*fixture['column'][b][1]+
                 fixture['row'][b][1]*fixture['column'][b][0] for b in (0,1))]
    for side in ('row','column'):
        if side+'_scalar' in fixture:
            c,d=fixture[side+'_scalar'];a,b=integer
            integer=[a*c,a*d+b*c]
    return dict(status='PASS_INDEPENDENT_CERTIFIED_ZERO_TWO_LEVEL_REPLAY',
                root_modular_jet=[v%4 for v in integer],independent_integer_jet=integer,
                independently_checked_nodes=calls,independently_checked_points=points,
                independently_checked_leaves=leaves,recovered_active_nodes=active,
                certified_zero_tuples_at_executed_points=covered,maximum_depth=2,
                full_formal_domain_enumerated=False,source_qualified=False,
                executable_refinement_proven=False,complexity_proven=False,
                scope='ONE_WIRE; TWO FINITE ACTIVE LEVELS; CERTIFIED ZERO FAMILIES, NOT SOURCE EXECUTOR')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed',action='store_true')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--replay',type=Path)
    args=parser.parse_args()
    if args.installed:
        from veritas.research.manuscript import executor
        if ROOT/'src' in Path(executor.__file__).resolve().parents:
            parser.error('installed experiment unexpectedly imported checkout source')
    if args.replay:
        print(json.dumps(replay(json.loads(args.replay.read_text())),indent=2));return
    if not args.output_dir:parser.error('--output-dir or --replay required')
    out=args.output_dir.resolve()
    if out==ROOT or ROOT in out.parents:parser.error('evidence must be outside source')
    out.mkdir(parents=True,exist_ok=True)
    certificate=produce();path=out/'certified_two_level.json'
    path.write_text(json.dumps(certificate,indent=2)+'\n')
    if certificate['report']['status']!='PASS_EXPERIMENTAL_CERTIFIED_ZERO_TWO_LEVEL':
        print(json.dumps(certificate['report'],indent=2));raise SystemExit(2)
    result=replay(json.loads(path.read_text()))
    (out/'independent_two_level_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
