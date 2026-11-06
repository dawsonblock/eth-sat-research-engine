"""Bounded exact extension-interpolation CLI for VERITAS-ETH v2.8."""
from __future__ import annotations
import argparse,json
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_packing.parameters import manuscript_parameters
from .shifted_cauchy import verify_cauchy_interpolation


def main(argv=None):
    parser=argparse.ArgumentParser(description='Bounded exact extension-ring interpolation research')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('cauchy');p.add_argument('--packet-size',type=int,default=2);p.add_argument('--node',type=int,default=1);p.add_argument('--precision',type=int,default=8);p.add_argument('--extension-degree',type=int,default=4)
    p=sub.add_parser('parameters');p.add_argument('--s',type=int,default=1000);p.add_argument('--depth',type=int,default=0)
    a=parser.parse_args(argv)
    if a.command=='parameters':
        out=manuscript_parameters(a.s,a.depth).to_dict()
    else:
        r=ExtensionRing(a.precision,first_irreducible(a.extension_degree))
        out=verify_cauchy_interpolation(a.packet_size,a.node,r)
    print(json.dumps(out,indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
