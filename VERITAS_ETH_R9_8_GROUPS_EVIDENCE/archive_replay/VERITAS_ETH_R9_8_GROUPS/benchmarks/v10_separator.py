"""Tiny deterministic *smoke* benchmark, not a performance generalization."""
import json
import platform
import time
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract, eliminate
from veritas.research.recursive_separator import recursive_contract


def timed(f):
    now=time.perf_counter()
    try:
        answer=f()
        return {'value':str(answer),'seconds':round(time.perf_counter()-now,8)}
    except Exception as exc:
        return {'error':type(exc).__name__,'seconds':round(time.perf_counter()-now,8)}


def main():
    data=[]
    for n,clauses in ((4,[[1,2],[-2,3],[3,4]]),
                      (6,[[1,2,3],[-1,-2],[3,4],[-4,5,6]]),
                      (7,[[1,2],[-1,3],[3,4],[-4,5],[5,6],[-6,7]])):
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>19:continue
        values={
            'enumeration':timed(lambda:brute_contract(net)),
            'bucket_elimination':timed(lambda:eliminate(net)),
            'separator_recursion':timed(lambda:recursive_contract(net)[0]),
        }
        confirmed={x['value'] for x in values.values() if 'value' in x}
        if len(confirmed)!=1:raise AssertionError('benchmark algorithms disagree')
        data.append({'n':n,'clauses':clauses,'edges':net.edges,**values})
    print(json.dumps({'python':platform.python_version(),
                      'note':'tiny deterministic smoke cases; not representative of asymptotic behavior',
                      'cases':data},indent=2))

if __name__=='__main__':main()
