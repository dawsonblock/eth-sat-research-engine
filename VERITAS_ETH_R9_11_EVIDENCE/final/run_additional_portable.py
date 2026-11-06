from pathlib import Path
import json,subprocess,os,sys,time
base=Path(__file__).resolve().parent
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_11_COUPLED_RECURSION')
sys.path.insert(0,str(root/'src'))
from veritas.research.tapered_v4.provenance import source_binding
source=source_binding()['digest'];reports=[]
for command in json.loads((base/'additional_portable_commands.json').read_text()):
 if command['name'].startswith('docker'):
  deadline=time.monotonic()+1800
  while True:
   primary=json.loads((base/'portable/summary.json').read_text())
   if primary['status']=='FAILED':raise RuntimeError('primary portable gate failed')
   if any(r['name']=='docker_build' and r['exit_code']==0 and r['source_after']==source for r in primary['commands']):break
   if time.monotonic()>deadline:raise RuntimeError('docker build readiness timeout')
   time.sleep(5)
 before=source_binding()['digest'];start=time.monotonic()
 with (base/(command['name']+'.log')).open('w') as log:
  code=subprocess.run(command['command'],cwd=root,env=os.environ,stdout=log,stderr=subprocess.STDOUT,timeout=900).returncode
 reports.append({**command,'exit_code':code,'seconds':time.monotonic()-start,'source_before':before,'source_after':source_binding()['digest']})
 (base/'additional_portable_summary.json').write_text(json.dumps({'status':'RUNNING','source':source,'commands':reports},indent=2))
 print(command['name'],code,flush=True)
 if code:break
passed=len(reports)==2 and all(r['exit_code']==0 and r['source_before']==r['source_after']==source for r in reports)
(base/'additional_portable_summary.json').write_text(json.dumps({'status':'PASS' if passed else 'FAILED','source':source,'commands':reports},indent=2))

raise SystemExit(0 if passed else 2)
