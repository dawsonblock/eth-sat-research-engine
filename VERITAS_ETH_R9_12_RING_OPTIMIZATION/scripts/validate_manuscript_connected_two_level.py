"""Connected finite two-level experiment with certified L=2 zero families.

Separate from the unpruned manuscript executor. The source schedule, source
qualification, full-domain enumeration and shrinking-child gates stay false.
The replay independently derives canonical packet tables and all node values.
"""
import argparse
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import product
import json
from math import comb
from pathlib import Path
import sys
from time import monotonic

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


def layout_data(network,layout):
    return dict(padded_height=layout.padded_height,
        labels=[dict(side=v.side,identity=v.identity,group=layout.labels(v.side)[v.identity][0])
                for v in network.vertices],
        packets=[dict(pair=list(p.pattern[0]),index=p.index,slots=[list(s) for s in p.slots])
                 for p in layout.packets])


class CertifiedSlotDomain(Domain):
    """Only occupied crossing slots at b=0 and binary power can survive."""
    def __init__(self,network,layout,point,budget):
        if (layout.a,layout.r,point.L,point.f,point.ell)!=(1,2,2,19,2) or point.t not in (-1,1):
            raise ZeroCertificateError('unsupported slot-zero geometry')
        if any(set(layout.labels(side))!={v.identity for v in network.vertices if v.side==side}
               for side in ('row','column')):
            raise ZeroCertificateError('label coverage mismatch')
        for labels in (layout.rows,layout.columns):
            if any(word not in ((0,),(1,)) for word in labels.values()):
                raise ZeroCertificateError('labels must be binary one-letter words')
        H=layout.padded_height
        if H<2 or H%2:raise ZeroCertificateError('invalid padding')
        inventory=[((pair,),index) for pair in ((0,0),(0,1),(1,1))
                   for index in range(H//(2 if pair[0]==pair[1] else 1))]
        if [(p.pattern,p.index) for p in layout.packets]!=inventory:
            raise ZeroCertificateError('incomplete padded inventory')
        seen=set();edges=network.edges()
        for packet in layout.packets:
            slots=set();pair=packet.pattern[0]
            for slot,edge in packet.slots:
                if slot not in (0,1) or slot in slots or edge in seen or not 0<=edge<network.wires:
                    raise ZeroCertificateError('invalid or repeated occupied slot')
                slots.add(slot);seen.add(edge);row,col=edges[edge]
                if (layout.rows[row][0],layout.columns[col][0])!=(pair[slot],pair[1-slot]):
                    raise ZeroCertificateError('packet orientation mismatch')
        if seen!=set(range(network.wires)):raise ZeroCertificateError('wire coverage mismatch')
        super().__init__(layout,point,budget)
        self.support=tuple(self.packet_rank[pid]*2+slot
            for pid,p in enumerate(layout.packets) if pid in self.packet_rank for slot,_ in p.slots)
        self.full_count=self.count()
        self.retained_count=sum(comb(len(self.support),k) for k in range(min(len(self.support),point.precision-1)+1))

    def tuples(self):
        for bits in product((0,1),repeat=len(self.support)):
            self.budget.tick()
            if sum(bits)>=self.point.precision:continue
            beta=[0]*self.size
            for index,bit in zip(self.support,bits):beta[index]=bit
            self.budget.tuples+=1
            yield tuple(beta)

    def certificate(self):
        return dict(schema='L2_OCCUPIED_SLOT_ZERO_V1',eligible_channels=list(self.support),
            formal_channels_per_weight=self.per_weight,formal_mode_count=self.size,
            formal_tuple_count=self.full_count,retained_tuple_count=self.retained_count,
            certified_zero_tuple_count=self.full_count-self.retained_count,
            families=['EMPTY_SOURCE_SLOT','POSITIVE_GEOMETRIC_EXPONENT_AT_J_ZERO','POWER_EXCEEDS_ONE_TARGET_ROW'])


def fixture_default():
    return dict(wires=2,precision=2,ell=2,vertices=[
        dict(side='row',identity=0,ports=[0,1],values=[[1,2],[3,1],[2,0],[1,2]]),
        dict(side='column',identity=0,ports=[0],values=[[2,1],[1,3]]),
        dict(side='column',identity=1,ports=[1],values=[[3,2],[2,1]])])


def produce(fixture=None,*,limits=Limits(max_work=300_000_000,max_seconds=180)):
    fixture=fixture_default() if fixture is None else fixture
    network=Network(fixture['wires'],tuple(Vertex(v['side'],v['identity'],tuple(v['ports']),
        DenseTensor(len(v['ports']),2,tuple(map(tuple,v['values'])))) for v in fixture['vertices']))
    if fixture['precision']!=2 or fixture['ell']!=2:raise ValueError('requires p=ell=2')
    if network.wires<2:raise ValueError('connected multi-wire root required')
    # Check all incident root vertices are in a single connected component.
    endpoints={e:[] for e in range(network.wires)}
    for i,v in enumerate(network.vertices):
        for e in v.ports:endpoints[e].append(i)
    reached={next(i for i,v in enumerate(network.vertices) if v.ports)}
    while True:
        grown=reached|{i for ends in endpoints.values() if reached.intersection(ends) for i in ends}
        if grown==reached:break
        reached=grown
    if reached!={i for i,v in enumerate(network.vertices) if v.ports}:raise ValueError('disconnected root')
    budget=Budget(limits);events=[];configuration=ScaledExperiment()
    flags=dict(source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
               full_formal_domain_enumerated=False,shrinking_children_certified=False)
    def emit(event):
        budget.items(len(events)+1,'event stream');events.append(event)
    try:
        def visit(graph,p,depth):
            budget.tick();budget.calls+=1;budget.max_depth=max(depth,budget.max_depth)
            if graph.wires>5:raise ZeroCertificateError('finite fixture wire cap exceeded')
            ring=Ring(p,19,2,budget)
            if depth==2 or not graph.wires:
                value=direct(graph,ring)
                emit(dict(kind='leaf',depth=depth,precision=p,wires=graph.wires,result=value));return value
            layout=configuration.layout(graph,budget)
            emit(dict(kind='active',depth=depth,precision=p,wires=graph.wires,
                      layout=layout_data(graph,layout)))
            def point_value(node,z,node_ring):
                budget.points+=1;point=Point(2,node.t,z,node.precision,19,2)
                domain=CertifiedSlotDomain(graph,layout,point,budget)
                value=point_contraction(graph,layout,domain,node_ring,
                    lambda child,q:visit(child,q,depth+1),require_bounds=False)
                emit(dict(kind='point',depth=depth,precision=node.precision,t=node.t,
                          multiplicity=node.multiplicity,zeta=z,result=value,zero_certificate=domain.certificate()))
                return value
            value=recover(graph.wires,1,1,ring,point_value,experimental_precision=True)
            emit(dict(kind='recovered',depth=depth,precision=p,wires=graph.wires,result=value));return value
        value=visit(network,2,0)
        if any(any(row[1:]) for row in value):raise ZeroCertificateError('root left base subring')
        report=dict(status='PASS_EXPERIMENTAL_CONNECTED_TWO_LEVEL',result=value,ledger=budget.report(),
                    active_levels=2,zero_families_certified=True,**flags)
    except ResourceLimit as exc:
        report=dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),**flags)
    except ZeroCertificateError as exc:
        report=dict(status='REFUSED_ZERO_CERTIFICATE',reason=str(exc),ledger=budget.report(),**flags)
    return dict(schema='VERITAS_CONNECTED_TWO_LEVEL_V1',fixture=fixture,report=report,events=events)


# Independent replay. No production constructor, layout, mode, packet evaluator,
# interpolation or recovery routine is invoked below this line.
def need(ok,message):
    if not ok:raise ReplayError(message)


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def canonical(value,p):
    need(isinstance(value,(list,tuple)) and len(value)==2 and
         all(isinstance(row,(list,tuple)) and len(row)==4 and
             all(type(x) is int and 0<=x<2**p for x in row) for row in value),'noncanonical jet')
    return tuple(map(tuple,value))


def mul(a,b,r):return (r.mul(a[0],b[0]),r.add(r.mul(a[0],b[1]),r.mul(a[1],b[0])))
def add(a,b,r):return tuple(r.add(x,y) for x,y in zip(a,b))


def decode_fixture(fixture):
    need(set(fixture)=={'wires','precision','ell','vertices'},'fixture fields')
    need(type(fixture['wires']) is int and 0<=fixture['wires']<=5 and
         type(fixture['precision']) is int and fixture['precision']==2 and
         type(fixture['ell']) is int and fixture['ell']==2,'fixture dimensions')
    vertices=[];seen=set();endpoints=set()
    need(isinstance(fixture['vertices'],list) and len(fixture['vertices'])<=32,'fixture vertex cap')
    for v in fixture['vertices']:
        need(set(v)=={'side','identity','ports','values'},'vertex fields')
        key=v['side'],v['identity']
        need(v['side'] in ('row','column') and type(v['identity']) is int and v['identity']>=0 and key not in seen,'vertex identity')
        seen.add(key)
        need(isinstance(v['ports'],list) and len(v['ports'])<=5,'ports')
        for edge in v['ports']:
            need(type(edge) is int and 0<=edge<fixture['wires'] and (v['side'],edge) not in endpoints,'wire ownership')
            endpoints.add((v['side'],edge))
        need(isinstance(v['values'],list) and len(v['values'])==2**len(v['ports']),'table arity')
        table=[]
        for row in v['values']:
            need(isinstance(row,list) and len(row)==2 and all(type(c) is int and 0<=c<4 for c in row),'input table entry')
            table.append(tuple((c,0,0,0) for c in row))
        vertices.append(dict(side=v['side'],identity=v['identity'],ports=tuple(v['ports']),table=table))
    need(len(endpoints)==2*fixture['wires'],'missing endpoint')
    return dict(wires=fixture['wires'],vertices=vertices)


def exact(graph,p):
    r=ExtensionRing(p,19);total=(r.zero,r.zero)
    for assignment in range(2**graph['wires']):
        term=(r.one,r.zero)
        for v in graph['vertices']:
            index=sum(((assignment>>e)&1)<<j for j,e in enumerate(v['ports']))
            term=mul(term,v['table'][index],r)
        total=add(total,term,r)
    return total


def verify_layout(graph,data):
    need(set(data)=={'labels','packets','padded_height'},'layout fields')
    labels=data['labels'];vertices=graph['vertices'];need(len(labels)==len(vertices),'label count')
    groups={};owners={}
    for v,label in zip(vertices,labels):
        need(set(label)=={'side','identity','group'} and type(label['group']) is int and label['group'] in (0,1),'label shape')
        need(same([label['side'],label['identity']],[v['side'],v['identity']]),'label vertex mismatch')
        groups[v['side'],v['identity']]=label['group']
        for e in v['ports']:owners[v['side'],e]=v['identity']
    classes={}
    for e in range(graph['wires']):
        pair=tuple(groups[side,owners[side,e]] for side in ('row','column'))
        classes.setdefault(pair,[]).append(e)
    H=2*((max(map(len,classes.values()))+1)//2)
    need(type(data['padded_height']) is int and data['padded_height']==H,'noncanonical padding')
    packets=[]
    for pair in ((0,0),(0,1),(1,1)):
        for index in range(H//(2 if pair[0]==pair[1] else 1)):
            slots=[]
            if pair[0]==pair[1]:
                bucket=classes.get(pair,[])
                for slot in (0,1):
                    offset=2*index+slot
                    if offset<len(bucket):slots.append([slot,bucket[offset]])
            else:
                for slot,direction in ((0,(0,1)),(1,(1,0))):
                    bucket=classes.get(direction,[])
                    if index<len(bucket):slots.append([slot,bucket[index]])
            packets.append(dict(pair=list(pair),index=index,slots=slots))
    need(same(packets,data['packets']),'packet inventory or slot mismatch')
    support=[];rank=0
    for pid,packet in enumerate(packets):
        if packet['pair']==[0,1]:
            support.extend((2*rank+slot,pid,slot) for slot,_ in packet['slots']);rank+=1
    return groups,owners,packets,support,2*rank


@lru_cache(None)
def hermite_weights(M):
    """Solve for the origin functional by rational monomial constraints.

    Independent Gaussian elimination, rather than producer reciprocal-series
    recurrence. Local coefficient j is comb(k,j)*t**(k-j)*4**j on monomial T^k.
    """
    m=3*M;columns=[(t,j) for t in (-1,1) for j in range(m)];n=2*m
    A=[[Fraction(comb(k,j)*t**(k-j)*4**j) if k>=j else Fraction(0)
        for t,j in columns]+[Fraction(k==0)] for k in range(n)]
    for col in range(n):
        pivot=next(i for i in range(col,n) if A[i][col]);A[col],A[pivot]=A[pivot],A[col]
        factor=A[col][col];A[col]=[x/factor for x in A[col]]
        for i in range(n):
            if i!=col and A[i][col]:
                factor=A[i][col];A[i]=[x-factor*y for x,y in zip(A[i],A[col])]
    return tuple(row[-1] for row in A)


@lru_cache(None)
def hermite_losses(M):
    m=3*M;weights=hermite_weights(M)
    return tuple(max((w.denominator&-w.denominator).bit_length()-1 for w in weights[k*m:(k+1)*m]) for k in range(2))


@lru_cache(None)
def partition_count(p,channels):
    if channels==0:return 1
    coefficients=[1]+[0]*(p-1)
    for weight in range(1,p):
        out=[0]*p
        for n,v in enumerate(coefficients):
            for copies in range((p-1-n)//weight+1):
                out[n+copies*weight]+=v*comb(copies+channels-1,channels-1)
        coefficients=out
    return sum(coefficients)


def kernel(t,z,x,y,r):
    coefficients=[Fraction(-1,2)]
    for root in (-2,-1,0,1):
        if root==y-x:continue
        out=[Fraction(0)]*(len(coefficients)+1)
        for j,c in enumerate(coefficients):out[j]-=root*c;out[j+1]+=c
        coefficients=out
    shifted=[sum(c*comb(j,k)*t**(j-k)*4**k for j,c in enumerate(coefficients) if j>=k)
             for k in range(len(coefficients))]
    value=r.zero
    for c in reversed(shifted):
        need(c.denominator%2==1,'nonintegral Cauchy coefficient')
        value=r.add(r.mul(value,z),r.elem([c.numerator*pow(c.denominator,-1,r.modulus)]))
    return value


def child_oracle(graph,layout,p,t,z,selected,group):
    groups,owners,packets,_,_=layout;r=ExtensionRing(p,19)
    variables=[(side,e) for side in ('row','column') for e in range(graph['wires'])
               if groups[side,owners[side,e]]==group]
    ids={key:i for i,key in enumerate(variables)};vertices=[]
    for v in graph['vertices']:
        if groups[v['side'],v['identity']]==group:
            vertices.append(dict(side='row',identity=len(vertices),
                ports=tuple(ids[v['side'],e] for e in v['ports']),table=v['table']))
    for pid,packet in enumerate(packets):
        rows=[(slot,e) for slot,e in packet['slots'] if ('row',e) in ids]
        cols=[(slot,e) for slot,e in packet['slots'] if ('column',e) in ids]
        ports=tuple(ids['row',e] for _,e in rows)+tuple(ids['column',e] for _,e in cols)
        table=[]
        for index in range(2**len(ports)):
            ys=[(index>>j)&1 for j in range(len(rows))]
            xs=[(index>>(j+len(rows)))&1 for j in range(len(cols))]
            value=r.one
            # Selected cross-slot modes are binary. At L=2 each target has
            # exactly one row; independently extract its affine coefficient.
            for (slot,_),bit in zip(rows,ys):
                if (pid,slot) in selected:
                    factor=kernel(t,z,slot,slot,r)
                    if not bit:factor=r.neg(factor)
                else:
                    factor=r.zero
                    for (col,_),x in zip(cols,xs):
                        if x:factor=r.add(factor,kernel(t,z,slot,col,r))
                    if not bit:factor=r.sub(r.one,factor)
                value=r.mul(value,factor)
            for (slot,_),bit in zip(cols,xs):
                if (pid,slot) in selected and not bit:value=r.zero
            table.append((value,r.zero))
        vertices.append(dict(side='column',identity=pid,ports=ports,table=table))
    return dict(wires=len(variables),vertices=vertices)


def point_exact(graph,layout,p,t,z):
    r=ExtensionRing(p,19);packets=layout[2];addresses={e:(pid,s) for pid,pac in enumerate(packets) for s,e in pac['slots']}
    weights={}
    for e,(pid,s) in addresses.items():
        for f,(other,col) in addresses.items():weights[e,f]=kernel(t,z,s,col,r) if pid==other else r.zero
    total=(r.zero,r.zero);M=graph['wires']
    for ys in product((0,1),repeat=M):
        for xs in product((0,1),repeat=M):
            term=(r.one,r.zero)
            for v in graph['vertices']:
                bits=ys if v['side']=='row' else xs
                index=sum(bits[e]<<j for j,e in enumerate(v['ports']))
                term=mul(term,v['table'][index],r)
            for e,bit in enumerate(ys):
                factor=r.zero
                for f,x in enumerate(xs):
                    if x:factor=r.add(factor,weights[e,f])
                if not bit:factor=r.sub(r.one,factor)
                term=tuple(r.mul(c,factor) for c in term)
            total=add(total,term,r)
    return total


def replay(certificate,*,max_seconds=180,max_events=200000):
    started=monotonic();need(set(certificate)=={'schema','fixture','report','events'},'certificate fields')
    need(certificate['schema']=='VERITAS_CONNECTED_TWO_LEVEL_V1','schema')
    graph=decode_fixture(certificate['fixture']);events=certificate['events'];report=certificate['report']
    need(graph['wires']>=2,'multi-wire root required')
    # Independently traverse adjacency through shared wire incidence.
    live=[set(v['ports']) for v in graph['vertices'] if v['ports']];connected=set(live.pop())
    while live:
        touching=[i for i,ports in enumerate(live) if ports&connected]
        need(bool(touching),'disconnected root')
        for i in reversed(touching):connected.update(live.pop(i))
    need(isinstance(events,list) and len(events)<=max_events,'event cap')
    need(report.get('status')=='PASS_EXPERIMENTAL_CONNECTED_TWO_LEVEL','producer did not complete')
    for key in ('source_qualified','executable_refinement_proven','complexity_proven','full_formal_domain_enumerated','shrinking_children_certified'):
        need(report.get(key) is False,'unsupported scope claim')
    need(report.get('zero_families_certified') is True and type(report.get('active_levels')) is int and report['active_levels']==2,'policy')
    cursor=0;counts=Counter();covered=0;wire_counts=set();precisions=set()
    def take(expected):
        nonlocal cursor
        if monotonic()-started>max_seconds:raise ReplayError('INCONCLUSIVE_RESOURCE_LIMIT: replay time cap')
        need(cursor<len(events),'truncated stream');event=events[cursor];cursor+=1
        need(set(event)==set(expected)|({'result'} if 'result' not in expected else set()),'event fields')
        for key,value in expected.items():need(same(event[key],value),'event metadata mismatch: '+key)
        return event
    def visit(graph,p,depth):
        nonlocal covered
        counts['calls']+=1;wire_counts.add(graph['wires']);precisions.add(p)
        need(graph['wires']<=5,'oracle wire cap')
        if depth==2 or not graph['wires']:
            counts['leaves']+=1
            event=take(dict(kind='leaf',depth=depth,precision=p,wires=graph['wires']))
            need(canonical(event['result'],p)==exact(graph,p),'leaf value mismatch');return
        counts['active']+=1
        need(cursor<len(events),'missing layout');data=events[cursor].get('layout')
        # Active events contain layout but no result.
        event=events[cursor]
        need(set(event)=={'kind','depth','precision','wires','layout'},'active fields')
        expected=dict(kind='active',depth=depth,precision=p,wires=graph['wires'],layout=data)
        need(same(event,expected),'active metadata')
        advance()
        layout=verify_layout(graph,data);support=layout[3];channels=layout[4];M=graph['wires']
        for node_index,t in enumerate((-1,1)):
            q=p+hermite_losses(M)[node_index]
            for index in range(3*M+1):
                z=tuple((index>>j)&1 for j in range(4));counts['points']+=1
                retained=0
                for bits in product((0,1),repeat=len(support)):
                    if sum(bits)>=q:continue
                    retained+=1;counts['tuples']+=1
                    selected={(pid,slot) for (_,pid,slot),bit in zip(support,bits) if bit}
                    for group in (0,1):visit(child_oracle(graph,layout,q,t,z,selected,group),q,depth+1)
                count=partition_count(q,channels);covered+=count-retained
                cert=dict(schema='L2_OCCUPIED_SLOT_ZERO_V1',eligible_channels=[c for c,_,_ in support],
                    formal_channels_per_weight=channels,formal_mode_count=channels*(q-1),formal_tuple_count=count,
                    retained_tuple_count=retained,certified_zero_tuple_count=count-retained,
                    families=['EMPTY_SOURCE_SLOT','POSITIVE_GEOMETRIC_EXPONENT_AT_J_ZERO','POWER_EXCEEDS_ONE_TARGET_ROW'])
                point=take(dict(kind='point',depth=depth,precision=q,t=t,multiplicity=3*M,zeta=z,zero_certificate=cert))
                need(canonical(point['result'],q)==point_exact(graph,layout,q,t,z),'independent half-edge point mismatch')
        event=take(dict(kind='recovered',depth=depth,precision=p,wires=M))
        need(canonical(event['result'],p)==exact(graph,p),'recovered node mismatch')
    def advance():
        nonlocal cursor
        cursor+=1
    visit(graph,2,0)
    need(cursor==len(events),'extra events');need(canonical(report['result'],2)==exact(graph,2),'root mismatch')
    ledger=report['ledger']
    for key,value in dict(calls=counts['calls'],interpolation_points=counts['points'],exponent_tuples=counts['tuples'],maximum_depth=2).items():
        need(type(ledger[key]) is int and ledger[key]==value,'ledger mismatch')
    need(ledger['bit_operations'] is None,'unsupported bit-operation claim')
    integer=[0,0]
    for assignment in range(2**graph['wires']):
        term=[1,0]
        for vertex in certificate['fixture']['vertices']:
            index=sum(((assignment>>e)&1)<<j for j,e in enumerate(vertex['ports']))
            c,d=vertex['values'][index];a,b=term;term=[a*c,a*d+b*c]
        integer=[a+b for a,b in zip(integer,term)]
    need([v%4 for v in integer]==[row[0] for row in exact(graph,2)],'integer root oracle mismatch')
    return dict(status='PASS_INDEPENDENT_CONNECTED_TWO_LEVEL_REPLAY',independent_integer_jet=integer,root_modular_jet=[row[0] for row in exact(graph,2)],
        independently_checked_nodes=counts['calls'],independently_checked_points=counts['points'],
        independently_checked_leaves=counts['leaves'],recovered_active_nodes=counts['active'],
        certified_zero_tuples_at_executed_points=covered,maximum_depth=2,node_wire_counts=sorted(wire_counts),
        node_precisions=sorted(precisions),full_formal_domain_enumerated=False,source_qualified=False,
        executable_refinement_proven=False,complexity_proven=False,shrinking_children_certified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--installed',action='store_true')
    parser.add_argument('--output-dir',type=Path);parser.add_argument('--replay',type=Path);args=parser.parse_args()
    if args.installed:
        from veritas.research.manuscript import executor
        if ROOT/'src' in Path(executor.__file__).resolve().parents:parser.error('checkout source imported')
    if args.replay:
        if args.replay.stat().st_size>20_000_000:parser.error('certificate byte cap')
        print(json.dumps(replay(json.loads(args.replay.read_text())),indent=2));return
    if not args.output_dir:parser.error('--output-dir or --replay required')
    out=args.output_dir.resolve()
    if out==ROOT or ROOT in out.parents:parser.error('evidence must be external')
    out.mkdir(parents=True,exist_ok=True);certificate=produce()
    path=out/'connected_two_level.json';path.write_text(json.dumps(certificate,indent=2)+'\n')
    if certificate['report']['status']!='PASS_EXPERIMENTAL_CONNECTED_TWO_LEVEL':
        print(json.dumps(certificate['report'],indent=2));raise SystemExit(2)
    result=replay(json.loads(path.read_text()));(out/'independent_connected_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
