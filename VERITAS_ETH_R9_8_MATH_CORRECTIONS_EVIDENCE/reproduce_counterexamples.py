"""Compare the preserved release with the corrected package, in fresh processes."""
from pathlib import Path
import json, os, subprocess, sys

base = Path('/Users/dawsonblock/MATH SPEED')
evidence = Path(__file__).resolve().parent
program = r'''
from dataclasses import replace
import json
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.parent_child_r98 import Budget, ExponentTuple, ModeSet, construct_children, from_described, verify_children
from veritas.research.parent_child_r98.model import canonical
from veritas.research.parent_child_r98.modes import build_modes, verify_modes
from veritas.research.parent_child_r98.packing import construct_layout, audit_layout, preconditions
from veritas.research.tensor import Factor, TensorNetwork
from veritas.research.tapered_v4.provenance import source_binding

net = TensorNetwork(1,(Factor((0,),(-2,3),'row:0'),Factor((0,),(4,5),'col:0')))
def parent(f):
    return from_described(describe_integer_network(net,creation_precision=5,defining_polynomial=f),root_s=16,precision=5)
def outcome(fn):
    try:
        fn()
        return {'status':'ACCEPT'}
    except (ValueError, KeyError) as e:
        return {'status':'REJECT','exception':type(e).__name__,'reason':str(e)}
other = parent(25)
other_layout = construct_layout(other,budget=Budget())
observations = {'valid_alternative_polynomial':outcome(lambda:build_modes(other,other_layout,-1,(0,1,0,0),budget=Budget()))}
p=parent(19);l=construct_layout(p,budget=Budget());m=build_modes(p,l,-1,(1,0,0,0),budget=Budget())
beta=ExponentTuple(m.content_digest,());cs=construct_children(p,l,m,beta,budget=Budget());c=cs[0]
observations['wrong_parent_context']=outcome(lambda:c.as_parent(replace(p,root_s=17)))
def altered_half_edge():
    maps=list(c.edge_map);row=list(maps[0]);row[1]=False;maps[0]=tuple(row)
    bad=replace(c,edge_map=tuple(maps))
    verify_children(p,l,m,beta,(bad,)+cs[1:],budget=Budget())
observations['boolean_half_edge']=outcome(altered_half_edge)
def altered_mode():
    data=m.certificate;data['jet_length']=True
    verify_modes(p,l,ModeSet(l.content_digest,canonical(data)),budget=Budget())
observations['boolean_jet_length']=outcome(altered_mode)
def altered_packet():
    data=l.source;data['edges'][0][0]=False
    audit_layout(p,replace(l,source_bytes=canonical(data)))
observations['boolean_packet_endpoint']=outcome(altered_packet)
observations['preflight']=preconditions(p)
observations['source_binding']=source_binding()['digest']
print(json.dumps(observations))
'''
results = {}
for name, directory in (('sealed_R98','VERITAS_ETH_R9_8_PARENT_CHILD'),
                        ('corrected','VERITAS_ETH_R9_8_MATH_REVIEW')):
    env=dict(os.environ,PYTHONPATH=str(base/directory/'src'),PYTHONDONTWRITEBYTECODE='1')
    run=subprocess.run([sys.executable,'-c',program],cwd=base/directory,env=env,
                       capture_output=True,text=True,check=True)
    results[name]=json.loads(run.stdout)
assert results['sealed_R98']['valid_alternative_polynomial']['status']=='REJECT'
assert results['corrected']['valid_alternative_polynomial']['status']=='ACCEPT'
for key in ('wrong_parent_context','boolean_half_edge','boolean_jet_length'):
    assert results['sealed_R98'][key]['status']=='ACCEPT'
    assert results['corrected'][key]['status']=='REJECT'
assert results['sealed_R98']['boolean_packet_endpoint']['status']=='REJECT'
assert results['corrected']['boolean_packet_endpoint']['exception']=='ValueError'
results['scope']='Four behavior corrections plus explicit packet-type rejection; no source-regime qualification'
(evidence/'counterexamples.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:results['corrected'][k]['status'] for k in
                 ('valid_alternative_polynomial','wrong_parent_context','boolean_half_edge','boolean_jet_length','boolean_packet_endpoint')}))
