"""CLI for bounded v3.2 mode-bond tensor construction and replay."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from .bonds import construct_bond_certificate,check_bond_certificate

def main(argv=None):
    ap=argparse.ArgumentParser(description='Bounded exact v3.2 mode-index bond networks; NOT a subexponential algorithm')
    sub=ap.add_subparsers(dest='command',required=True)
    make=sub.add_parser('construct')
    make.add_argument('--n',type=int,default=2)
    make.add_argument('--clauses-json',default='[[1,2]]')
    make.add_argument('--radix',type=int,default=2)
    make.add_argument('--a',type=int,default=1)
    make.add_argument('--node',type=int,default=1)
    make.add_argument('--precision',type=int,default=5)
    make.add_argument('--extension-degree',type=int,default=3)
    make.add_argument('--jet-length',type=int,default=2)
    make.add_argument('--output')
    check=sub.add_parser('check')
    check.add_argument('--certificate',required=True)
    args=ap.parse_args(argv)
    if args.command=='check':
        cert=json.loads(Path(args.certificate).read_text(encoding='utf-8'))
        verdict=check_bond_certificate(cert)
        print(json.dumps(verdict,indent=2))
        return 0 if verdict['valid'] else 1
    net=from_cnf(CNF.from_lists(args.n,json.loads(args.clauses_json)))
    d3=construct_d3_packing(make_bipartite_edges(net),r=args.radix,a=args.a,max_packets=256)
    modes=make_jet_tile_modes(d3,node=args.node,precision=args.precision,
                              extension_degree=args.extension_degree,jet_length=args.jet_length)
    cert=construct_bond_certificate(net,modes)
    verdict=check_bond_certificate(cert)
    if not verdict['valid']:raise ArithmeticError('bond network checker rejected result')
    if args.output:Path(args.output).write_text(json.dumps(cert,indent=2),encoding='utf-8')
    print(json.dumps({'verdict':verdict,'result':cert['result'],
        'stats':cert['stats'],'saved_certificate':args.output},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
