"""Local JSON CLI for independently checked finite D.3 packet construction."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .constructor import construct_d3_packing
from .checker import verify_d3_packing
from veritas.research.eth_packing.parameters import manuscript_parameters


def main(argv=None):
    p=argparse.ArgumentParser(description='VERITAS-ETH v2.6: finite D.3 proof-carrying packet constructor')
    commands=p.add_subparsers(dest='command',required=True)
    pack=commands.add_parser('pack');pack.add_argument('--edges-json',required=True)
    pack.add_argument('--r',type=int,default=2);pack.add_argument('--a',type=int,default=1)
    pack.add_argument('--max-work',type=int,default=3_000_000)
    pack.add_argument('--max-packets',type=int,default=10000)
    pack.add_argument('--require-preconditions',action='store_true')
    pack.add_argument('--output',type=Path,help='Save full certificate as JSON')
    checker=commands.add_parser('check');checker.add_argument('--certificate',type=Path,required=True)
    checker.add_argument('--skip-trace',action='store_true')
    params=commands.add_parser('parameters');params.add_argument('--s',type=int,default=1000)
    params.add_argument('--depth',type=int,default=0);params.add_argument('--M',type=int)
    params.add_argument('--delta',type=int)
    opts=p.parse_args(argv)
    try:
        if opts.command=='pack':
            output=construct_d3_packing(json.loads(opts.edges_json),r=opts.r,a=opts.a,
                max_work=opts.max_work,max_packets=opts.max_packets,
                require_theorem_preconditions=opts.require_preconditions)
            if opts.output:
                opts.output.write_text(json.dumps(output,indent=2),encoding='utf8')
            summary={'status':output['verification']['status'],
                     'packet_count':len(output['packets']),
                     'verification':output['verification'],
                     'saved_certificate':str(opts.output) if opts.output else None}
            print(json.dumps(summary if opts.output else output,indent=2))
            return 0
        if opts.command=='check':
            result=verify_d3_packing(json.loads(opts.certificate.read_text(encoding='utf8')),
                                     check_trace=not opts.skip_trace)
            print(json.dumps(result,indent=2))
            return 0 if result['valid'] else 2
        result=manuscript_parameters(opts.s,opts.depth,M=opts.M,delta=opts.delta)
        print(json.dumps(result.to_dict(),indent=2))
        return 0
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        print(json.dumps({'status':'ERROR','reason':str(exc)}),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
