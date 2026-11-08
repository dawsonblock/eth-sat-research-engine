"""Reproducible finite active-path integration; evidence must be outside source."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from veritas.research.manuscript.experimental import contract_scaled
from veritas.research.manuscript.finite_replay import replay
from veritas.research.manuscript.model import DenseTensor,Network,Vertex
from veritas.research.manuscript.resources import Limits


def produce(ell=2,limits=Limits(max_work=200_000_000,max_seconds=120)):
    fixture=dict(precision=2,ell=ell,row=[[1,2][:ell],[3,1][:ell]],
                 column=[[2,1][:ell],[1,3][:ell]])
    vertices=tuple(Vertex(side,0,(0,),DenseTensor(1,2,tuple(map(tuple,fixture[key]))))
                   for side,key in (('row','row'),('column','column')))
    events=[];leaves=Counter();depths=set();wires=set()
    def emit(event):
        if event['kind']=='leaf':
            leaves['count']+=1;depths.add(event['depth']);wires.add(event['wires'])
        else:events.append(event)
    report=contract_scaled(Network(1,vertices),precision=2,ell=ell,limits=limits,event_sink=emit)
    return dict(schema='VERITAS_SCALED_ONE_WIRE_V1',fixture=fixture,report=report,events=events,
                leaf_summary=dict(count=leaves['count'],depths=sorted(depths),wire_counts=sorted(wires)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--replay',type=Path)
    args=parser.parse_args()
    if args.replay:
        print(json.dumps(replay(json.loads(args.replay.read_text())),indent=2));return
    if not args.output_dir:parser.error('--output-dir or --replay is required')
    output=args.output_dir.resolve()
    if output==ROOT or ROOT in output.parents:parser.error('evidence must be outside source tree')
    output.mkdir(parents=True,exist_ok=True)
    certificate=produce()
    path=output/'active_scaled_certificate.json'
    path.write_text(json.dumps(certificate,indent=2)+'\n')
    if certificate['report']['status']!='PASS_EXPERIMENTAL_SCALED_RECURSION':
        print(json.dumps(certificate['report'],indent=2));raise SystemExit(2)
    result=replay(json.loads(path.read_text()))
    result['certificate_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    (output/'independent_replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
