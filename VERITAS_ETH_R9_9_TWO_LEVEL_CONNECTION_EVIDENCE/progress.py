import json
from pathlib import Path
root=Path(__file__).parent
out={}
for name,path in [('full','full/summary.json'),('inherited','inherited/summary.json'),('portable','portable/portable_summary.json')]:
 p=root/path
 out[name]=json.loads(p.read_text())['status'] if p.exists() else 'RUNNING'
log=root/'full/pytest.log'
if log.exists():
 lines=[l for l in log.read_text().splitlines() if '%' in l]
 if lines:out['pytest_progress']=lines[-1].split('[')[-1].strip(']')
print(json.dumps(out))
