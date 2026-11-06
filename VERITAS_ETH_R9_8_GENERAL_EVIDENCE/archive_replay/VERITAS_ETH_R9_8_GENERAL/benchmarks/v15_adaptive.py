"""Exact-count benchmarking, explicitly not a proof of asymptotic performance."""
from __future__ import annotations
import time,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.adaptive_contract import adaptive_count
from veritas.research.bounded_degree import bounded_degree_from_cnf
from veritas.research.minfill_contract import minfill_contract

cases={
  'path_25':CNF.from_lists(25,[[i,i+1] for i in range(1,25)]),
  'star_22':CNF.from_lists(22,[[1,i] for i in range(2,23)]),
  'two_chains_24':CNF.from_lists(24,[[i,i+1] for i in range(1,12)]+[[i,i+1] for i in range(13,24)]),
  'cycle_10':CNF.from_lists(10,[[i,i+1] for i in range(1,10)]+[[10,1]]),
}
results=[]
for name,cnf in cases.items():
    t=time.perf_counter(); v15=adaptive_count(cnf,timeout_s=15)
    sec_v15=time.perf_counter()-t
    t=time.perf_counter();net,_=bounded_degree_from_cnf(cnf)
    try:
        baseline,stat=minfill_contract(net,timeout_s=15)
        legacy={'status':'EXACT_COUNT','count':str(baseline),
                'elapsed_seconds':round(time.perf_counter()-t,6),
                'peak_intermediate_entries':stat.peak_intermediate_entries,
                'evaluated_assignments':stat.evaluated_assignments}
        assert str(baseline)==v15['count']
    except Exception as exc:
        legacy={'status':'LIMIT_OR_ERROR','reason':str(exc)}
    results.append({'case':name,'n':cnf.n,'clauses':len(cnf.clauses),
                    'v15':{'status':v15['status'],'count':v15['count'],
                    'engine':v15['engine'],'representation':v15['representation'],
                    'heuristic':v15['selected_heuristic'],
                    'peak_table_entries':v15['execution']['peak_table_entries'],
                    'evaluated_assignments':v15['execution']['evaluated_assignments'],
                    'elapsed_seconds':round(sec_v15,6)},'v14_copy3_legacy':legacy})
report={'version':'1.5.0','warning':'one run per case; hardware-dependent, includes planning and conversion; not a universal speedup or ETH result', 'results':results}
path=Path(__file__).resolve().parents[1]/'validation'/'benchmark_v15.json'
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
