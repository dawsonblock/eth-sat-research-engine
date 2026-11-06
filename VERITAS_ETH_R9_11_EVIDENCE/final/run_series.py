from pathlib import Path
import subprocess,os,sys,json,time
root=Path('/Users/dawsonblock/MATH SPEED/VERITAS_ETH_R9_11_COUPLED_RECURSION');base=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'src'))
from veritas.research.tapered_v4.provenance import source_binding
kind=sys.argv[1];commands=[];py=sys.executable
def add(name,args,expected=0):commands.append({'name':name,'command':[py,*args],'expected_exit':expected})
if kind=='numerical_series':
 add('fresh235',['scripts/validate_r910.py','--output-dir',str(base/'numerical')])
 for n,stem in [('235','r910_matching235'),('242','r99_nonconstant_matching242')]:
  add('replay'+n,['-m','veritas.research.parent_child_r910.cli','examples/'+stem+'.json','--layout-file','examples/'+stem+'_layout.json','--replay-dir',str(base/'sealed_r910'/n),'--output-dir',str(base/('replay'+n)),'--max-seconds','600','--oracle-max-seconds','600','--oracle-max-work','5000000'])
 for resource,work,seconds in [('work','1','600'),('time','5000000','1')]:
  add('refused_oracle_'+resource,['-m','veritas.research.parent_child_r910.cli','examples/r910_matching235.json','--layout-file','examples/r910_matching235_layout.json','--replay-dir',str(base/'sealed_r910/235'),'--output-dir',str(base/('refused_oracle_'+resource)),'--oracle-max-work',work,'--oracle-max-seconds',seconds],2)
 add('focused',['-m','pytest','-q','tests/test_r911_portability.py','tests/test_r911_experiments.py','tests/test_r910_numerical.py','-k','not two_levels and not nested','--junitxml='+str(base/'focused.xml')])
else:
 driver='scripts/experiment_r911.py'
 def experiment(name,flags,expected):add(name,[driver,'--output-dir',str(base/name),*flags],expected)
 experiment('coupled_one_level',['--cycle-pairs','22','--all-columns','--max-seconds','300','--max-work','100000000'],0)
 experiment('coupled_one_level_no_cache',['--cycle-pairs','22','--all-columns','--cache-bytes','0','--max-seconds','300','--max-work','100000000'],0)
 experiment('coupled_core',['--max-seconds','600','--max-work','100000000','--max-certificate-bytes','20000000'],2)
 experiment('coupled_core_100mb',['--max-seconds','180','--max-work','12000000'],2)
 experiment('fully_nonconstant_cycle',['--active-rows','242','--all-columns','--max-seconds','30','--max-work','1000000'],2)
 for b in [1,2,4,8,16,32,242]:
  (base/'sweep_shifted').mkdir(exist_ok=True)
  experiment('sweep_shifted/b'+str(b),['--kind','matching','--active-rows',str(b),'--max-seconds','120','--max-work','12000000'],2)
 for b in [1,2,4,8,16,32,242]:
  (base/'sweep').mkdir(exist_ok=True)
  add('sweep/b'+str(b),[str(base/'experiment_r911_initial.py'),'--kind','matching','--active-rows',str(b),'--max-seconds','120','--max-work','12000000','--output-dir',str(base/'sweep'/('b'+str(b)))],2)
source=source_binding()['digest'];reports=[]
for record in commands:
 before=source_binding()['digest'];start=time.monotonic()
 with (base/(record['name'].replace('/','_')+'.log')).open('w') as log:
  try: code=subprocess.run(record['command'],cwd=root,env=dict(os.environ,PYTHONPATH=str(root/'src')),stdout=log,stderr=subprocess.STDOUT,timeout=1200).returncode
  except subprocess.TimeoutExpired:code=124
 reports.append({**record,'exit_code':code,'seconds':time.monotonic()-start,'source_before':before,'source_after':source_binding()['digest']})
 (base/(kind+'.json')).write_text(json.dumps({'status':'RUNNING','source':source,'commands':reports},indent=2))
 print(record['name'],code,flush=True)
 if code!=record['expected_exit'] or before!=source or reports[-1]['source_after']!=source:break
status='PASS_EXPECTED_OUTCOMES' if len(reports)==len(commands) and all(r['exit_code']==r['expected_exit'] and r['source_before']==r['source_after']==source for r in reports) else 'FAILED'
(base/(kind+'.json')).write_text(json.dumps({'status':status,'source':source,'commands':reports},indent=2))
