"""Isolated CLI for the v2.5 exact/scaled manuscript research components."""
import argparse
import json
from .parameters import manuscript_parameters, scaled_parameters
from .packing import construct_packing
from .checker import check_packing
from .cauchy import verify_cauchy_matrix
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing


def main(argv=None):
    ap=argparse.ArgumentParser(description="VERITAS-ETH v2.5 finite packet and ring laboratory")
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('parameters');p.add_argument('--s',type=int,default=1000);p.add_argument('--depth',type=int,default=0)
    p=sub.add_parser('pack');p.add_argument('--edges-json',required=True,help='JSON array of [u,v] endpoint pairs');p.add_argument('--r',type=int,default=4);p.add_argument('--a',type=int,default=2);p.add_argument('--enforce-bounds',action='store_true')
    p=sub.add_parser('check');p.add_argument('--certificate',required=True,help='JSON certificate file');p.add_argument('--require-bounds',action='store_true')
    p=sub.add_parser('ring');p.add_argument('--precision',type=int,default=8);p.add_argument('--degree',type=int,default=4)
    p=sub.add_parser('cauchy');p.add_argument('--packet-size',type=int,default=4)
    args=ap.parse_args(argv)
    if args.command=='parameters':
        out=manuscript_parameters(args.s,args.depth).to_dict()
    elif args.command=='pack':
        out=construct_packing(json.loads(args.edges_json),r=args.r,a=args.a,enforce_bounds=args.enforce_bounds)
    elif args.command=='check':
        with open(args.certificate,encoding='utf-8') as f:
            out=check_packing(json.load(f),require_bounds=args.require_bounds)
    elif args.command=='ring':
        f=first_irreducible(args.degree);ring=ExtensionRing(args.precision,f)
        example=ring.elem([1,1]);out={'f_binary':bin(f),'precision':ring.p,'degree':ring.e,'example':example,'inverse':ring.inverse(example)}
    else:
        out={'packet_size':args.packet_size,'W(0)=I':verify_cauchy_matrix(args.packet_size)}
    print(json.dumps(out,indent=2,default=list))
    return 0 if out.get('valid_structure',True) else 2

if __name__=='__main__':
    raise SystemExit(main())
