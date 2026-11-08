"""Independently replay every child contraction in the one-wire finite fixture.

This strengthens the compact point oracle without changing package sources or
literal source policies. All 76,960 leaf values are stored losslessly as runs.
"""
from fractions import Fraction
import argparse
import json
from math import comb
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if '--installed' not in sys.argv:sys.path.insert(0,str(ROOT/'src'))
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.manuscript.finite_replay import replay,ReplayError
from veritas.research.manuscript.experimental import contract_scaled
from veritas.research.manuscript.model import DenseTensor,Network,Vertex
from veritas.research.manuscript.resources import Limits


def _append(runs,value):
    value=[list(row) for row in value]
    if runs and runs[-1]['result']==value:runs[-1]['count']+=1
    else:runs.append(dict(count=1,result=value))


def _betas(remaining=8,index=0,prefix=()):
    """Independent depth-first weighted compositions, not the odometer."""
    if index==32:
        yield prefix
        return
    weight=1+index//4
    for power in range(remaining//weight+1):
        yield from _betas(remaining-power*weight,index+1,prefix+(power,))


def _kernel(ring,t,z):
    coefficients=[Fraction(1)]
    for root in (-2,-1,1):
        nxt=[Fraction(0)]*(len(coefficients)+1)
        for j,c in enumerate(coefficients):nxt[j]-=root*c;nxt[j+1]+=c
        coefficients=nxt
    shifted=[sum(-c*comb(j,k)*t**(j-k)*4**k/2
                 for j,c in enumerate(coefficients) if j>=k) for k in range(4)]
    out=ring.zero
    for c in reversed(shifted):
        if c.denominator!=1:raise ReplayError('nonintegral independent kernel coefficient')
        out=ring.add(ring.mul(out,z),ring.elem([c.numerator]))
    return out


def replay_children(certificate):
    result=replay(certificate)
    fixture=certificate['fixture'];ell=fixture['ell'];left=fixture['row'];right=fixture['column']
    ring=ExtensionRing(9,19);zero=(ring.zero,)*ell;expected=[]
    allzero=tuple(ring.elem([v]) for v in left[0])
    column_zero=tuple(ring.elem([a+b]) for a,b in zip(right[0],right[1]))
    column_positive=tuple(ring.elem([v]) for v in right[1])
    for event in certificate['events'][1:9]:
        t=event['t'];z=tuple(event['zeta'])
        kernel=_kernel(ring,t,z)
        denominator=ring.add(ring.elem([t]),ring.mul(ring.elem([4]),z))
        ratio=ring.mul(ring.elem([2]),ring.inverse(denominator))
        row_modes=[];coefficient=kernel
        for b in range(8):
            row_modes.append(tuple(ring.mul(ring.elem([a-c]),coefficient)
                                   for a,c in zip(left[1],left[0])))
            coefficient=ring.mul(coefficient,ratio)
        count=0
        for beta in _betas():
            count+=1
            support=[j for j,power in enumerate(beta) if power]
            # Group 0 contains one row endpoint and no column endpoints. Its
            # single affine factor can choose at most one occupied tile mode.
            if not support:row=allzero
            elif len(support)==1 and support[0]%4==0 and beta[support[0]]==1:
                row=row_modes[support[0]//4]
            else:row=zero
            # Group 1 has only column x at tile zero, local coordinate j=0.
            # Any positive j-exponent vanishes. Powers of the b=0 source x
            # all equal x; positive modes of empty packets vanish separately.
            if not support:column=column_zero
            elif support==[0]:column=column_positive
            else:column=zero
            _append(expected,row);_append(expected,column)
        if count!=4810:raise ReplayError('independent beta enumeration count mismatch')
    actual=certificate.get('child_runs')
    if not isinstance(actual,list) or len(actual)>512:
        raise ReplayError('invalid child contraction run inventory')
    for run in actual:
        if (not isinstance(run,dict) or set(run)!= {'count','result'} or
            type(run['count']) is not int or not 1<=run['count']<=76960 or
            not isinstance(run['result'],list) or len(run['result'])!=ell or
            any(not isinstance(row,list) or len(row)!=4 or
                any(type(c) is not int or not 0<=c<512 for c in row)
                for row in run['result'])):
            raise ReplayError('noncanonical child contraction run')
    if actual!=expected:raise ReplayError('independent child contraction mismatch')
    result.update(independently_recomputed_child_contractions=sum(run['count'] for run in expected),
                  lossless_child_runs=len(expected),
                  scope='ONE_WIRE_ONE_ACTIVE_LEVEL; every child contraction, point and root recomputed')
    return result


def produce():
    fixture=dict(precision=2,ell=2,row=[[1,2],[3,1]],column=[[2,1],[1,3]])
    network=Network(1,tuple(Vertex(side,0,(0,),DenseTensor(1,2,tuple(map(tuple,fixture[side]))))
                             for side in ('row','column')))
    events=[];runs=[];count=0
    def emit(event):
        nonlocal count
        if event['kind']=='leaf':
            if (event['depth'],event['wires'],event['precision'],event['reason'])!=(1,1,9,'EXPERIMENT_DEPTH_LIMIT'):
                raise ReplayError('unexpected child metadata')
            _append(runs,event['result']);count+=1
        else:events.append(event)
    report=contract_scaled(network,precision=2,ell=2,limits=Limits(max_work=200_000_000,max_seconds=180),event_sink=emit)
    return dict(schema='VERITAS_SCALED_ONE_WIRE_V1',fixture=fixture,report=report,events=events,
                leaf_summary=dict(count=count,depths=[1],wire_counts=[1]),child_runs=runs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed',action='store_true',help='use only the installed package, not checkout src')
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--replay',type=Path)
    args=parser.parse_args()
    if args.installed:
        from veritas.research.manuscript import executor
        if ROOT/'src' in Path(executor.__file__).resolve().parents:
            parser.error('installed replay unexpectedly imported checkout source')
    if args.replay:
        print(json.dumps(replay_children(json.loads(args.replay.read_text())),indent=2));return
    if not args.output_dir:parser.error('--output-dir or --replay required')
    output=args.output_dir.resolve()
    if output==ROOT or ROOT in output.parents:parser.error('evidence must be outside source')
    output.mkdir(parents=True,exist_ok=True)
    certificate=produce()
    path=output/'full_children_certificate.json'
    path.write_text(json.dumps(certificate,indent=2)+'\n')
    result=replay_children(json.loads(path.read_text()))
    (output/'full_children_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
