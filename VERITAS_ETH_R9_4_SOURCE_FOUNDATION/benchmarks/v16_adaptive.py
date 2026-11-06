"""Median comparison of original v1.5 planning / dense engine and v1.6 modes.

This is a single-system microbenchmark, not a universal speedup claim.
"""
import json,time,statistics
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.adaptive_contract import adaptive_count
cases={
 'path_25':CNF.from_lists(25,[[i,i+1] for i in range(1,25)]),
 'star_22':CNF.from_lists(22,[[1,i] for i in range(2,23)]),
 'two_chains_24':CNF.from_lists(24,[[i,i+1] for i in range(1,12)]+[[i,i+1] for i in range(13,24)]),
 'cycle_10':CNF.from_lists(10,[[i,i+1] for i in range(1,10)]+[[10,1]]),
 'grid_4x4':CNF.from_lists(16,[[4*r+c+1,4*r+c+2] for r in range(4) for c in range(3)] +
                                      [[4*r+c+1,4*(r+1)+c+1] for r in range(3) for c in range(4)]),
}
methods={
 'v16_thorough_legacy':{'portfolio_mode':'thorough','execution_mode':'legacy'},
 'v16_fast_indexed':{'portfolio_mode':'auto','execution_mode':'indexed'},
 'v16_full_indexed':{'portfolio_mode':'thorough','execution_mode':'indexed'},
 'v16_fast_sparse':{'portfolio_mode':'auto','execution_mode':'sparse'},
}
rows=[]
for name,cnf in cases.items():
    result={'case':name,'n':cnf.n,'clauses':len(cnf.clauses),'methods':{}}
    for method,opts in methods.items():
        observations=[]
        for _ in range(4):
            tick=time.perf_counter()
            out=adaptive_count(cnf,timeout_s=20,**opts)
            elapsed=time.perf_counter()-tick
            observations.append(elapsed)
        result['methods'][method]={'count':out['count'],'median_seconds':round(statistics.median(observations),8),
                                   'min_seconds':round(min(observations),8),'representation':out['representation'],
                                   'engine':out['engine'],'peak_entries':out['execution']['peak_table_entries']}
    assert len({v['count'] for v in result['methods'].values()})==1
    rows.append(result)
report={'version':'1.6.0','runs_per_method':4,
 'limitations':'Microbenchmark includes planning, dispatch, Python overhead; not a general speedup or ETH result',
 'results':rows}
path=Path(__file__).resolve().parents[1]/'validation'/'benchmark_v16.json'
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
