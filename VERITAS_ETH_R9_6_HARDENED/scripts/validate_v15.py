"""Seeded exact differential validation, independently of API and old validators."""
from __future__ import annotations
import random,time,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.contraction_planner import original_cnf_model,copy3_model,plan_portfolio,contract_order
from veritas.research.boundary_dp import boundary_contract
from veritas.research.adaptive_contract import adaptive_count

rng=random.Random(15052026)
start=time.perf_counter()
cases=500
checks=0
for i in range(cases):
    n=rng.randrange(0,9)
    clauses=([[rng.choice([-1,1])*rng.randrange(1,n+1)
               for _ in range(rng.randrange(0,5))]
              for _ in range(rng.randrange(0,10))] if n else ([[]] if i%2 else []))
    cnf=CNF.from_lists(n,clauses)
    oracle=exhaustive_count(cnf)
    for model in (original_cnf_model(cnf),copy3_model(cnf)):
        for plan in plan_portfolio(model):
            result,_=contract_order(model,plan)
            assert result==oracle,(i,model.representation,plan.heuristic,oracle,result)
            checks+=1
        result,_=boundary_contract(model)
        assert result==oracle,(i,'boundary',model.representation)
        checks+=1
    precision=1+rng.randrange(1,12)
    result=adaptive_count(cnf,precision_bits=precision)
    assert int(result['count'])==oracle%(1<<precision),(i,'modular',result,oracle)
    checks+=1
output={'version':'1.5.0','seed':15052026,'instances':cases,
        'exact_or_modular_differential_checks':checks,
        'all_passed':True,'seconds':round(time.perf_counter()-start,3),
        'scope':'small Boolean CNF, exact reference, both representations, three plans, boundary DP, modular adaptive'}
path=Path(__file__).resolve().parents[1]/'validation'/'validation_v15.json'
path.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
