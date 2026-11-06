"""Verified finite mode-bond child scope CLI; not a D.4.4 theorem proof."""
import argparse,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from .network import construct_child_network_certificate,check_child_network_certificate

def main(argv=None):
    p=argparse.ArgumentParser(description='Exact finite child mode-bond network scopes')
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('construct')
    c.add_argument('--n',type=int,default=2)
    c.add_argument('--clauses-json',default='[[1,2]]')
    c.add_argument('--radix',type=int,default=2)
    c.add_argument('--a',type=int,default=1)
    c.add_argument('--node',type=int,default=1)
    c.add_argument('--precision',type=int,default=5)
    c.add_argument('--extension-degree',type=int,default=3)
    c.add_argument('--jet-length',type=int,default=2)
    c.add_argument('--max-child-scope',type=int,default=64)
    c.add_argument('--output')
    v=sub.add_parser('check');v.add_argument('--certificate',required=True)
    args=p.parse_args(argv)
    if args.command=='check':
        verdict=check_child_network_certificate(json.loads(Path(args.certificate).read_text()))
        print(json.dumps(verdict,indent=2));return 0 if verdict['valid'] else 1
    net=from_cnf(CNF.from_lists(args.n,json.loads(args.clauses_json)))
    d3=construct_d3_packing(make_bipartite_edges(net),r=args.radix,a=args.a,max_packets=256)
    modes=make_jet_tile_modes(d3,node=args.node,precision=args.precision,
        extension_degree=args.extension_degree,jet_length=args.jet_length)
    cert=construct_child_network_certificate(net,modes,max_child_scope=args.max_child_scope)
    verdict=check_child_network_certificate(cert)
    if not verdict['valid']:raise ArithmeticError(verdict['reason'])
    if args.output:Path(args.output).write_text(json.dumps(cert,indent=2))
    print(json.dumps({'checker':verdict,'summary':cert['model']['summary'],'certificate':args.output},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
