"""Reproducible, machine-local comparison of two exact proof formats.

Measures *generator time*, nodes, JSON size, independently checked count.
Results are not evidence of subexponential complexity or universal speedups.
"""
import json
from pathlib import Path
from time import perf_counter

from veritas.core.cnf import CNF
from veritas.solvers.count_certificates import make_count_certificate, check_count_certificate
from veritas.solvers.count_dag import make_dag_count_certificate, check_dag_count_certificate

cases = {
    '12_disjoint_or': CNF.from_lists(26, [[2*i+1, 2*i+2] for i in range(12)]),
    'shared_variable': CNF.from_lists(9, [[1,2],[1,3],[-1,4],[-1,5],[6,7],[-7,8],[8,9]]),
    'chain': CNF.from_lists(10, [[i,i+1] for i in range(1,10)]),
    'all_tautologies': CNF.from_lists(26, [[i,-i] for i in range(1,14)]),
}
records=[]
for name,cnf in cases.items():
    row={'name':name,'variables':cnf.n,'clauses':len(cnf.clauses)}
    for label,make,verify in (('shannon_tree',make_count_certificate,check_count_certificate),
                              ('component_dag',make_dag_count_certificate,check_dag_count_certificate)):
        t0=perf_counter()
        result=make(cnf,timeout_s=20)
        seconds=perf_counter()-t0
        if result.status!='COUNT':
            raise AssertionError(f'{name}/{label} failed: {result.reason}')
        valid, reason, value, checked_nodes=verify(cnf,result.certificate)
        if not valid or value!=result.count:
            raise AssertionError(f'{name}/{label}: {reason}')
        row[label]={'count':str(value),'nodes':result.nodes,
                    'serialized_bytes':len(json.dumps(result.certificate,separators=(',',':')).encode()),
                    'generation_ms':round(seconds*1000,3), 'checker_nodes':checked_nodes}
    if row['shannon_tree']['count']!=row['component_dag']['count']:
        raise AssertionError('cross-format count mismatch')
    records.append(row)
result={'scope':'bounded local reference; not ETH asymptotics','cases':records}
output=Path(__file__).resolve().parents[1]/'validation'/'benchmark_v22.json'
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
