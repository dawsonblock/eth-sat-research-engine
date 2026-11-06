"""Run C++ gate and a full, source-bound pytest without hiding failures."""
import json, os, platform, subprocess, sys, time
from pathlib import Path
from xml.etree import ElementTree
from veritas.research.tapered_v4.provenance import source_binding
root=Path.cwd(); evidence=root.parent/'VERITAS_ETH_R9_8_TRANSFER_EVIDENCE'
env=dict(os.environ, PYTHONPATH=str(root/'src'), PYTHONDONTWRITEBYTECODE='1',
         LEAN_BIN='/Users/dawsonblock/.elan/toolchains/leanprover--lean4---v4.35.0/bin/lean')
before=source_binding()['digest']
record={'schema':'VERITAS_R98_TRANSFER_PYTEST_V1','status':'INCOMPLETE','cwd':str(root),
        'source_before':before,'python':platform.python_version(),
        'environment':{'PYTHONPATH':'src','PYTHONDONTWRITEBYTECODE':'1','LEAN_BIN':env['LEAN_BIN']},
        'cpp_commands':[]}
def run(name,command,timeout):
    start=time.monotonic(); log=evidence/(name+'.log')
    with log.open('w') as stream:
        try:
            p=subprocess.run(command,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
            code=p.returncode
        except subprocess.TimeoutExpired:
            code=124
    return {'name':name,'command':command,'exit_code':code,'seconds':time.monotonic()-start,'log':log.name}
try:
    for name,cmd in (
        ('cpp_configure',['cmake','-S','cpp','-B','build/cpp','-DCMAKE_BUILD_TYPE=Release']),
        ('cpp_build',['cmake','--build','build/cpp','-j2']),
        ('cpp_selftest',['./build/cpp/veritas_d3_selftest']),
    ):
        result=run(name,cmd,600);record['cpp_commands'].append(result)
        if result['exit_code']:raise ValueError(name+' failed')
    xml=evidence/'pytest.xml'
    result=run('pytest',[sys.executable,'-m','pytest','-q','--junitxml='+str(xml)],3600)
    record['full_run']=result
    if xml.exists():
        tree=ElementTree.parse(xml); cases=tree.findall('.//testcase')
        failures=[];errors=[];skips=[]
        for case in cases:
            identity=case.get('classname','')+'::'+case.get('name','')
            if case.find('failure') is not None:failures.append(identity)
            if case.find('error') is not None:errors.append(identity)
            if case.find('skipped') is not None:skips.append(identity)
        record.update(tests=len(cases), passed=len(cases)-len(failures)-len(errors)-len(skips),
                      failures=failures,errors=errors,skipped=skips)
    after=source_binding()['digest'];record['source_after']=after
    if before!=after:raise ValueError('source binding changed during full validation')
    record['status']='PASS' if result['exit_code']==0 else 'FAILED_OR_INCONCLUSIVE'
except (ValueError,TypeError,KeyError,ArithmeticError,RuntimeError,MemoryError,OSError) as exc:
    record.update(status='FAILED_OR_INCONCLUSIVE',reason=str(exc),source_after=source_binding()['digest'])
record['artifacts']={p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest()
                     for p in (evidence/'cpp_configure.log',evidence/'cpp_build.log',evidence/'cpp_selftest.log',
                               evidence/'pytest.log',evidence/'pytest.xml') if p.exists()}
(evidence/'pytest_summary.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:record.get(k) for k in ('status','tests','passed','failures','errors','skipped','source_before','source_after','reason')}))
sys.exit(0 if record['status']=='PASS' else 1)
