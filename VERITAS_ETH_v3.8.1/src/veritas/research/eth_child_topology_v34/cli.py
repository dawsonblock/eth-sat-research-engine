"""Bounded v3.4 structural child preflight; no ETH speedup claim."""
import argparse,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from .topology import construct_topology_certificate,check_topology_certificate
from .pipeline import construct_integrated_certificate,check_integrated_certificate


def main(argv=None):
    parser=argparse.ArgumentParser(description='D.3 port / finite D.4.4 mode topology certificate, not a recursive ETH proof')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('construct')
    p.add_argument('--n',type=int,default=2)
    p.add_argument('--clauses-json',default='[[1,2]]')
    p.add_argument('--radix',type=int,default=2)
    p.add_argument('--a',type=int,default=1)
    p.add_argument('--node',type=int,default=1)
    p.add_argument('--precision',type=int,default=5)
    p.add_argument('--extension-degree',type=int,default=3)
    p.add_argument('--jet-length',type=int,default=2)
    p.add_argument('--with-modes',action='store_true')
    p.add_argument('--output')
    v=sub.add_parser('check');v.add_argument('--certificate',required=True)
    q=sub.add_parser('contract')
    for action in p._actions:
        if action.dest not in ('help','output','with_modes'):
            opts={'dest':action.dest,'default':action.default}
            if action.type is not None:opts['type']=action.type
            q.add_argument(*action.option_strings,**opts)
    q.add_argument('--output')
    args=parser.parse_args(argv)
    if args.command=='check':
        data=json.loads(Path(args.certificate).read_text(encoding='utf-8'))
        result=(check_integrated_certificate(data) if data.get('schema')=='VERITAS_ETH_STRUCTURAL_FINITE_CONTRACTION_V34'
                else check_topology_certificate(data))
        print(json.dumps(result,indent=2));return 0 if result['valid'] else 1
    net=from_cnf(CNF.from_lists(args.n,json.loads(args.clauses_json)))
    d3=construct_d3_packing(make_bipartite_edges(net),r=args.radix,a=args.a,max_packets=256)
    modes=make_jet_tile_modes(d3,node=args.node,precision=args.precision,
        extension_degree=args.extension_degree,jet_length=args.jet_length) if args.command=='contract' or args.with_modes else None
    coordinate=(abs(args.node)&-abs(args.node)).bit_length()-1 if modes is not None else 0
    cert=(construct_integrated_certificate(net,modes) if args.command=='contract'
          else construct_topology_certificate(d3,mode_certificate=modes,coordinate=coordinate))
    verdict=(check_integrated_certificate(cert) if args.command=='contract' else check_topology_certificate(cert))
    if not verdict['valid']:raise ArithmeticError(verdict['reason'])
    if args.output:Path(args.output).write_text(json.dumps(cert,indent=2),encoding='utf-8')
    summary=(cert['topology_certificate']['summary'] if args.command=='contract' else cert['summary'])
    print(json.dumps({'checker':verdict,'summary':summary,'saved_certificate':args.output},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
