"""Explicit L=4, a=u=2 finite support experiment and independent replay.

Two coupled degree-two tensors and copy slots 0,2 exercise nonzero b>0 modes
and target powers greater than one. This is one active level, radix 2 and an
explicit label permutation, not literal source-active recursion or a proof.
"""
import argparse
from dataclasses import asdict
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import product
import json
from math import comb,isfinite
from pathlib import Path
import sys
from time import monotonic
from types import MappingProxyType

ROOT=Path(__file__).resolve().parents[1]
if '--installed' not in sys.argv:sys.path.insert(0,str(ROOT/'src'))
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.manuscript.cauchy import Point
from veritas.research.manuscript.certified_modes import DegreeCertifiedDomain
from veritas.research.manuscript.children import point_contraction
from veritas.research.manuscript.finite_replay import ReplayError
from veritas.research.manuscript.model import Network,Vertex,DenseTensor,direct
from veritas.research.manuscript.packing import Packet,Layout
from veritas.research.manuscript.recovery import recover
from veritas.research.manuscript.resources import Budget,Limits,ResourceLimit
from veritas.research.manuscript.ring import Ring

FIXTURE={'row':[[1,2],[3,1],[2,0],[1,2]],'column':[[2,1],[1,3],[3,2],[2,1]]}
FLAGS=dict(source_qualified=False,executable_refinement_proven=False,complexity_proven=False,
           full_formal_domain_enumerated=False,shrinking_children_certified=False)


def need(ok,message):
    if not ok:raise ReplayError(message)


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def fixture_network(fixture):
    if type(fixture) is not dict or set(fixture)!={'row','column'}:
        raise ValueError('fixed two-tensor fixture required')
    return Network(2,tuple(Vertex(side,0,(0,1),DenseTensor(2,2,tuple(map(tuple,fixture[side]))))
                           for side in ('row','column')))


def fixture_layout():
    # A fixed coordinate-0 column alphabet permutation preserves class loads.
    packets=[]
    for pattern in product(((0,0),(0,1),(1,1)),repeat=2):
        for k in range(4 >> sum(lo==hi for lo,hi in pattern)):
            slots=((0,0),(2,1)) if (pattern,k)==(((0,1),(0,0)),0) else ()
            packets.append(Packet(pattern,k,slots))
    return Layout(2,2,MappingProxyType({0:(0,0)}),MappingProxyType({0:(1,0)}),tuple(packets),4,60)


def layout_record(layout):
    return dict(a=layout.a,r=layout.r,padded_height=layout.padded_height,variance_scaled=layout.variance_scaled,
                rows=[[key,list(word)] for key,word in sorted(layout.rows.items())],
                columns=[[key,list(word)] for key,word in sorted(layout.columns.items())],
                packets=[dict(pattern=p.pattern,index=p.index,slots=p.slots) for p in layout.packets])


def verify_layout_record(data):
    # Re-derive direction and copy bits from the fixed declared label words.
    # This checker never calls encode_class_offset or the producer constructor.
    need(type(data) is dict and set(data)=={'a','r','padded_height','variance_scaled','rows','columns','packets'},'layout fields')
    for key,value in dict(a=2,r=2,padded_height=4,variance_scaled=60,
                          rows=[[0,[0,0]]],columns=[[0,[1,0]]]).items():
        need(same(data[key],value),'layout metadata mismatch: '+key)
    row=(0,0);col=(1,0);pattern=tuple(tuple(sorted(pair)) for pair in zip(row,col))
    equal=[j for j in range(2) if row[j]==col[j]];copies=2**len(equal);occupied={}
    for edge in (0,1):
        index,copy=divmod(edge,copies);slot=0;copy_index=0
        for j in range(2):
            if row[j]==col[j]:bit=(copy>>copy_index)&1;copy_index+=1
            else:bit=int(row[j]>col[j])
            slot+=bit*2**j
        occupied.setdefault((pattern,index),[]).append((slot,edge))
    expected=[]
    for pattern in product(((0,0),(0,1),(1,1)),repeat=2):
        for index in range(4//2**sum(lo==hi for lo,hi in pattern)):
            expected.append(dict(pattern=pattern,index=index,slots=occupied.get((pattern,index),[])))
    need(same(data['packets'],expected),'independent direction/copy slot mismatch')
    return True


def produce(fixture=None,*,limits=Limits(max_work=1_000_000_000,max_seconds=600),check_children=False):
    fixture=FIXTURE if fixture is None else fixture
    graph=fixture_network(fixture);layout=fixture_layout();budget=Budget(limits);events=[]
    root_ring=Ring(2,19,2,budget);counts=Counter();start=monotonic()
    try:
        def point_value(node,z,ring):
            point=Point(4,node.t,z,node.precision,19,2)
            domain=DegreeCertifiedDomain(graph,layout,point,budget)
            children=[];oracle=PointOracle(fixture,node.precision,node.t,z) if check_children else None
            def leaf(child,p):
                budget.calls+=1;budget.max_depth=1
                value=direct(child,Ring(p,19,2,budget))
                # Every child carries the same complete beta in its packet recipes.
                recipe=child.vertices[-1].tensor;beta=recipe.beta;group=recipe.group
                if oracle:
                    selected=tuple((j,power) for j,power in enumerate(beta) if power)
                    if value!=oracle.child(selected,group):raise RuntimeError('independent child mismatch')
                budget.items((counts['children']+len(children)+1)*8,'child transcript scalar coordinates')
                children.append(value);return value
            budget.points+=1
            value=point_contraction(graph,layout,domain,ring,leaf,require_bounds=False)
            budget.items(len(events)+1,'point transcript')
            events.append(dict(t=node.t,precision=node.precision,multiplicity=node.multiplicity,zeta=z,
                certificate=domain.certificate(),children=children,result=value))
            counts['children']+=len(children)
            return value
        value=recover(2,2,2,root_ring,point_value,experimental_precision=True)
        report=dict(status='PASS_FINITE_FOUR_SLOT_RECOVERY',result=value,ledger=budget.report(),limits=asdict(limits),
                    active_levels=1,a=2,u=2,radix=2,
                    layout_policy='FIXED_COORDINATE_0_COLUMN_PERMUTATION',coordinate_1_occupied_modes=False,**FLAGS)
    except ResourceLimit as exc:
        report=dict(status='INCONCLUSIVE_RESOURCE_LIMIT',reason=str(exc),ledger=budget.report(),limits=asdict(limits),**FLAGS)
    return dict(schema='VERITAS_FOUR_SLOT_SUPPORT_V1',fixture=fixture,layout=layout_record(layout),report=report,events=events)


# Independent arithmetic: rational Cauchy polynomials, old extension-ring
# implementation, explicit affine coefficient extraction and Boolean sums.
def jetmul(a,b,r):return (r.mul(a[0],b[0]),r.add(r.mul(a[0],b[1]),r.mul(a[1],b[0])))
def jetadd(a,b,r):return tuple(r.add(x,y) for x,y in zip(a,b))


@lru_cache(None)
def weights():
    M,a,u=2,2,2;L=2**a;h=(3*M+u-1)//u
    nodes=[(t,(abs(t)&-abs(t)).bit_length()-1) for t in range(-L,L) if t]
    columns=[(t,j) for t,i in nodes if i<u for j in range(h*(u-i))]
    n=len(columns)
    matrix=[[Fraction(comb(k,j)*t**(k-j)*8**j) if k>=j else Fraction(0)
             for t,j in columns]+[Fraction(k==0)] for k in range(n)]
    for col in range(n):
        pivot=next(i for i in range(col,n) if matrix[i][col]);matrix[col],matrix[pivot]=matrix[pivot],matrix[col]
        d=matrix[col][col];matrix[col]=[x/d for x in matrix[col]]
        for i in range(n):
            if i!=col and matrix[i][col]:
                d=matrix[i][col];matrix[i]=[a-d*b for a,b in zip(matrix[i],matrix[col])]
    return tuple((t,j,matrix[k][-1]) for k,(t,j) in enumerate(columns))


def required_precision(t):
    return 2+max((w.denominator&-w.denominator).bit_length()-1 for node,j,w in weights() if node==t)


class PointOracle:
    def __init__(self,fixture,p,t,z):
        self.fixture=fixture;self.r=ExtensionRing(p,19);self.t=t;self.z=tuple(z)
        self.coordinate=(abs(t)&-abs(t)).bit_length()-1;self.B=2**(self.coordinate+1)
        self.packets=[]
        for first in ((0,0),(0,1),(1,1)):
            for second in ((0,0),(0,1),(1,1)):
                pattern=(first,second)
                for index in range(4//(2**(int(first[0]==first[1])+int(second[0]==second[1])))):
                    self.packets.append((pattern,index,((0,0),(2,1)) if (pattern,index)==(((0,1),(0,0)),0) else ()))
        self.active=[pid for pid,(pattern,_,_) in enumerate(self.packets) if pattern[self.coordinate][0]!=pattern[self.coordinate][1]]
        self.channels=len(self.active)*self.B
        self._kernel={};self._mode={}

    def kernel(self,x,y):
        if (x,y) in self._kernel:return self._kernel[x,y]
        r=self.r;coefficients=[Fraction(-1,144)]
        for root in range(-4,4):
            if root==y-x:continue
            out=[Fraction(0)]*(len(coefficients)+1)
            for j,c in enumerate(coefficients):out[j]-=root*c;out[j+1]+=c
            coefficients=out
        shifted=[sum(c*comb(j,k)*self.t**(j-k)*8**k for j,c in enumerate(coefficients) if j>=k)
                 for k in range(8)]
        value=r.zero
        for c in reversed(shifted):
            need(c.denominator%2==1,'nonintegral shifted kernel')
            value=r.add(r.mul(value,self.z),r.elem([c.numerator*pow(c.denominator,-1,r.modulus)]))
        self._kernel[x,y]=value;return value

    def mode(self,x,tile,b):
        key=x,tile,b
        if key not in self._mode:
            r=self.r;d=self.t-tile+x;v=(abs(d)&-abs(d)).bit_length()-1
            need(d!=0 and v<=self.coordinate,'crossing denominator')
            unit=r.add(r.elem([d//2**v]),r.mul(r.elem([8//2**v]),self.z))
            ratio=r.mul(r.elem([self.B//2**v]),r.inverse(unit))
            self._mode[key]=r.mul(self.kernel(x,tile),r.pow(ratio,b))
        return self._mode[key]

    def decode(self,index):
        b,channel=divmod(index,self.channels);rank,tile=divmod(channel,self.B)
        pid=self.active[rank];pair=self.packets[pid][0][self.coordinate]
        bit=(tile>>self.coordinate)&1
        return pid,tile,b,pair[1-bit],pair[bit]

    def selected(self):
        # Independently construct the coefficient support by Cartesian source
        # tiles and finite target degrees, not the producer's weighted odometer.
        candidates=[];capacities={}
        for index in range(self.channels*(self.r.p-1)):
            pid,tile,b,source,target=self.decode(index);pattern,_,slots=self.packets[pid]
            pair=pattern[self.coordinate]
            target_rows=[slot for slot,e in slots if pair[(slot>>self.coordinate)&1]==target]
            source_js=[slot//self.B for slot,e in slots if pair[1-((slot>>self.coordinate)&1)]==source and slot%self.B==tile]
            if target_rows and source_js and (b==0 or any(j!=0 for j in source_js)):
                candidates.append((index,b+1,(pid,target)));capacities[pid,target]=len(target_rows)
        # There is one active occupied packet at odd nodes and none at even.
        need(len(capacities)<=1,'oracle geometry scope')
        if not candidates:yield ();return
        need(next(iter(capacities.values()))==2,'target degree scope')
        combinations=[()]
        for i,(index,w,key) in enumerate(candidates):
            if w<self.r.p:combinations.append(((index,1),))
            if 2*w<self.r.p:combinations.append(((index,2),))
            for other,v,other_key in candidates[i+1:]:
                if w+v<self.r.p:combinations.append(((index,1),(other,1)))
        # Formal tuple lexicographic order: larger indices increment first.
        def dense(selected):
            values=dict(selected);return tuple(values.get(j,0) for j in range(self.channels*(self.r.p-1)))
        yield from sorted(combinations,key=dense)

    def child(self,selected,group):
        r=self.r;i=self.coordinate;labels={'row':(0,0),'column':(1,0)}
        variables=[(side,e) for side in ('row','column') for e in (0,1) if labels[side][i]==group]
        total=(r.zero,r.zero)
        modes=[(self.decode(index),power) for index,power in selected]
        for bits in product((0,1),repeat=len(variables)):
            assignment=dict(zip(variables,bits));term=(r.one,r.zero)
            for side in ('row','column'):
                if labels[side][i]==group:
                    index=assignment[side,0]+2*assignment[side,1]
                    term=jetmul(term,tuple(r.elem([c]) for c in self.fixture[side][index]),r)
            for pid,(pattern,_,slots) in enumerate(self.packets):
                rows=[(slot,e) for slot,e in slots if ('row',e) in assignment]
                cols=[(slot,e) for slot,e in slots if ('column',e) in assignment]
                targeted=[(mode,power) for mode,power in modes if mode[0]==pid and mode[4]==group]
                sourced=[(mode,power) for mode,power in modes if mode[0]==pid and mode[3]==group]
                if sum(power for _,power in targeted)>len(rows):term=(r.zero,r.zero);break
                source=r.one
                for (_,tile,b,_,_),power in sourced:
                    linear=sum((slot//self.B)**b*assignment['column',e] for slot,e in cols if slot%self.B==tile)
                    source=r.mul(source,r.elem([pow(linear,power,r.modulus)]))
                if source==r.zero:term=(r.zero,r.zero);break
                # Dictionary polynomial multiplication differs from production's
                # per-row choice-vector coefficient procedure.
                poly={(0,)*len(targeted):r.one}
                for slot,e in rows:
                    local=r.zero
                    for col,f in cols:
                        if assignment['column',f]:local=r.add(local,self.kernel(slot,col))
                    y=assignment['row',e];constant=local if y else r.sub(r.one,local)
                    coefficients=[constant]+[self.mode(slot,mode[1],mode[2]) if y else r.neg(self.mode(slot,mode[1],mode[2])) for mode,power in targeted]
                    out={}
                    for powers,value in poly.items():
                        for j,c in enumerate(coefficients):
                            key=list(powers)
                            if j:key[j-1]+=1
                            key=tuple(key);out[key]=r.add(out.get(key,r.zero),r.mul(value,c))
                    poly=out
                scalar=r.mul(source,poly.get(tuple(power for _,power in targeted),r.zero))
                term=tuple(r.mul(c,scalar) for c in term)
            total=jetadd(total,term,r)
        return total

    def half_edge(self):
        r=self.r;total=(r.zero,r.zero)
        for ys in product((0,1),repeat=2):
            for xs in product((0,1),repeat=2):
                term=jetmul(tuple(r.elem([c]) for c in self.fixture['row'][ys[0]+2*ys[1]]),
                            tuple(r.elem([c]) for c in self.fixture['column'][xs[0]+2*xs[1]]),r)
                for e,y in enumerate(ys):
                    scalar=r.zero
                    for f,x in enumerate(xs):
                        if x:scalar=r.add(scalar,self.kernel(2*e,2*f))
                    if not y:scalar=r.sub(r.one,scalar)
                    term=tuple(r.mul(c,scalar) for c in term)
                total=jetadd(total,term,r)
        return total


def canonical(value,p):
    need(isinstance(value,(list,tuple)) and len(value)==2 and all(isinstance(row,(list,tuple)) and len(row)==4
        and all(type(c) is int and 0<=c<2**p for c in row) for row in value),'noncanonical scalar jet')
    return tuple(map(tuple,value))


def replay(certificate,*,max_seconds=600):
    started=monotonic()
    need(set(certificate)=={'schema','fixture','layout','report','events'},'certificate fields')
    need(certificate['schema']=='VERITAS_FOUR_SLOT_SUPPORT_V1','schema')
    verify_layout_record(certificate['layout'])
    fixture=certificate['fixture'];need(type(fixture) is dict and set(fixture)=={'row','column'},'fixture fields')
    for table in fixture.values():
        need(type(table) is list and len(table)==4 and all(type(row) is list and len(row)==2
            and all(type(c) is int and 0<=c<4 for c in row) for row in table),'fixture table')
    report=certificate['report']
    need(type(report) is dict and set(report)==set(FLAGS)|{'status','result','ledger','limits','active_levels','a','u','radix','layout_policy','coordinate_1_occupied_modes'},'report fields')
    need(report.get('status')=='PASS_FINITE_FOUR_SLOT_RECOVERY','producer incomplete')
    limits=report['limits']
    need(type(limits) is dict and set(limits)=={'max_work','max_seconds','max_items','max_integer_bits'},'limit fields')
    for key,value in limits.items():
        need(value is None or (type(value) in ((int,float) if key=='max_seconds' else (int,)) and isfinite(value) and value>0),'invalid recorded resource limit')
    for key in FLAGS:need(report.get(key) is False,'unsupported qualification')
    for key,value in {'active_levels':1,'a':2,'u':2,'radix':2}.items():
        need(type(report.get(key)) is int and report[key]==value,'policy mismatch')
    need(report.get('layout_policy')=='FIXED_COORDINATE_0_COLUMN_PERMUTATION' and report.get('coordinate_1_occupied_modes') is False,'layout policy')
    events=certificate['events'];need(type(events) is list and len(events)==90,'complete point inventory required')
    counts=Counter();position=0
    for t in (-3,-2,-1,1,2,3):
        p=required_precision(t);odd=abs(t)%2==1;channels=16 if odd else 32
        expected_certificate=dict(schema='PACKET_SOURCE_AND_TARGET_DEGREE_ZERO_V1',
            eligible_modes=[b*16 for b in range(p-1)] if odd else [],
            target_capacities=[[4,0,2]] if odd else [],
            formal_channels_per_weight=channels,formal_mode_count=channels*(p-1),
            families=['EMPTY_SOURCE_TILE','POSITIVE_EXPONENT_WITH_ONLY_J_ZERO','TOTAL_POWER_EXCEEDS_TARGET_ROW_COUNT'])
        for number in range(15):
            if monotonic()-started>max_seconds:raise ReplayError('INCONCLUSIVE_RESOURCE_LIMIT: replay wall cap')
            event=events[position];position+=1;z=tuple((number>>j)&1 for j in range(4))
            need(set(event)=={'t','precision','multiplicity','zeta','certificate','children','result'},'point fields')
            for key,value in dict(t=t,precision=p,multiplicity=6 if odd else 3,zeta=z,certificate=expected_certificate).items():
                need(same(event[key],value),'point metadata or support certificate mismatch: '+key)
            oracle=PointOracle(fixture,p,t,z);children=event['children'];need(type(children) is list,'child list')
            total=(oracle.r.zero,oracle.r.zero);cursor=0
            for selected in oracle.selected():
                term=(oracle.r.one,oracle.r.zero)
                for group in (0,1):
                    if monotonic()-started>max_seconds:raise ReplayError('INCONCLUSIVE_RESOURCE_LIMIT: replay wall cap')
                    need(cursor<len(children),'missing child')
                    expected=oracle.child(selected,group)
                    need(canonical(children[cursor],p)==expected,'independent child value mismatch')
                    term=jetmul(term,expected,oracle.r);cursor+=1;counts['children']+=1
                if selected and term!=(oracle.r.zero,oracle.r.zero):
                    counts['nonzero_terms']+=1
                    if any(index//channels>0 for index,power in selected):counts['nonzero_higher_geometric_terms']+=1
                    if any(power>1 for index,power in selected):counts['nonzero_power_above_one_terms']+=1
                total=jetadd(total,term,oracle.r);counts['tuples']+=1
            need(cursor==len(children),'extra child')
            need(canonical(event['result'],p)==total==oracle.half_edge(),'independent half-edge point mismatch')
            counts['points']+=1
    integer=[0,0]
    for index in range(4):
        a,b=fixture['row'][index];c,d=fixture['column'][index]
        integer[0]+=a*c;integer[1]+=a*d+b*c
    expected=tuple((c%4,0,0,0) for c in integer)
    need(canonical(report.get('result'),2)==expected,'integer contraction mismatch')
    ledger=report['ledger']
    need(type(ledger) is dict and set(ledger)=={'work_units','elapsed_seconds','calls','interpolation_points','exponent_tuples','maximum_depth','bit_operations','hard_memory_limit_enforced'},'ledger fields')
    need(type(ledger['work_units']) is int and ledger['work_units']>0 and (limits['max_work'] is None or ledger['work_units']<=limits['max_work']),'invalid work accounting')
    need(type(ledger['elapsed_seconds']) in (int,float) and isfinite(ledger['elapsed_seconds']) and ledger['elapsed_seconds']>=0,'invalid elapsed time')
    need(ledger['hard_memory_limit_enforced'] is False,'unsupported memory claim')
    for key,value in dict(calls=counts['children'],interpolation_points=90,exponent_tuples=counts['tuples'],maximum_depth=1).items():
        need(type(ledger.get(key)) is int and ledger[key]==value,'ledger mismatch')
    need(ledger.get('bit_operations') is None,'unsupported instrumentation claim')
    return dict(status='PASS_INDEPENDENT_FOUR_SLOT_REPLAY',integer_jet=integer,modular_jet=[c%4 for c in integer],
                independently_checked_children=counts['children'],checked_points=90,retained_tuples=counts['tuples'],
                nonzero_higher_geometric_terms=counts['nonzero_higher_geometric_terms'],
                nonzero_power_above_one_terms=counts['nonzero_power_above_one_terms'],
                node_precisions=[9,35],active_levels=1,**FLAGS)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--installed',action='store_true')
    parser.add_argument('--output-dir',type=Path);parser.add_argument('--replay',type=Path);args=parser.parse_args()
    if args.installed:
        from veritas.research.manuscript import certified_modes
        if ROOT/'src' in Path(certified_modes.__file__).resolve().parents:parser.error('checkout imported')
    if args.replay:
        if args.replay.stat().st_size>20_000_000:parser.error('certificate byte cap')
        print(json.dumps(replay(json.loads(args.replay.read_text())),indent=2));return
    if not args.output_dir:parser.error('--output-dir or --replay required')
    out=args.output_dir.resolve()
    if out==ROOT or ROOT in out.parents:parser.error('external evidence required')
    out.mkdir(parents=True,exist_ok=True);certificate=produce()
    (out/'four_slot_certificate.json').write_text(json.dumps(certificate,separators=(',',':'))+'\n')
    if certificate['report']['status']!='PASS_FINITE_FOUR_SLOT_RECOVERY':
        print(json.dumps(certificate['report'],indent=2));raise SystemExit(2)
    result=replay(certificate);(out/'independent_four_slot_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
