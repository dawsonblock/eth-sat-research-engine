"""CLI: bounded geometric extension-ring modes and finite scalar children."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from .jet_tiles import make_jet_tile_modes,check_jet_tile_modes,contract_mode_children,check_mode_child_certificate


def main(argv=None):
    ap=argparse.ArgumentParser(description='Finite D.4.4 geometric jet-mode + scalar child reference; NOT a subexponential solver')
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
        verdict=check_mode_child_certificate(cert)
        print(json.dumps(verdict,indent=2))
        return 0 if verdict['valid'] else 1
    net=from_cnf(CNF.from_lists(args.n,json.loads(args.clauses_json)))
    d3=construct_d3_packing(make_bipartite_edges(net),r=args.radix,a=args.a,max_packets=256)
    modes=make_jet_tile_modes(d3,node=args.node,precision=args.precision,extension_degree=args.extension_degree,jet_length=args.jet_length)
    check_modes=check_jet_tile_modes(modes)
    if not check_modes['valid']:raise ArithmeticError('mode checker rejected certificate')
    cert=contract_mode_children(net,modes)
    verified=check_mode_child_certificate(cert)
    if not verified['valid']:raise ArithmeticError('child certificate checker rejected result')
    if args.output:
        Path(args.output).write_text(json.dumps(cert,indent=2),encoding='utf-8')
    print(json.dumps({'verdict':verified,'modes':check_modes,'result':cert['result'],
            'children':cert['children'],'saved_certificate':args.output},indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
