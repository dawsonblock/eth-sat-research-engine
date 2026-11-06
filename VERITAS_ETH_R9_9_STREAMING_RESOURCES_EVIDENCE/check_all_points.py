from pathlib import Path
from dataclasses import replace
import json,sys
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_STREAMING_RESOURCES')
sys.path.insert(0,str(root/'src'))
from veritas.research.parent_child_r98.shrinking_cli import load_input
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.parent_child_r99.stream_engine import contract_streaming
from veritas.research.parent_child_r99.stream_recovery import StreamRecovery
from veritas.research.independent_r82.point_mode_oracle import _IndependentExtension,_Meter
from veritas.research.tapered_v4.provenance import source_binding
p=load_input(root/'examples/r98_general_matching22.json')
original=StreamRecovery.add
checked=[]
def check(self,t,point,bits,value):
    assert self.parent.content_digest==p.content_digest
    assert bits==p.precision+64*p.edge_count
    meter=_Meter(5_000_000,60)
    ar=_IndependentExtension(bits+1,p.defining_polynomial,meter,max_precision_bits=65536,max_extension_degree=12)
    T=ar.add(ar.scalar(t),ar.mul(ar.scalar(4),tuple(point)))
    numerator=ar.mul(ar.mul(ar.add(T,ar.scalar(2)),ar.add(T,ar.one)),ar.sub(T,ar.one))
    assert all(x%2==0 for x in numerator)
    mod=1<<bits
    W=tuple((-(x//2))%mod for x in numerator)
    expected=tuple(x%mod for x in ar.pow(ar.add(ar.scalar(24),ar.mul(ar.scalar(7),W)),22))
    assert tuple(value)==expected,(t,point)
    checked.append({'node':t,'zeta':list(point),'precision':bits,'equality':True})
    return original(self,t,point,bits,value)
StreamRecovery.add=check
r=contract_streaming(p,policy=replace(DEFAULT_SHRINKING_POLICY,max_seconds=600,max_work=1_000_000_000))
assert r['status']=='PASS_FINITE_STREAMED_TAPERED_RECURSION',r
assert len(checked)==134 and r['result'][0][0]==31**22
out={'status':'PASS_ALL_134_INDEPENDENT_CAUCHY_POINT_VALUES',
     'implementation_source_sha256':source_binding()['digest'],
     'formula':'W(T)=-(T+2)(T+1)(T-1)/2; F(T)=(24+7W(T))^22',
     'method':'external validation observer; independent ring arithmetic at p_t+1 before exact division by two',
     'production_answers_substituted':False,'points':checked,'run':r,'source_qualified':False}
(root.parent/'VERITAS_ETH_R9_9_STREAMING_RESOURCES_EVIDENCE/all_points.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])
