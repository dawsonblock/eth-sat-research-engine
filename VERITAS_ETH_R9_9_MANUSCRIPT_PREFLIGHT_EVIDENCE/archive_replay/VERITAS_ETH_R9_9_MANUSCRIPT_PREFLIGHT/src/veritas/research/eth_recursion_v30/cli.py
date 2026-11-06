"""CLI for finite extension-ring implicit child tensors and certificate replay."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from .implicit_children import make_bipartite_edges,make_child_certificate,check_child_certificate


def main(argv=None):
    parser=argparse.ArgumentParser(description='v3.0 finite implicit child tensors; NOT the ETH subexponential recursion')
    sub=parser.add_subparsers(dest='command',required=True)
    demo=sub.add_parser('construct',help='generate and self-check finite child certificate')
    demo.add_argument('--n',type=int,default=2)
    demo.add_argument('--clauses-json',default='[[1,2]]')
    demo.add_argument('--a',type=int,default=1)
    demo.add_argument('--radix',type=int,default=2)
    demo.add_argument('--node',type=int,default=1)
    demo.add_argument('--precision',type=int,default=8)
    demo.add_argument('--extension-degree',type=int,default=4)
    demo.add_argument('--jet-length',type=int,default=3)
    demo.add_argument('--max-assignments',type=int,default=250_000)
    demo.add_argument('--output',help='save complete replay certificate JSON')
    verify=sub.add_parser('check',help='independently replay a saved certificate')
    verify.add_argument('--certificate',required=True)
    args=parser.parse_args(argv)
    if args.command=='check':
        cert=json.loads(Path(args.certificate).read_text(encoding='utf-8'))
        result=check_child_certificate(cert)
        print(json.dumps(result,indent=2))
        return 0 if result['valid'] else 1
    clauses=json.loads(args.clauses_json)
    net=from_cnf(CNF.from_lists(args.n,clauses),max_degree=12)
    base=construct_d3_packing(make_bipartite_edges(net),r=args.radix,a=args.a,
                               max_work=150_000,max_packets=256)
    cert=make_child_certificate(net,base,node=args.node,precision=args.precision,
               extension_degree=args.extension_degree,jet_length=args.jet_length,
               max_assignments=args.max_assignments)
    verdict=check_child_certificate(cert,max_assignments=args.max_assignments)
    if not verdict['valid']:
        raise ArithmeticError('independent replay rejected output: '+str(verdict))
    if args.output:
        Path(args.output).write_text(json.dumps(cert,indent=2),encoding='utf-8')
    print(json.dumps({'verdict':verdict,'result':cert['result'],
        'children':cert['children'],'saved_certificate':args.output,
        'scope':cert['scope']},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
