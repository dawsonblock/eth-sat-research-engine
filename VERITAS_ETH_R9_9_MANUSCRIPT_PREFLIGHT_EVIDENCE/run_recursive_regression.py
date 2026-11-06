from pathlib import Path
import json,subprocess,sys,time,os
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT')
ev=root.parent/'VERITAS_ETH_R9_9_MANUSCRIPT_PREFLIGHT_EVIDENCE';out=ev/'final_v2';out.mkdir(exist_ok=True)
sys.path.insert(0,str(root/'src'))
from veritas.research.tapered_v4.provenance import source_binding
start_binding=source_binding()['digest'];kind=sys.argv[1]
base=[sys.executable,'-m','veritas.research.parent_child_r99.cli'];policy=['--max-work','1000000000','--max-seconds','3600','--max-calls','2000000','--max-certificate-bytes','100000000']
if kind=='recursive':
 args=['examples/r99_nonconstant_matching242.json','--mode','recursion'];layout=['--layout-file','examples/r99_nonconstant_matching242_layout.json'];cert=['--certificate',str(out/'recursive.events')]
 commands=[('recursive',base+args+layout+cert+['--output',str(out/'recursive_report.json')]+policy),('recursive_replay',base+args+cert+['--verify','--result-report',str(out/'recursive_report.json'),'--output',str(out/'recursive_replay.json')]+policy),('closed_form',[sys.executable,'scripts/check_r99_matching242.py','--input',args[0],'--events',str(out/'recursive.events'),'--report',str(out/'recursive_report.json'),'--output',str(out/'closed_form.json')])]
else:
 args=['examples/r99_multislot_crossing2.json','--layout-file','examples/r99_multislot_crossing2_layout.json','--certificate',str(out/'crossing_certificate.json')]
 commands=[('crossing',base+args+['--output',str(out/'crossing_report.json')]+policy),('crossing_replay',base+args+['--verify','--output',str(out/'crossing_replay.json')]+policy)]
results=[]
for name,cmd in commands:
 t=time.monotonic()
 with (out/(name+'.log')).open('w') as log:
  p=subprocess.run(cmd,cwd=root,env=dict(os.environ,PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1'),stdout=log,stderr=subprocess.STDOUT,timeout=3900)
 results.append({'name':name,'command':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-t,'source':source_binding()['digest']})
 (out/(kind+'_commands.json')).write_text(json.dumps(results,indent=2))
 print(name,p.returncode,results[-1]['seconds'],flush=True)
 if p.returncode or results[-1]['source']!=start_binding:sys.exit(1)
