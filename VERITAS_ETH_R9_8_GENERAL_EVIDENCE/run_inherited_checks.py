import concurrent.futures, hashlib, json, os, subprocess, sys, threading, time
from pathlib import Path
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_8_GENERAL')
evidence=root.with_name(root.name+'_EVIDENCE')
old=root.with_name('VERITAS_ETH_R9_8_SHRINKING_EVIDENCE')
commands=json.loads((old/'verification.json').read_text())['validators']
env=dict(os.environ,PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1')
results=[]
lock=threading.Lock()
def fingerprint():
    h=hashlib.sha256()
    for p in sorted((root/'src').rglob('*.py')):
        h.update(str(p.relative_to(root)).encode());h.update(p.read_bytes())
    return h.hexdigest()
def run(record):
    name=record['name']
    cmd=[str(x).replace(str(old),str(evidence)).replace('VERITAS_ETH_R9_8_SHRINKING/','VERITAS_ETH_R9_8_GENERAL/') for x in record['command']]
    cmd[0]=sys.executable
    start=time.monotonic(); before=fingerprint()
    print('START '+name,flush=True)
    with (evidence/(name+'.log')).open('w') as output:
        try:
            rc=subprocess.run(cmd,cwd=root,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=1200).returncode
        except subprocess.TimeoutExpired:
            rc=124
    entry={'name':name,'command':cmd,'exit_code':rc,'wall_seconds':time.monotonic()-start,'source_sha256_before':before,'source_sha256_after':fingerprint()}
    with lock:
        results.append(entry)
        (evidence/'inherited_checks_commands.json').write_text(json.dumps(results,indent=2)+'\n')
    print('DONE '+name+' '+str(rc),flush=True)
    return entry
independent=[r for r in commands if r['name'] not in ('r97_verify','r97_faults')]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,r) for r in independent]
    for future in futures:future.result()
for record in commands:
    if record['name'] in ('r97_verify','r97_faults'):run(record)
print('ALL_DONE '+str(sum(x['exit_code']==0 for x in results))+'/'+str(len(results)),flush=True)
