"""CLI for the exact finite, group-local D.4.4 child reference."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from .children import construct_child_reference,verify_child_reference

def main():
    parser=argparse.ArgumentParser(description='Finite D.4.4 group-local child reference (no ETH complexity proof)')
    sub=parser.add_subparsers(dest='command',required=True)
    con=sub.add_parser('construct')
    con.add_argument('--n',type=int,default=2)
    con.add_argument('--clauses-json',default='[[1,2]]')
    con.add_argument('--node',type=int,default=1)
    con.add_argument('--precision',type=int,default=5)
    con.add_argument('--jet-length',type=int,default=2)
    con.add_argument('--extension-degree',type=int,default=3)
    con.add_argument('--output',default='d44-child.json')
    chk=sub.add_parser('check')
    chk.add_argument('--certificate',required=True)
    args=parser.parse_args()
    if args.command=='construct':
        clauses=json.loads(args.clauses_json)
        net=from_cnf(CNF.from_lists(args.n,clauses))
        packing=construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
        modes=make_jet_tile_modes(packing,node=args.node,precision=args.precision,
            jet_length=args.jet_length,extension_degree=args.extension_degree)
        result=construct_child_reference(net,modes)
        check=verify_child_reference(result)
        if not check['valid']:raise RuntimeError(check)
        Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({'status':check['status'], 'result':result['result'],
            'children':result['children'],'output':args.output,
            'subexponential_runtime_proven':False},indent=2))
    else:
        result=verify_child_reference(json.loads(Path(args.certificate).read_text(encoding='utf-8')))
        print(json.dumps(result,indent=2))
        if not result['valid']:raise SystemExit(1)

if __name__=='__main__':main()
