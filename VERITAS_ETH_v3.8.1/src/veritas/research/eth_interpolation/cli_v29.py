"""Command line interface for finite tapered Hermite and extension-ring modes."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .tapered_hermite import (make_tapered_plan,sample_integer_polynomial,
                              reconstruct_tapered,check_tapered_against_polynomial)
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_modes_v29.extension_modes import make_extension_modes,check_extension_modes


def main(argv=None):
    ap=argparse.ArgumentParser(description='VERITAS-ETH v2.9 finite exact algebra laboratory')
    sub=ap.add_subparsers(dest='command',required=True)
    t=sub.add_parser('tapered',help='schedule plus independent polynomial recovery')
    t.add_argument('--wires',type=int,default=2);t.add_argument('--a',type=int,default=1)
    t.add_argument('--u',type=int,default=1);t.add_argument('--precision',type=int,default=8)
    t.add_argument('--coefficients-json',default='[12,9,-3,0,2]')
    m=sub.add_parser('modes',help='checked extension-ring rank-one Cauchy modes')
    m.add_argument('--edges-json',default='[[0,0],[1,1],[0,1],[1,0]]')
    m.add_argument('--a',type=int,default=1);m.add_argument('--r',type=int,default=2)
    m.add_argument('--node',type=int,default=1);m.add_argument('--precision',type=int,default=8)
    m.add_argument('--extension-degree',type=int,default=4);m.add_argument('--jet-length',type=int,default=3)
    m.add_argument('--output',help='optional JSON certificate path')
    v=sub.add_parser('check-modes',help='check saved research certificate independently')
    v.add_argument('--certificate',required=True)
    a=ap.parse_args(argv)
    if a.command=='tapered':
        plan=make_tapered_plan(M=a.wires,a=a.a,u=a.u,p=a.precision)
        coefficients=json.loads(a.coefficients_json)
        if not isinstance(coefficients,list) or not coefficients or any(type(c) is not int for c in coefficients):
            raise ValueError('polynomial coefficients must be a nonempty integer JSON array')
        jets=sample_integer_polynomial(plan,coefficients)
        out={'plan':plan.to_dict(),'recovered_mod_2p':reconstruct_tapered(plan,jets),
             'oracle':check_tapered_against_polynomial(plan,jets,coefficients)}
    elif a.command=='modes':
        edges=json.loads(a.edges_json)
        base=construct_d3_packing(edges,r=a.r,a=a.a)
        cert=make_extension_modes(base,node=a.node,precision=a.precision,
             extension_degree=a.extension_degree,jet_length=a.jet_length)
        result=check_extension_modes(cert)
        if not result['valid']:raise ArithmeticError('self-check failed: '+str(result))
        if a.output:Path(a.output).write_text(json.dumps(cert,indent=2),encoding='utf-8')
        out={'checker':result,'certificate_file':a.output,'claim':cert['claim']}
    else:
        cert=json.loads(Path(a.certificate).read_text(encoding='utf-8'))
        out=check_extension_modes(cert)
        print(json.dumps(out,indent=2));return 0 if out['valid'] else 1
    print(json.dumps(out,indent=2));return 0

if __name__=='__main__':
    raise SystemExit(main())
