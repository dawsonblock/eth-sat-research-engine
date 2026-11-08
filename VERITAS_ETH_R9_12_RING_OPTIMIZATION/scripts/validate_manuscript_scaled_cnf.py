"""Shared general CNF encoder -> explicit finite recursion -> independent count.

Producer has no fixed n=2 or occurrence cap. The independent replay is bounded:
L=2/radix 2 certified support, ell=1, <=12 variables, <=8 wires at every node,
field degree <=16 and <=256 precision bits. These are checker limits only.
"""
import argparse
from collections import Counter
from dataclasses import asdict
from itertools import product
import json
from math import isqrt
from pathlib import Path
import sys
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
if '--installed' not in sys.argv:sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from validate_manuscript_connected_two_level import hermite_weights,kernel,verify_layout,same
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.manuscript.cnf import Formula
from veritas.research.manuscript.experimental import ScaledExperiment,count_scaled_cnf
from veritas.research.manuscript.finite_replay import ReplayError
from veritas.research.manuscript.resources import Budget,Limits


def need(ok,message):
    if not ok:raise ReplayError(message)


def produce(n=2,clauses=None,*,active_depth=2,limits=Limits(max_work=2_000_000_000,max_seconds=600)):
    clauses=[[1,2]] if clauses is None else clauses
    experiment=ScaledExperiment(active_depth=active_depth,certified_support=True)
    budget=Budget(limits);events=[]
    def emit(event):
        budget.items(len(events)+1,'recursive event stream');events.append(event)
    report=count_scaled_cnf(Formula(n,tuple(map(tuple,clauses))),experiment=experiment,
                            limits=limits,budget=budget,event_sink=emit)
    return dict(schema='VERITAS_SHARED_SCALED_CNF_V1',formula=dict(n=n,clauses=clauses),
                configuration=experiment.description(),limits=asdict(limits),report=report,events=events)


# Independent root equivalence: equality components are checked by union-find,
# rather than rebuilding the producer's deterministic equality-chain algorithm.
def verify_encoding(formula,event):
    n=formula['n'];original=formula['clauses']
    need(set(event)=={'kind','n','clauses','wires','unused_variables','precision','vertices'},'encoding fields')
    need(event['kind']=='encoding' and type(event['n']) is int and event['n']==n,'encoding n')
    normalized=set()
    for clause in original:
        literals=frozenset(clause)
        if any(-lit in literals for lit in literals):continue
        normalized.add(literals)
    recorded=event['clauses']
    need(type(recorded) is list and len(recorded)==len(normalized) and
         all(type(c) is list and c and all(type(l) is int and 1<=abs(l)<=n for l in c)
             and len(c)==len(set(c)) for c in recorded) and
         {frozenset(c) for c in recorded}==normalized,'normalized clauses mismatch')
    M=event['wires'];p=n+1
    need(type(M) is int and 1<=M<=8,'INCONCLUSIVE_RESOURCE_LIMIT: root wire cap')
    used={abs(l) for c in recorded for l in c}
    need(type(event['unused_variables']) is int and event['unused_variables']==n-len(used),'unused factor mismatch')
    need(type(event['precision']) is int and event['precision']==p,'count precision mismatch')
    vertices=event['vertices'];need(type(vertices) is list and len(vertices)<=128,'root vertex cap')
    parents=list(range(M))
    def find(x):
        while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
        return x
    def union(a,b):parents[find(a)]=find(b)
    seen=set();owners=set();clauses={};out=[]
    for v in vertices:
        need(type(v) is dict and set(v)=={'side','identity','ports','tensor'},'root vertex fields')
        side,key,ports,tensor=v['side'],v['identity'],v['ports'],v['tensor']
        need(side in ('row','column') and type(key) is int and key>=0 and (side,key) not in seen,'vertex identity')
        seen.add((side,key))
        need(type(ports) is list and len(ports)<=8 and all(type(e) is int and 0<=e<M for e in ports),'ports')
        for e in ports:
            need((side,e) not in owners,'duplicate endpoint');owners.add((side,e))
        need(type(tensor) is dict and tensor.get('creation_precision')==p and type(tensor.get('creation_precision')) is int,'tensor creation precision')
        if tensor.get('kind')=='clause':
            need(set(tensor)=={'kind','positive','creation_precision'} and side=='row' and 0<=key<len(recorded),'clause tensor metadata')
            need(type(tensor['positive']) is list and len(tensor['positive'])==len(ports) and
                 all(type(x) is bool for x in tensor['positive']),'literal signs')
            need(same(tensor['positive'],[l>0 for l in recorded[key]]) and len(ports)==len(recorded[key]),'clause signs/arity')
            clauses[key]=ports
            table=[int(any(bool((bits>>j)&1)==sign for j,sign in enumerate(tensor['positive']))) for bits in range(2**len(ports))]
        else:
            need(set(tensor)=={'kind','arity','creation_precision'} and tensor['kind']=='equality' and
                 type(tensor['arity']) is int and tensor['arity']==len(ports),'equality metadata')
            need(len(ports)==2 if side=='column' else 1<=len(ports)<=3,'equality degree')
            for e in ports[1:]:union(ports[0],e)
            table=[int(bits in (0,2**len(ports)-1)) for bits in range(2**len(ports))]
        out.append(dict(side=side,identity=key,ports=tuple(ports),table=table,creation_precision=p))
    need(len(owners)==2*M and set(clauses)==set(range(len(recorded))),'encoding incidence coverage')
    component_variable={};variable_component={}
    for key,ports in clauses.items():
        for edge,lit in zip(ports,recorded[key]):
            component=find(edge);variable=abs(lit)
            need(component_variable.get(component,variable)==variable,'equality merges distinct variables')
            need(variable_component.get(variable,component)==component,'variable equality component disconnected')
            component_variable[component]=variable;variable_component[variable]=component
    need({find(e) for e in range(M)}==set(component_variable),'unaccounted free equality component')
    return dict(wires=M,vertices=out),event['unused_variables']


def irreducible(f,e):
    if type(f) is not int or f.bit_length()!=e+1:return False
    def remainder(value,divisor):
        while value and value.bit_length()>=divisor.bit_length():value^=divisor<<(value.bit_length()-divisor.bit_length())
        return value
    return not any(remainder(f,(1<<degree)|low)==0 for degree in range(1,e//2+1) for low in range(1<<degree))


class Replay:
    def __init__(self,f,events,active_depth,leaf_threshold,*,max_seconds=600):
        self.f=f;self.e=f.bit_length()-1;self.events=events;self.cursor=1
        self.active_depth=active_depth;self.leaf_threshold=leaf_threshold;self.counts=Counter()
        self.started=monotonic();self.max_seconds=max_seconds

    def check_time(self):
        need(monotonic()-self.started<=self.max_seconds,'INCONCLUSIVE_RESOURCE_LIMIT: recursive replay time')

    def canonical(self,value,p):
        need(type(value) in (tuple,list) and len(value)==1 and type(value[0]) in (tuple,list)
             and len(value[0])==self.e and all(type(c) is int and 0<=c<2**p for c in value[0]),'noncanonical scalar result')
        return tuple(value[0])

    def exact(self,graph,p):
        r=ExtensionRing(p,self.f);total=r.zero
        for assignment in range(2**graph['wires']):
            self.check_time();term=r.one
            for v in graph['vertices']:
                index=sum(((assignment>>edge)&1)<<j for j,edge in enumerate(v['ports']))
                term=r.mul(term,v['table'][index])
            total=r.add(total,term)
        return total

    def take(self,expected):
        self.check_time();need(self.cursor<len(self.events),'truncated recursive stream')
        event=self.events[self.cursor];self.cursor+=1
        need(type(event) is dict and set(event)==set(expected)|{'result'},'event fields')
        for key,value in expected.items():need(same(event[key],value),'event mismatch: '+key)
        return event

    def layout(self,graph,event):
        labels=event['labels'];need(type(labels) is list and len(labels)==len(graph['vertices']),'label inventory')
        legacy_labels=[]
        for v,label in zip(graph['vertices'],labels):
            need(type(label) is dict and set(label)=={'side','identity','word'} and
                 same([label['side'],label['identity']],[v['side'],v['identity']]),'label vertex')
            word=label['word'];need(type(word) in (tuple,list) and len(word)==1 and type(word[0]) is int and word[0] in (0,1),'binary label')
            legacy_labels.append(dict(side=v['side'],identity=v['identity'],group=word[0]))
        packets=[]
        for packet in event['packets']:
            need(type(packet) is dict and set(packet)=={'pattern','index','slots'} and
                 type(packet['pattern']) in (tuple,list) and len(packet['pattern'])==1,'packet fields')
            packets.append(dict(pair=packet['pattern'][0],index=packet['index'],slots=packet['slots']))
        layout=verify_layout(graph,dict(padded_height=event['padded_height'],labels=legacy_labels,packets=packets))
        groups,owners,packets,support,channels=layout
        classes=Counter((groups['row',owners['row',e]],groups['column',owners['column',e]]) for e in range(graph['wires']))
        need(type(event['variance_scaled']) is int and event['variance_scaled']==4*sum(n*n for n in classes.values())-graph['wires']**2,'class variance')
        need(type(event['padded_packets']) is int and event['padded_packets']==len(packets),'packet count')
        return layout

    def child(self,graph,layout,p,t,z,selected,group):
        groups,owners,packets,_,_=layout;r=ExtensionRing(p,self.f)
        variables=[(side,e) for side in ('row','column') for e in range(graph['wires']) if groups[side,owners[side,e]]==group]
        ids={key:i for i,key in enumerate(variables)};vertices=[]
        for v in graph['vertices']:
            if groups[v['side'],v['identity']]==group:
                vertices.append(dict(side='row',identity=len(vertices),ports=tuple(ids[v['side'],e] for e in v['ports']),table=v['table'],creation_precision=v['creation_precision']))
        for pid,packet in enumerate(packets):
            rows=[(s,e) for s,e in packet['slots'] if ('row',e) in ids]
            cols=[(s,e) for s,e in packet['slots'] if ('column',e) in ids]
            ports=tuple(ids['row',e] for s,e in rows)+tuple(ids['column',e] for s,e in cols);table=[]
            for index in range(2**len(ports)):
                ys=[(index>>j)&1 for j in range(len(rows))];xs=[(index>>(j+len(rows)))&1 for j in range(len(cols))]
                value=r.one
                for (slot,e),y in zip(rows,ys):
                    if (pid,slot) in selected:
                        factor=kernel(t,z,slot,slot,r)
                        if not y:factor=r.neg(factor)
                    else:
                        factor=r.zero
                        for (col,f),x in zip(cols,xs):
                            if x:factor=r.add(factor,kernel(t,z,slot,col,r))
                        if not y:factor=r.sub(r.one,factor)
                    value=r.mul(value,factor)
                for (slot,e),x in zip(cols,xs):
                    if (pid,slot) in selected and not x:value=r.zero
                table.append(value)
            vertices.append(dict(side='column',identity=pid,ports=ports,table=table,creation_precision=p))
        return dict(wires=len(variables),vertices=vertices)

    def point_exact(self,graph,layout,p,t,z):
        r=ExtensionRing(p,self.f);packets=layout[2];M=graph['wires']
        addresses={edge:(pid,slot) for pid,packet in enumerate(packets) for slot,edge in packet['slots']}
        weights={(e,f):(kernel(t,z,slot,col,r) if pid==other else r.zero)
                 for e,(pid,slot) in addresses.items() for f,(other,col) in addresses.items()}
        total=r.zero
        for ys in product((0,1),repeat=M):
            self.check_time()
            for xs in product((0,1),repeat=M):
                term=r.one
                for v in graph['vertices']:
                    bits=ys if v['side']=='row' else xs
                    index=sum(bits[e]<<j for j,e in enumerate(v['ports']));term=r.mul(term,v['table'][index])
                for e,y in enumerate(ys):
                    factor=r.zero
                    for f,x in enumerate(xs):
                        if x:factor=r.add(factor,weights[e,f])
                    if not y:factor=r.sub(r.one,factor)
                    term=r.mul(term,factor)
                total=r.add(total,term)
        return total

    def visit(self,graph,p,depth):
        self.check_time();M=graph['wires'];need(M<=8 and p<=256 and len(graph['vertices'])<=256,'INCONCLUSIVE_RESOURCE_LIMIT: node oracle scope')
        self.counts['calls']+=1;self.counts['maximum_depth']=max(depth,self.counts['maximum_depth'])
        if M==0 or depth>=self.active_depth:
            event=self.take(dict(kind='leaf',depth=depth,wires=M,precision=p,reason='EMPTY_NETWORK' if M==0 else 'EXPERIMENT_DEPTH_LIMIT'))
            value=self.exact(graph,p);need(self.canonical(event['result'],p)==value,'leaf value mismatch');return value
        need(self.cursor<len(self.events),'missing active record');event=self.events[self.cursor];self.cursor+=1
        fields={'kind','depth','wires','precision','a','u','padded_packets','leaf_threshold','experiment_scaled','defining_polynomial','radix','packets','padded_height','variance_scaled','labels'}
        need(type(event) is dict and set(event)==fields,'active fields')
        for key,value in dict(kind='active',depth=depth,wires=M,precision=p,a=1,u=1,leaf_threshold=self.leaf_threshold,
                              experiment_scaled=True,defining_polynomial=self.f,radix=2).items():
            need(same(event[key],value),'active metadata mismatch: '+key)
        layout=self.layout(graph,event);support=layout[3];channels=layout[4];weights=hermite_weights(M);m=3*M
        capacities=sorted([[pid,layout[2][pid]['pair'][slot],1] for _,pid,slot in support])
        for node,t in enumerate((-1,1)):
            loss=max((w.denominator&-w.denominator).bit_length()-1 for w in weights[node*m:(node+1)*m]);q=p+loss
            need(q<=256,'INCONCLUSIVE_RESOURCE_LIMIT: point precision')
            zero=dict(schema='PACKET_SOURCE_AND_TARGET_DEGREE_ZERO_V1',eligible_modes=[index for index,pid,slot in support],
                      target_capacities=capacities,formal_channels_per_weight=channels,formal_mode_count=channels*(q-1),
                      families=['EMPTY_SOURCE_TILE','POSITIVE_EXPONENT_WITH_ONLY_J_ZERO','TOTAL_POWER_EXCEEDS_TARGET_ROW_COUNT'])
            for number in range(3*M+1):
                z=tuple((number>>j)&1 for j in range(self.e));r=ExtensionRing(q,self.f);total=r.zero
                for bits in product((0,1),repeat=len(support)):
                    if sum(bits)>=q:continue
                    self.counts['tuples']+=1
                    selected={(pid,slot) for (index,pid,slot),bit in zip(support,bits) if bit};term=r.one
                    for group in (0,1):term=r.mul(term,self.visit(self.child(graph,layout,q,t,z,selected,group),q,depth+1))
                    total=r.add(total,term)
                point=self.take(dict(kind='point',depth=depth,wires=M,t=t,multiplicity=m,precision=q,zeta=z,zero_certificate=zero))
                need(self.canonical(point['result'],q)==total==self.point_exact(graph,layout,q,t,z),'point or tuple sum mismatch')
                self.counts['points']+=1
        recovered=self.take(dict(kind='recovered',depth=depth,wires=M));value=self.exact(graph,p)
        need(self.canonical(recovered['result'],p)==value,'recovered contraction mismatch');return value


def replay(certificate,*,max_seconds=600):
    """Numerically check every event without calling producer constructions.

    This is a bounded independent oracle, not a proof or a general solver.
    All recursive recovered values are checked against independent Boolean
    sums, all point values against independent half-edge sums, and all leaf
    tables against independently constructed creation-precision children.
    """
    started=monotonic()
    need(type(max_seconds) in (int,float) and 0<max_seconds<float('inf'),'positive checker time allowance')
    need(type(certificate) is dict and set(certificate)=={'schema','formula','configuration','limits','report','events'},'certificate fields')
    need(certificate['schema']=='VERITAS_SHARED_SCALED_CNF_V1','certificate schema')
    formula=certificate['formula'];need(type(formula) is dict and set(formula)=={'n','clauses'},'formula fields')
    n,clauses=formula['n'],formula['clauses']
    need(type(n) is int and 0<=n<=12,'INCONCLUSIVE_RESOURCE_LIMIT: original-variable oracle cap')
    need(type(clauses) is list and len(clauses)<=128 and all(type(c) is list and len(c)<=128 and
         all(type(l) is int and 1<=abs(l)<=n for l in c) for c in clauses),'formula clauses')
    configuration=certificate['configuration'];need(type(configuration) is dict,'configuration object')
    depth=configuration.get('active_depth');shift=configuration.get('column_label_shift')
    need(type(depth) is int and 1<=depth<=3 and type(shift) is int and shift in (0,1),'checker finite schedule scope')
    expected_configuration=dict(a=1,u=1,radix=2,active_depth=depth,column_label_shift=shift,
        precision_policy='EXACT_HERMITE_FUNCTIONAL_DENOMINATOR_LOSS',
        stopping_rule='EXPLICIT_DEPTH_NOT_SOURCE_LEAF_THRESHOLD',full_padded_inventory=True,
        full_weighted_mode_domain=False,manuscript_packing_bounds_enforced=False,shrinking_children_certified=False)
    need(same(configuration,expected_configuration),'unsupported finite configuration')
    limits=certificate['limits'];need(type(limits) is dict and set(limits)=={'max_work','max_seconds','max_items','max_integer_bits'},'producer limits')
    for key in ('max_work','max_items','max_integer_bits'):
        need(limits[key] is None or type(limits[key]) is int and limits[key]>0,'invalid producer allowance')
    need(limits['max_seconds'] is None or type(limits['max_seconds']) in (int,float) and 0<limits['max_seconds']<float('inf'),'invalid producer time')
    report=certificate['report'];events=certificate['events']
    need(type(report) is dict,'producer report object')
    if report.get('status')=='INCONCLUSIVE_RESOURCE_LIMIT':
        raise ReplayError('INCONCLUSIVE_RESOURCE_LIMIT: producer did not complete: '+str(report.get('reason','')))
    need(report.get('status')=='PASS_EXACT_COUNT','producer did not complete')
    need(type(events) is list and len(events)<=200000,'INCONCLUSIVE_RESOURCE_LIMIT: event inventory')
    for key in ('source_qualified','executable_refinement_proven','complexity_proven'):
        need(report.get(key) is False,'unsupported qualification')
    need(report.get('experimental_scaled') is True and same(report.get('experimental_scaling'),configuration),'experimental metadata')
    exact_count=0
    for bits in product((False,True),repeat=n):
        need(monotonic()-started<=max_seconds,'INCONCLUSIVE_RESOURCE_LIMIT: original-variable oracle time')
        exact_count+=all(any(bits[abs(l)-1] if l>0 else not bits[abs(l)-1] for l in c) for c in clauses)
    need(type(report.get('count')) is int and report['count']==exact_count,'original CNF count mismatch')
    nontrivial=[set(c) for c in clauses if not any(-l in c for l in c)]
    counts=Counter();encoded_wires=extension_degree=0
    if not nontrivial or any(not c for c in nontrivial):
        need(report.get('route')=='EXPERIMENTAL_TRIVIAL_CNF' and events==[],'trivial route or events')
    else:
        need(len(events)>=2 and type(events[0]) is dict,'missing encoding stream')
        graph,unused=verify_encoding(formula,events[0]);encoded_wires=graph['wires'];p=n+1
        s=max(2,encoded_wires,p,max(len(v['ports']) for v in graph['vertices'])**2)
        lam=(s-1).bit_length();extension_degree=4*lam;H=(s+isqrt(lam)-1)//isqrt(lam)
        need(extension_degree<=16,'INCONCLUSIVE_RESOURCE_LIMIT: extension field oracle cap')
        delta=next(d for d in range(1,s+1) if d**10>=s**9)
        params=dict(s=s,C=1,lambda_value=lam,extension_degree=extension_degree,leaf_threshold=H,degree_limit=delta)
        expected=dict(route='EXPERIMENTAL_SCALED_CNF',inner_route='EXPERIMENTAL_CERTIFIED_RECURSION',
            tensor_status='PASS_EXPERIMENTAL_CERTIFIED_RECURSION',encoding='CLAUSE_EQUALITY_TREE_SUBDIVISION',
            encoded_wires=encoded_wires,precision=p,ell=1,unused_variables=unused,extension_degree=extension_degree,
            finite_parameters=params,full_formal_domain_enumerated=False,budget_policy='SHARED_ENCODING_AND_CONTRACTION')
        for key,value in expected.items():need(same(report.get(key),value),'report metadata mismatch: '+key)
        need(type(events[1]) is dict,'first recursive event');f=events[1].get('defining_polynomial')
        need(irreducible(f,extension_degree),'invalid root field polynomial')
        r=ExtensionRing(p,f)
        for v in graph['vertices']:v['table']=[r.elem([value]) for value in v['table']]
        checker=Replay(f,events,depth,H,max_seconds=max_seconds-(monotonic()-started))
        result=checker.visit(graph,p,0);need(checker.cursor==len(events),'trailing recursive events')
        need(not any(result[1:]),'non-base-field count')
        need((result[0]<<unused)%(1<<p)==exact_count,'root count recovery mismatch')
        counts=checker.counts
    ledger=report.get('ledger');need(type(ledger) is dict and set(ledger)=={'work_units','elapsed_seconds','calls','interpolation_points','exponent_tuples','maximum_depth','bit_operations','hard_memory_limit_enforced'},'ledger fields')
    for key,value in dict(calls=counts['calls'],interpolation_points=counts['points'],exponent_tuples=counts['tuples'],maximum_depth=counts['maximum_depth']).items():
        need(type(ledger[key]) is int and ledger[key]==value,'ledger mismatch: '+key)
    need(type(ledger['work_units']) is int and ledger['work_units']>=0 and (limits['max_work'] is None or ledger['work_units']<=limits['max_work']),'producer work ledger allowance')
    need(type(ledger['elapsed_seconds']) in (int,float) and 0<=ledger['elapsed_seconds']<float('inf'),'producer time ledger')
    need(ledger['bit_operations'] is None and ledger['hard_memory_limit_enforced'] is False,'unsupported resource claim')
    return dict(status='PASS_INDEPENDENT_SHARED_SCALED_CNF_REPLAY',n=n,count=exact_count,encoded_wires=encoded_wires,
        extension_degree=extension_degree,precision=n+1,calls=counts['calls'],points=counts['points'],
        exponent_tuples=counts['tuples'],maximum_depth=counts['maximum_depth'],
        checked_original_CNF=True,checked_encoding_equality_components=True,checked_every_child_and_point=True,
        checker_limits=dict(original_variables=12,node_wires=8,extension_degree=16,precision=256,events=200000,max_seconds=max_seconds),
        elapsed_seconds=monotonic()-started,source_qualified=False,executable_refinement_proven=False,complexity_proven=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed',action='store_true');parser.add_argument('--replay',type=Path)
    parser.add_argument('--output-dir',type=Path);parser.add_argument('--n',type=int,default=2)
    parser.add_argument('--clauses-json',default='[[1,2]]');parser.add_argument('--active-depth',type=int,default=2)
    args=parser.parse_args()
    if args.installed:
        import veritas
        need(not Path(veritas.__file__).resolve().is_relative_to(ROOT/'src'),'installed replay imported checkout')
    try:
        if args.replay:
            need(args.replay.stat().st_size<=32*1024*1024,'INCONCLUSIVE_RESOURCE_LIMIT: certificate byte cap')
            certificate=json.loads(args.replay.read_text())
        else:
            if args.output_dir is None:parser.error('--output-dir required for generation')
            need(not args.output_dir.resolve().is_relative_to(ROOT),'evidence must be external')
            args.output_dir.mkdir(parents=True,exist_ok=True)
            certificate=produce(args.n,json.loads(args.clauses_json),active_depth=args.active_depth)
            (args.output_dir/'certificate.json').write_text(json.dumps(certificate,separators=(',',':')))
        result=replay(certificate)
    except (ReplayError,ValueError,TypeError,KeyError,OverflowError) as exc:
        result=dict(status='INCONCLUSIVE_RESOURCE_LIMIT' if 'INCONCLUSIVE_RESOURCE_LIMIT' in str(exc) else 'FAIL_REPLAY',reason=str(exc))
    if args.output_dir:
        need(not args.output_dir.resolve().is_relative_to(ROOT),'evidence must be external')
        args.output_dir.mkdir(parents=True,exist_ok=True)
        (args.output_dir/'independent_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS_INDEPENDENT_SHARED_SCALED_CNF_REPLAY' else 1


if __name__=='__main__':raise SystemExit(main())
