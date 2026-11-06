from pathlib import Path
import json, os, subprocess, sys, time
root=Path(sys.argv[1]); evidence=Path(sys.argv[2]); group=sys.argv[3]
env=dict(os.environ, PYTHONPATH=str(root/'src'), PYTHONDONTWRITEBYTECODE='1', LEAN_BIN='/Users/dawsonblock/.elan/toolchains/leanprover--lean4---v4.35.0/bin/lean')
plans=json.loads((evidence/'check_plans.json').read_text())[group]
records=[]
for name,arguments in plans:
    command=[sys.executable,*arguments]
    started=time.monotonic()
    with (evidence/(name+'.log')).open('w') as log:
        try:
            p=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800,check=False)
            code=p.returncode
        except subprocess.TimeoutExpired:
            code=124
    record={'name':name,'command':command,'exit_code':code,'wall_seconds':time.monotonic()-started}
    records.append(record)
    (evidence/(group+'_commands.json')).write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(record),flush=True)
raise SystemExit(int(any(x['exit_code'] for x in records)))
