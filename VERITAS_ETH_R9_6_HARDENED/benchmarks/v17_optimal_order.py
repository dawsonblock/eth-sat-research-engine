"""v1.7 objective vs baseline and observed timing, no extrapolated claims."""
from __future__ import annotations
from statistics import median
from time import perf_counter
from pathlib import Path
import json
from veritas.core.cnf import CNF
from veritas.research.contraction_planner import original_cnf_model, elimination_order
from veritas.research.optimal_order import optimize_small_model
from veritas.research.indexed_contract import indexed_contract_order
from veritas.solvers.reference import exhaustive_count

CASES={
    'sparse_chain':(9, [[i,i+1] for i in range(1,9)]),
    'dense_triples':(8, [[1,2,3],[2,4,5],[3,5,6],[4,6,7],[1,7,8],[2,6,8]]),
    'min_degree_counterexample':(9,[[-7,9],[-2,4],[3,-5],[8,1],[3,-7],[-4,8],
        [1,5,-8],[8,-5],[-3,7,2],[-9,1,5],[5,-7],[-3,7],[-1,6,4],
        [2,6],[1,-3],[-7,-5],[-1,8,-5],[-8,4,7],[-9,3,-7],[-7,2],[-8,-6]])
}

def main():
    results=[]
    for name,(n,clauses) in CASES.items():
        cnf=CNF.from_lists(n,clauses)
        model=original_cnf_model(cnf)
        expected=exhaustive_count(cnf)
        row={'case':name,'variables':n,'clauses':len(clauses),'correct_count':str(expected)}
        for label,planner in [('quick',lambda:elimination_order(model,'min_degree')),
                              ('optimal',lambda:optimize_small_model(model)[0])]:
            planning=[]; running=[];plan=None
            for rep in range(7):
                start=perf_counter(); plan=planner(); planning.append(perf_counter()-start)
                start=perf_counter(); result,_=indexed_contract_order(model,plan);running.append(perf_counter()-start)
                assert result==expected
            row[label]={'estimated_assignments':plan.estimated_assignments,
                        'induced_width':plan.induced_width,
                        'median_planning_seconds':median(planning),
                        'median_execution_seconds':median(running),
                        'median_total_seconds':median([a+b for a,b in zip(planning,running)])}
        results.append(row)
    output={'version':'1.7.0','repeat_count':7,'runtime_guaranteed_faster':False,
            'environment':'local machine at validation time','cases':results}
    path=Path('validation/benchmark_v17.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
