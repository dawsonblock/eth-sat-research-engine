"""Benchmark one-DAG exact all-variable posterior inference against repeated WMC.

Reports wall-time on a fixed small formula. Local results are not general claims.
"""
from __future__ import annotations
import json
from pathlib import Path
from time import perf_counter
from veritas.core.cnf import CNF
from veritas.solvers.marginals import exact_marginals
from veritas.solvers.conditional import exact_conditional


def main():
    n=16
    clauses=[[v,v+1] for v in range(1,16,2)] + [[-v,v+1] for v in range(2,16,2)]
    cnf=CNF.from_lists(n,clauses)
    weights={str(v):(['1/2','1/2'] if v%2 else ['1/3','2/3']) for v in range(1,n+1)}
    a=perf_counter()
    batch=exact_marginals(cnf,weights)
    batch_s=perf_counter()-a
    assert batch.status=='POSTERIORS'
    a=perf_counter()
    for v in range(1,n+1):
        query=CNF.from_lists(n,[[v]])
        result=exact_conditional(cnf,query,weights)
        assert result.status=='PROBABILITY'
        assert result.probability==batch.marginals[str(v)][1]
    repeated_s=perf_counter()-a
    payload={'version':'2.4.0','n':n,'clauses':len(clauses),'batch_seconds':round(batch_s,6),
             'repeated_conditional_seconds':round(repeated_s,6),
             'ratio_repeated_over_batch':round(repeated_s/batch_s,3) if batch_s else None,
             'matching_exact_results':True,
             'interpretation':'Illustrative single-machine benchmark; one case; no general speedup guarantee'}
    out=Path(__file__).resolve().parents[1]/'validation/benchmark_v24.json'
    out.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))


if __name__=='__main__':main()
