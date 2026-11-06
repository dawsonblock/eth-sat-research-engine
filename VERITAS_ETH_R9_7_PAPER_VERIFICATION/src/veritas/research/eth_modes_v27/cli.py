"""Command line construction/checking of finite D.4.4 certificates."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from .constructor import construct_tile_modes
from .checker import verify_tile_modes
from .enumeration import count_tuples, ModeBudgetExceeded


def main(argv=None):
    parser=argparse.ArgumentParser(description='Finite Appendix D.4.4 scalar tile-mode certificate laboratory')
    sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('construct',help='D.3 pack and build checked finite D.4.4 modes')
    create.add_argument('--edges-json',required=True)
    create.add_argument('--radix',type=int,default=2)
    create.add_argument('--a',type=int,default=2)
    create.add_argument('--node',type=int,default=1)
    create.add_argument('--zeta',type=int,default=1)
    create.add_argument('--precision',type=int,default=5)
    create.add_argument('--output',type=Path)
    check=sub.add_parser('check',help='Independently verify a saved mode certificate')
    check.add_argument('--certificate',type=Path,required=True)
    count=sub.add_parser('count-tuples',help='Count weighted nonnegative exponent tuples exactly')
    count.add_argument('--weights-json',required=True)
    count.add_argument('--precision',type=int,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='construct':
            d3=construct_d3_packing(json.loads(args.edges_json),r=args.radix,a=args.a)
            cert=construct_tile_modes(d3,node=args.node,zeta=args.zeta,precision=args.precision)
            verification=verify_tile_modes(cert)
            if not verification['valid']:
                raise ValueError('constructed certificate failed independent verification: '+str(verification))
            if args.output:
                args.output.write_text(json.dumps(cert,indent=2),encoding='utf-8')
            print(json.dumps({'status':verification['status'],'verification':verification,
                              'certificate_path':str(args.output) if args.output else None,
                              'certificate':None if args.output else cert},indent=2))
            return 0
        if args.command=='check':
            cert=json.loads(args.certificate.read_text(encoding='utf-8'))
            result=verify_tile_modes(cert)
            print(json.dumps(result,indent=2))
            return 0 if result['valid'] else 2
        print(json.dumps({'count':count_tuples(json.loads(args.weights_json),args.precision)},indent=2))
        return 0
    except (ValueError,TypeError,KeyError,OverflowError,ModeBudgetExceeded) as exc:
        print(json.dumps({'status':'ERROR','reason':str(exc)}),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
