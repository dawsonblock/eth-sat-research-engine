import os,sys,json,subprocess,time
from pathlib import Path
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_9_STREAMING_RESOURCES')
evidence=root.parent/'VERITAS_ETH_R9_9_STREAMING_RESOURCES_EVIDENCE'
sys.path.insert(0,str(root/'src'))
from veritas.research.tapered_v4.provenance import source_binding
binding=source_binding()['digest']
kind=sys.argv[1]; out=evidence/kind;out.mkdir(exist_ok=True)
env=dict(os.environ,PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1',LEAN_BIN='/Users/dawsonblock/.elan/toolchains/leanprover--lean4---v4.35.0/bin/lean')
if kind.startswith('full'):
 commands=[{'name':'cpp_configure','command':['cmake','-S','cpp','-B','build/cpp','-DCMAKE_BUILD_TYPE=Release']},
 {'name':'cpp_build','command':['cmake','--build','build/cpp','-j2']},
 {'name':'cpp_selftest','command':['./build/cpp/veritas_d3_selftest']},
 {'name':'pytest','command':[sys.executable,'-m','pytest','-q','--junitxml='+str(out/'pytest.xml')]}]
else:
 old=root.parent/'VERITAS_ETH_R9_8_TRANSFER_EVIDENCE/post-meter/inherited'
 commands=json.loads((old/'inherited_checks_commands.json').read_text())
 commands=[{'name':c['name'],'command':[x.replace(str(old),str(out)) for x in c['command']]} for c in commands]
 commands.append({'name':'r99','command':[sys.executable,'scripts/validate_r99_packets.py','--output',str(out/'r99.json')]})
reports=[]
for c in commands:
 start=time.monotonic();before=source_binding()['digest']
 with (out/(c['name']+'.log')).open('w') as log:
  try: code=subprocess.run(c['command'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=2400).returncode
  except subprocess.TimeoutExpired:code=124
 after=source_binding()['digest'];record=dict(c,exit_code=code,seconds=time.monotonic()-start,source_before=before,source_after=after)
 reports.append(record);(out/'summary.json').write_text(json.dumps({'status':'RUNNING','source':binding,'commands':reports},indent=2))
 print(c['name'],code,flush=True)
 if code or before!=binding or after!=binding:break
status='PASS' if len(reports)==len(commands) and all(r['exit_code']==0 and r['source_before']==r['source_after']==binding for r in reports) else 'FAILED'
(out/'summary.json').write_text(json.dumps({'status':status,'source':binding,'commands':reports},indent=2))
