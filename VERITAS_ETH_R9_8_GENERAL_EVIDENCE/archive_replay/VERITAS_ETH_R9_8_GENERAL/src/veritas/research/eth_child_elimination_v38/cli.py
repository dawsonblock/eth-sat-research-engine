"""Standalone source-replayable D.4.4 finite child elimination."""
import argparse
import json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from .engine import construct_elimination_reference, verify_elimination_reference

def _int_range(low, high):
    def parse(value):
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError('expected an integer') from exc
        if not low <= parsed <= high:
            raise argparse.ArgumentTypeError(f'must be in {low}..{high}')
        return parsed
    return parse

def main():
    p = argparse.ArgumentParser(description='Finite exact D.4.4 child elimination, NOT an ETH theorem proof')
    sub = p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('construct')
    c.add_argument('--n',type=int,default=2)
    c.add_argument('--clauses-json',default='[[1,2]]')
    c.add_argument('--node',type=int,default=1)
    c.add_argument('--precision',type=int,default=5)
    c.add_argument('--extension-degree',type=int,default=3)
    c.add_argument('--jet-length',type=int,default=2)
    c.add_argument('--max-entries',type=_int_range(2,32768),default=1024)
    c.add_argument('--max-work',type=_int_range(100,2_000_000),default=800000)
    c.add_argument('--cross-check-v37',action='store_true')
    c.add_argument('--output',default='d44-v38-certificate.json')
    v=sub.add_parser('check')
    v.add_argument('--certificate',required=True)
    args=p.parse_args()
    if args.action=='construct':
        net=from_cnf(CNF.from_lists(args.n,json.loads(args.clauses_json)))
        packing=construct_d3_packing(make_bipartite_edges(net),r=2,a=1)
        modes=make_jet_tile_modes(packing,node=args.node,precision=args.precision,
                                  extension_degree=args.extension_degree,jet_length=args.jet_length)
        cert=construct_elimination_reference(net,modes,max_work=args.max_work,
                  max_entries=args.max_entries,compare_v37=args.cross_check_v37)
        verdict=verify_elimination_reference(cert,max_work=args.max_work)
        if not verdict['valid']:
            raise RuntimeError(verdict)
        Path(args.output).write_text(json.dumps(cert,indent=2),encoding='utf-8')
        print(json.dumps({'verdict':verdict,'result':cert['result'],
              'work':cert['work'],'max_intermediate_entries':cert['max_intermediate_entries'],
              'output':args.output},indent=2))
    else:
        verdict=verify_elimination_reference(json.loads(Path(args.certificate).read_text(encoding='utf-8')))
        print(json.dumps(verdict,indent=2))
        if not verdict['valid']: raise SystemExit(1)
if __name__=='__main__':main()
