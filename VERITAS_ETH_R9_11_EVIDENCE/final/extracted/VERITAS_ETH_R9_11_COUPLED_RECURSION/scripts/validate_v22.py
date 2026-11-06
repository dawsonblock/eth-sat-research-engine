"""Seeded exact-count and adversarial proof-check validation for v2.2."""
import copy
import json
import random
from pathlib import Path

from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.solvers.count_dag import make_dag_count_certificate, check_dag_count_certificate

r=random.Random(20261030)
checked=0
for _ in range(2000):
    n=r.randrange(0,10)
    clauses=[]
    for _ in range(r.randrange(0,15)):
        clauses.append([r.choice([-1,1])*r.randint(1,n) for _ in range(r.randrange(0,5))] if n else [])
    cnf=CNF.from_lists(n,clauses)
    made=make_dag_count_certificate(cnf,timeout_s=5)
    if made.status!='COUNT':
        raise AssertionError((made.status,made.reason))
    good, why, count, _=check_dag_count_certificate(cnf,made.certificate)
    if not good or count!=exhaustive_count(cnf,max_vars=12):
        raise AssertionError((why,cnf.as_dict()))
    altered=copy.deepcopy(made.certificate)
    altered['count']=str(count+1)
    if check_dag_count_certificate(cnf,altered)[0]:
        raise AssertionError('forged count accepted')
    checked+=1
payload={'status':'PASS','seed':20261030,'instances':checked,
         'checks':'independent DAG checker vs exhaustive counting and forged count rejection',
         'limitation':'Finite randomized tests are not a formal proof or subexponential algorithm'}
out=Path(__file__).resolve().parents[1]/'validation'/'validation_v22.json'
out.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
print(json.dumps(payload,indent=2))
