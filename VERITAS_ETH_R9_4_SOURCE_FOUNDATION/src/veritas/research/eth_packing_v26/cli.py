"""Local JSON CLI for independently checked finite D.3 packet construction."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .constructor import construct_d3_packing
from .checker import verify_d3_packing
from .streaming import construct_streaming_d3_packing
from .streaming_check import verify_streaming_d3_certificate
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
    stream=commands.add_parser('stream-pack',help='run the bounded exact streaming labeler')
    stream.add_argument('--edges-json',required=True)
    stream.add_argument('--r',type=int,default=2);stream.add_argument('--a',type=int,default=1)
    stream.add_argument('--max-work',type=int,default=30_000_000)
    stream.add_argument('--max-candidates',type=int,default=1_000_000)
    stream.add_argument('--score-backend',choices=('python','cpp','auto'),default='python')
    stream.add_argument('--output',type=Path,help='Save the finite execution certificate as JSON')
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
        if opts.command=='stream-pack':
            built=construct_streaming_d3_packing(
                json.loads(opts.edges_json),r=opts.r,a=opts.a,
                max_work=opts.max_work,
                max_candidate_evaluations=opts.max_candidates,
                score_backend=opts.score_backend)
            checked=verify_streaming_d3_certificate(
                built.certificate,max_work=opts.max_work,
                max_candidate_evaluations=opts.max_candidates)
            if not checked.get('valid'):
                print(json.dumps({'status':'INCONCLUSIVE_CERTIFICATE_REPLAY',
                                  'verification':checked},indent=2),file=sys.stderr)
                return 2
            if opts.output:
                opts.output.write_text(json.dumps(built.certificate,indent=2),encoding='utf8')
            print(json.dumps({
                'status':checked['status'],
                'requested_score_backend':built.certificate['score_backend_requested'],
                'selected_score_backend':built.certificate['score_backend'],
                'work_units':built.work_units,
                'verification':checked,
                'saved_certificate':str(opts.output) if opts.output else None,
                'theorem_mode_enabled':False,
            },indent=2))
            return 0
        if opts.command=='check':
            result=verify_d3_packing(json.loads(opts.certificate.read_text(encoding='utf8')),
                                     check_trace=not opts.skip_trace)
            print(json.dumps(result,indent=2))
            return 0 if result['valid'] else 2
        result=manuscript_parameters(opts.s,opts.depth,M=opts.M,delta=opts.delta)
        print(json.dumps(result.to_dict(),indent=2))
        return 0
    except (ValueError,TypeError,KeyError,OverflowError,RuntimeError) as exc:
        print(json.dumps({'status':'ERROR','reason':str(exc)}),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
