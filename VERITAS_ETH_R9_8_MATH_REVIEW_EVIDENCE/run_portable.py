from pathlib import Path
import os, json, subprocess, sys, time

root = Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_8_MATH_REVIEW')
evidence = Path(__file__).resolve().parent
python = evidence/'clean_py310/bin/python'
wheel = evidence/'wheels/veritas_eth-3.8.2.post98-py3-none-any.whl'
env = dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
env.pop('PYTHONPATH',None)
commands = [
 ('wheel_build',[sys.executable,'-m','pip','wheel','--no-deps','--no-build-isolation',str(root),'-w',str(wheel.parent)]),
 ('venv',['/opt/homebrew/bin/python3.10','-m','venv',str(python.parent.parent)]),
 ('wheel_install',[str(python),'-m','pip','install',str(wheel)]),
]
for name in ('packet_fix','validate_r98_installed','validate_r97_installed'):
    commands.append(('wheel_'+name,[str(python),'-I',str(evidence/'installed'/(name+'.py'))]))
commands.append(('docker_build',['docker','build','-t','veritas-eth:r98-math-review',str(root)]))
for name in ('packet_fix','validate_r98_installed','validate_r97_installed'):
    commands.append(('docker_'+name,['docker','run','--rm','--network','none','--cpus','2',
                     '--memory','1g','--pids-limit','256','--entrypoint','python',
                     '-v',str(evidence/'installed')+':/checks:ro',
                     'veritas-eth:r98-math-review','-I','/checks/'+name+'.py']))
records=[]
for name,command in commands:
    start=time.monotonic()
    with (evidence/(name+'.log')).open('w') as log:
        try:
            result=subprocess.run(command,cwd=evidence,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code=124
    records.append({'name':name,'command':command,'exit_code':code,'seconds':time.monotonic()-start})
    (evidence/'portable_commands.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records[-1]),flush=True)
    if code:
        raise SystemExit(code)
