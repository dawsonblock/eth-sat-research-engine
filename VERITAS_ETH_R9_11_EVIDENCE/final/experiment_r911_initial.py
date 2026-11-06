"""Bounded coupled-core and row-density experiments; no general release gate.

The cycle has a rank-two interacting core. Unless --all-columns is supplied,
constant tensors outside that core are padding. Even all-column cases have
constant rows and bounded graph width; they are not hard general networks.
"""
import argparse
from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from veritas.research.parent_child_r98.model import Budget, PacketLayout, canonical
from veritas.research.parent_child_r98.shrinking_cli import load_input, _check_output
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r98.shrinking_layout import (
    construct_vertex_shrinking_layout, construct_shrinking_layout, audit_vertex_shrinking_layout)
from veritas.research.parent_child_r99.row_degree import certify_row_degree
from veritas.research.parent_child_r910.engine import contract
from veritas.research.parent_child_r910.checker import verify
from veritas.research.parent_child_r910.reference import matching_reference
from veritas.research.independent_r82.point_mode_oracle import OracleLimits
from veritas.research.tapered_v4.provenance import source_binding


def cycle_input(n=242, active_rows=2, all_columns=False):
    if type(n) is not int or not 2 <= n <= 242 or not 2 <= active_rows <= n:
        raise ValueError('bounded cycle with at least two active rows required')
    rows = [{'side':'row', 'ports':[2*i,2*i+1],
             'table':([2,1,1,3] if i%2==0 else [3,1,2,2]) if i<active_rows else [1]*4}
            for i in range(n)]
    cols = [{'side':'column','ports':[2*i+1,2*((i+1)%n)],
             'table':[1,2,3,5] if all_columns or i<active_rows-1 else [1]*4}
            for i in range(n)]
    # Field covers the root and all 44-wire descendants (<=22 active ports).
    degree = max(4, (6*active_rows).bit_length(), 7 if all_columns else 4)
    return {'root_s':1024,'precision':1024 if all_columns else 512,
            'extension_degree':degree,'edges':2*n,'vertices':rows+cols}


def cycle_reference(data):
    """Integer trace of ordered 2x2 factors; no engine or recipe arithmetic."""
    n = data['edges']//2
    rows = [v for v in data['vertices'] if v['side']=='row']
    cols = [v for v in data['vertices'] if v['side']=='column']
    if len(rows)!=n or len(cols)!=n or any(len(v['table'])!=4 for v in rows+cols):
        raise ValueError('cycle oracle dimensions')
    matrix = [[1,0],[0,1]]
    determinants = []
    for i,(row,col) in enumerate(zip(rows,cols)):
        if row['ports'] != [2*i,2*i+1] or col['ports'] != [2*i+1,2*((i+1)%n)]:
            raise ValueError('cycle oracle incidence')
        for vertex in (row,col):
            t = vertex['table']
            factor = [[t[a+2*b] for b in range(2)] for a in range(2)]
            determinants.append(t[0]*t[3]-t[1]*t[2])
            matrix = [[sum(matrix[a][c]*factor[c][b] for c in range(2))
                       for b in range(2)] for a in range(2)]
    integer = matrix[0][0]+matrix[1][1]
    return {'method':'INTEGER_2_BY_2_TRANSFER_TRACE','unreduced_integer':integer,
            'result':((integer % (1<<data['precision']),)+(0,)*(data['extension_degree']-1),),
            'rank_two_vertices':sum(d!=0 for d in determinants),
            'all_vertices_rank_two':all(d!=0 for d in determinants),
            'source_qualified':False}


def exhaustive_reference(data):
    if data['edges']>16:
        raise ValueError('exhaustive reference cap')
    total=0
    for bits in product((0,1),repeat=data['edges']):
        term=1
        for vertex in data['vertices']:
            term *= vertex['table'][sum(bits[e]<<i for i,e in enumerate(vertex['ports']))]
        total += term
    return total


def shifted_cycle_layout(parent,budget):
    if parent.edge_count!=484:
        raise ValueError('shifted two-level experiment requires 484 wires')
    base=construct_vertex_shrinking_layout(parent,budget=budget)
    src=base.source
    src['row_labels']={str(i):[i//11] for i in range(242)}
    src['column_labels']={str(i):[(i//11+11)%22] for i in range(242)}
    counts={}; packets=[]
    for edge,(row,col) in enumerate(parent.bipartite_edges()):
        rg,cg=src['row_labels'][str(row)][0],src['column_labels'][str(col)][0]
        pair=min(rg,cg),max(rg,cg)
        if rg==cg:
            raise ValueError('descendant components require crossing root edges')
        index=counts.get(pair,0); counts[pair]=index+1
        packets.append({'symbol_pairs':[list(pair)],'index':index,'occupied_slots':[[int(rg>cg),edge]]})
    src['packets']=sorted(packets,key=lambda p:(p['symbol_pairs'],p['index']))
    src['H_pad']=2*((max(counts.values())+1)//2)
    layout=PacketLayout(parent.content_digest,1,1,canonical(src),base.strategy)
    audit_vertex_shrinking_layout(parent,layout)
    return layout


def matching_input(b):
    if type(b) is not int or not 1<=b<=242:
        raise ValueError('nonconstant row count must be 1..242')
    return {'root_s':1024,'precision':1024,'extension_degree':max(3,(3*b).bit_length()),
            'edges':242,'vertices':[
                {'side':side,'ports':[e], 'table':table if e<b else [1,1]}
                for side,table in [('row',[1,3]),('column',[2,5])] for e in range(242)]}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--kind',choices=('cycle','matching'),default='cycle')
    parser.add_argument('--active-rows',type=int,default=2)
    parser.add_argument('--all-columns',action='store_true')
    parser.add_argument('--max-work',type=int,default=100_000_000)
    parser.add_argument('--max-seconds',type=int,default=300)
    parser.add_argument('--oracle-max-work',type=int,default=20_000_000)
    parser.add_argument('--cache-bytes',type=int,default=1_000_000)
    parser.add_argument('--plan-only',action='store_true')
    args=parser.parse_args(argv)
    policy=replace(DEFAULT_SHRINKING_POLICY,max_work=args.max_work,max_seconds=args.max_seconds)
    oracle=OracleLimits(args.oracle_max_work,args.max_seconds)
    _check_output(args.output_dir)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    data=cycle_input(active_rows=args.active_rows,all_columns=args.all_columns) if args.kind=='cycle' else matching_input(args.active_rows)
    path=args.output_dir/'input.json'; path.write_bytes(canonical(data))
    parent=load_input(path,max_extension_degree=12)
    budget=Budget(policy)
    root_layout=shifted_cycle_layout(parent,budget) if args.kind=='cycle' else construct_vertex_shrinking_layout(parent,budget=budget)
    degree=certify_row_degree(parent,1,budget=budget)
    reference=cycle_reference(data) if args.kind=='cycle' else matching_reference(parent)
    (args.output_dir/'reference.json').write_bytes(canonical(reference))
    plan={'schema':'VERITAS_R911_BOUNDED_EXPERIMENT_V1', 'kind':args.kind,
        'implementation_source_sha256':source_binding()['digest'],
        'driver_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'input_sha256':sha256(path.read_bytes()).hexdigest(),
        'root_layout':root_layout.source, 'degree_certificate':degree,
        'root_expected_samples':2*(degree['degree_bound']+1),
        'root_nonconstant_rows':args.active_rows,
        'structurally_connected':args.kind=='cycle',
        'constant_row_padding':args.active_rows<242,
        'descendant_strategy':'balanced_components' if args.kind=='cycle' else 'balanced_vertices',
        'total_work_bound':'NOT_ESTABLISHED', 'source_qualified':False,
        'policy':{'max_work':args.max_work,'max_seconds':args.max_seconds,'oracle':oracle.record()},
        'status':'NOT_RUN_PLAN_ONLY' if args.plan_only else 'PLANNED'}
    (args.output_dir/'plan.json').write_bytes(canonical(plan))
    if args.plan_only:
        print(plan['status']); return 0
    def factory(call,a,u,budget):
        if call.depth==parent.depth:
            return root_layout
        return (construct_shrinking_layout if args.kind=='cycle' else construct_vertex_shrinking_layout)(call,budget=budget)
    with (args.output_dir/'events.jsonl').open('xb') as out:
        report=contract(parent,schedule=((1,1),(1,1)),policy=policy,oracle_limits=oracle,
            max_points=4096,cache_bytes=args.cache_bytes,layout_factory=factory,
            preflight_work=budget.work,evidence_sink=lambda raw:out.write(raw+b'\n'))
    (args.output_dir/'report.json').write_bytes(canonical(report))
    checked=None
    if report['status']=='PASS_FINITE_TWO_LEVEL_CAPABLE_RECURSION':
        with (args.output_dir/'events.jsonl').open('rb') as stream:
            checked=verify(parent,(line.rstrip(b'\n') for line in stream),report,policy=policy,oracle_limits=oracle)
        (args.output_dir/'verification.json').write_bytes(canonical(checked))
    passed=(checked is not None and checked['status']=='PASS_INDEPENDENT_NUMERICAL_REPLAY'
        and canonical(report['result'])==canonical(reference['result'])
        and report['active_calls_by_depth'].get('1',0)>0
        and report['largest_deformation_degree_by_depth'].get('1',0)>0)
    summary={'status':'PASS_BOUNDED_TWO_LEVEL_REFERENCE_AND_REPLAY' if passed else report['status']
        if checked is None else 'INCONCLUSIVE_EXPERIMENT', 'independent_reference_matches':
        canonical(report.get('result'))==canonical(reference['result']),
        'two_active_levels_and_nonconstant_descendant':passed,
        'source_qualified':False,'constant_row_padding':args.active_rows<242,
        'general_connected_gate':'NOT_ESTABLISHED'}
    (args.output_dir/'summary.json').write_bytes(canonical(summary))
    print(summary['status']); return 0 if passed else 2


if __name__=='__main__':
    raise SystemExit(main())
