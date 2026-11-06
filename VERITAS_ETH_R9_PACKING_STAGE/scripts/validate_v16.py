"""Seeded independent oracle comparisons: v1.6 indexed, sparse, legacy modes."""
import random,json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.contraction_planner import original_cnf_model,copy3_model,elimination_order,contract_order
from veritas.research.indexed_contract import indexed_contract_order
from veritas.research.sparse_contract import sparse_contract_order
from veritas.research.adaptive_contract import adaptive_count
rng=random.Random(16022026)
counts={'instances':0,'cross_checks':0,'failures':0}
for case in range(400):
    n=rng.randrange(0,9)
    clauses=([[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randrange(0,4))]
              for __ in range(rng.randrange(0,12))] if n else ([[]] if rng.randrange(2) else []))
    cnf=CNF.from_lists(n,clauses)
    truth=exhaustive_count(cnf)
    for model in (original_cnf_model(cnf),copy3_model(cnf)):
        plan=elimination_order(model,'min_degree')
        for engine in (indexed_contract_order,sparse_contract_order,contract_order):
            exact,_=engine(model,plan)
            assert exact==truth,(case,model.representation,engine.__name__)
            counts['cross_checks']+=1
            for precision in (1,3,8):
                rem,_=engine(model,plan,modulus=1<<precision)
                assert rem==truth%(1<<precision),(case,model.representation,engine.__name__)
                counts['cross_checks']+=1
    result=adaptive_count(cnf,execution_mode='indexed',precision_bits=4)
    assert int(result['count'])==truth%16
    counts['cross_checks']+=1
    counts['instances']+=1
out=Path(__file__).resolve().parents[1]/'validation'/'validation_v16.json'
out.write_text(json.dumps(counts,indent=2)+'\n')
print(json.dumps(counts))
