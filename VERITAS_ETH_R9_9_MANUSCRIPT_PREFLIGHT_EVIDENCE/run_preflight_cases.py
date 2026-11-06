import os,sys,json,subprocess,time
from pathlib import Path
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT')
out=root.parent/'VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT_EVIDENCE/final'
out.mkdir(exist_ok=True)
env=dict(os.environ,PYTHONPATH=str(root/'src'))
sys.path.insert(0,str(root/'src'))
from veritas.research.parent_child_r98.model import decode,canonical,digest
from veritas.research.tapered_v4.provenance import source_binding
binding=source_binding()['digest']
cases=[('groups',0,['examples/r98_shrinking_cycle484.json','--compare-groups','64,128,256,512,1024','--max-calls','2000000']),
 ('matching',2,['examples/r99_nonconstant_matching242.json','--layout-file','examples/r99_nonconstant_matching242_layout.json','--schedule','1:1,1:1','--max-points','4096','--max-calls','2000000','--descendants','singleton_first_fit']),
 ('point_count',0,['examples/r98_general_matching22.json','--schedule','1:1','--count-point','-1','0'])]
records=[]
for name,expected,args in cases:
 cmd=[sys.executable,'-m','veritas.research.parent_child_r99.preflight_cli',*args,'--output',str(out/(name+'.json'))]
 result=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True,timeout=60)
 (out/(name+'.log')).write_text(result.stdout+result.stderr)
 assert result.returncode==expected,(name,result.stdout,result.stderr)
 data=decode((out/(name+'.json')).read_bytes(),cap=100000000)
 recorded=data.pop('report_digest')
 assert recorded==digest(canonical(data))
 assert 'result' not in data and not data.get('source_qualified',False)
 assert data['implementation_source_sha256']==binding==source_binding()['digest']
 records.append({'name':name,'exit_code':result.returncode,'status':data['status'],'report_digest':recorded})
summary={'status':'PASS','source_binding':binding,'cases':records,'source_qualified':False}
(out/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary))
