"""Command line v3.3 bounded recursive mode-bond reference."""
import argparse,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from .recursive import construct_recursive_certificate,check_recursive_certificate

def main(argv=None):
    parser=argparse.ArgumentParser(description='Exact bounded recursive mode bonds; no ETH complexity claim')
    sub=parser.add_subparsers(dest='command',required=True)
    c=sub.add_parser('construct')
    c.add_argument('--n',type=int,default=2)
    c.add_argument('--clauses-json',default='[[1,2]]')
    c.add_argument('--node',type=int,default=1)
    c.add_argument('--precision',type=int,default=5)
    c.add_argument('--jet-length',type=int,default=2)
    c.add_argument('--extension-degree',type=int,default=3)
    c.add_argument('--output')
    v=sub.add_parser('check');v.add_argument('--certificate',required=True)
    args=parser.parse_args(argv)
    if args.command=='check':
        res=check_recursive_certificate(json.loads(Path(args.certificate).read_text(encoding='utf-8')))
        print(json.dumps(res,indent=2));return 0 if res['valid'] else 1
    net=from_cnf(CNF.from_lists(args.n,json.loads(args.clauses_json)))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_jet_tile_modes(d3,node=args.node,precision=args.precision,
        extension_degree=args.extension_degree,jet_length=args.jet_length)
    cert=construct_recursive_certificate(net,modes)
    result=check_recursive_certificate(cert)
    if not result['valid']:raise ArithmeticError(result['reason'])
    if args.output:Path(args.output).write_text(json.dumps(cert,indent=2),encoding='utf-8')
    print(json.dumps({'verdict':result,'result':cert['result'],
        'stats':cert['stats'],'saved_certificate':args.output},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
