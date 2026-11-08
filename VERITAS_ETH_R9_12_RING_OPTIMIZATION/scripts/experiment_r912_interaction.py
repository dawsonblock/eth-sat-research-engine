"""Fully nonconstant degree-three graphs and a separate integer elimination oracle."""
import argparse
from dataclasses import replace
from itertools import product
from pathlib import Path
import random
from time import monotonic
from veritas.research.parent_child_r98.model import Budget,PacketLayout,canonical
from veritas.research.parent_child_r98.packing import audit_layout
from veritas.research.parent_child_r98.shrinking_cli import load_input,_check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import construct_vertex_shrinking_layout
from veritas.research.parent_child_r910.engine import contract
from veritas.research.parent_child_r910.checker import verify
from veritas.research.independent_r82.point_mode_oracle import OracleLimits


def graph(n=32,offset=5):
    if n<3 or len({0,1,offset%n})!=3:raise ValueError('three distinct incidences required')
    edges=[(r,(r+d)%n) for r in range(n) for d in (0,1,offset%n)]
    rng=random.Random(912+n+offset);vertices=[]
    for side in (0,1):
        for v in range(n):
            ports=[e for e,pair in enumerate(edges) if pair[side]==v]
            # All three flattenings must have rank >1, so no port is a scalar factor.
            while True:
                table=[rng.randrange(1,5) for _ in range(8)]
                if all(any(table[i]*table[j|1<<bit]!=table[j]*table[i|1<<bit]
                    for i in range(8) for j in range(8) if not (i|j)&1<<bit) for bit in range(3)):break
            vertices.append({'side':'column' if side else 'row','ports':ports,'table':table})
    return {'root_s':4*n,'edges':3*n,'precision':512,'extension_degree':10,'vertices':vertices}


def integer_elimination(data,max_work=50_000_000,max_frontier=18):
    """Exact Python integer sum-product; no tensor executor or modular arithmetic."""
    factors=[(tuple(v['ports']),list(v['table'])) for v in data['vertices']]
    work=width=peak=0;started=monotonic()
    while any(scope for scope,_ in factors):
        all_vars={v for scope,_ in factors for v in scope}
        scope_for={v:set().union(*(set(s) for s,_ in factors if v in s)) for v in all_vars}
        v=min(all_vars,key=lambda x:(len(scope_for[x]),x));joined=[(s,t) for s,t in factors if v in s]
        remaining=tuple(sorted(scope_for[v]-{v}));width=max(width,len(remaining))
        if width>max_frontier:raise RuntimeError('independent integer frontier cap')
        output=[]
        for assignment in range(1<<len(remaining)):
            env={x:(assignment>>j)&1 for j,x in enumerate(remaining)};total=0
            for bit in (0,1):
                env[v]=bit;term=1
                for scope,table in joined:
                    term*=table[sum(env[x]<<j for j,x in enumerate(scope))];work+=1
                total+=term
            output.append(total)
            if work>max_work or monotonic()-started>120:raise RuntimeError('independent integer work/time cap')
        factors=[(s,t) for s,t in factors if v not in s]+[(remaining,output)]
        peak=max(peak,sum(len(t) for _,t in factors))
    answer=1
    for _,table in factors:answer*=table[0]
    return {'status':'PASS_INDEPENDENT_INTEGER_ELIMINATION','integer':answer,
        'work_units':work,'max_frontier_bits':width,'peak_table_entries':peak,'elapsed_seconds':monotonic()-started}


def separated_layout(parent,a,u,budget):
    if (a,u)!=(1,1):raise ValueError('probe uses a=u=1')
    n=parent.edge_count//3
    if n!=32:raise ValueError('32+32 vertices required for singleton child groups')
    src=construct_vertex_shrinking_layout(parent,budget=budget).source
    src['row_labels']={str(i):[i] for i in range(n)}
    src['column_labels']={str(i):[n+i] for i in range(n)}
    src['H_pad']=2
    src['packets']=sorted([{'symbol_pairs':[[r,n+c]],'index':0,'occupied_slots':[[0,e]]}
        for e,(r,c) in enumerate(parent.bipartite_edges())],key=lambda p:p['symbol_pairs'])
    result=PacketLayout(parent.content_digest,1,1,canonical(src),'balanced_vertices')
    assert audit_layout(parent,result)['group_load_bound_met']
    return result


def eliminate_and_compare(parent,ref,budget):
    """Separately classified exact elimination; never a recursive or source result."""
    from veritas.research.parent_child_r912.routes import Route,contract_routed
    report=contract_routed(parent,route=Route.ELIMINATION,elimination_budget=budget)
    if report['status']=='PASS_EXACT_BOUNDED_WIDTH_ELIMINATION':
        report['matches_independent_integer_reference']=(report['result'][0][0]==ref['integer'] and
            not any(report['result'][0][1:]) and not any(map(any,report['result'][1:])))
    return report


def main():
    from veritas.research.parent_child_r912.elimination import EliminationBudget
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--max-work',type=int,default=3000000);ap.add_argument('--offset',type=int,default=5)
    ap.add_argument('--elimination-max-width',type=int,default=20)
    ap.add_argument('--reference-max-frontier',type=int,default=18)
    ap.add_argument('--skip-recursive',action='store_true');args=ap.parse_args()
    _check_output(args.output_dir);args.output_dir.mkdir(parents=True,exist_ok=False)
    data=graph(32,args.offset);source=args.output_dir/'input.json';source.write_bytes(canonical(data));parent=load_input(source,max_extension_degree=12)
    ref=integer_elimination(data,max_frontier=args.reference_max_frontier);(args.output_dir/'reference.json').write_bytes(canonical(ref))
    routed=eliminate_and_compare(parent,ref,EliminationBudget(max_width=args.elimination_max_width))
    (args.output_dir/'elimination.json').write_bytes(canonical(routed))
    print(routed['status'],routed.get('elimination_width'),routed.get('matches_independent_integer_reference'))
    if routed['status'].startswith('PASS'):assert routed['matches_independent_integer_reference']
    if args.skip_recursive:return
    policy=replace(DEFAULT_SHRINKING_POLICY,max_work=args.max_work,max_seconds=600,max_certificate_bytes=100000000)
    oracle=OracleLimits(100000000,600)
    with (args.output_dir/'events.jsonl').open('xb') as stream:
        report=contract(parent,schedule=((1,1),),policy=policy,oracle_limits=oracle,max_points=4096,
            layout_factory=separated_layout,coefficient_encoding=True,compressed_records=True,
            evidence_sink=lambda raw:stream.write(raw+b'\n'))
    (args.output_dir/'report.json').write_bytes(canonical(report))
    if report['status'].startswith('PASS'):
        with (args.output_dir/'events.jsonl').open('rb') as stream:
            checked=verify(parent,(line.rstrip(b'\n') for line in stream),report,policy=policy,oracle_limits=oracle)
        (args.output_dir/'verification.json').write_bytes(canonical(checked))
        assert checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
        assert report['result'][0][0]==ref['integer'] and not any(report['result'][0][1:])
    print(report['status'])


if __name__=='__main__':main()
