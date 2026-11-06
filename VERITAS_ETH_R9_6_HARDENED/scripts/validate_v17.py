"""Seeded finite-instance independent differential check for v1.7.

The score optimum is independently enumerated over all order permutations
on <=6 vertices; larger instances validate exact counts but not optimality.
"""
import itertools
import json
import random
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.adaptive_contract import adaptive_count
from veritas.research.optimal_order import optimize_small_model, replay_order
from veritas.research.contraction_planner import original_cnf_model, elimination_order


def main():
    rng=random.Random(170017)
    score_checks=0
    count_checks=0
    strict_improvements=0
    for i in range(240):
        n=rng.randrange(0,9)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n)
                  for _ in range(rng.randrange(0,4))]
                 for _ in range(rng.randrange(0,13))] if n else ([[]] if i%2 else [])
        cnf=CNF.from_lists(n,clauses)
        model=original_cnf_model(cnf)
        plan,proof=optimize_small_model(model)
        quick=elimination_order(model,'min_degree')
        assert plan.estimated_assignments<=quick.estimated_assignments
        strict_improvements+=plan.estimated_assignments<quick.estimated_assignments
        if n<=6:
            costs=[replay_order(model,order)[0] for order in itertools.permutations(model.variables)]
            assert plan.estimated_assignments==min(costs)
            score_checks+=1
        expected=exhaustive_count(cnf)
        for mode in ('indexed','sparse'):
            result=adaptive_count(cnf,portfolio_mode='optimal_small',
                                  include_copy3=False,enable_separators=False,
                                  execution_mode=mode,timeout_s=10)
            assert int(result['count'])==expected
            count_checks+=1
        modular=adaptive_count(cnf,portfolio_mode='optimal_small',
                               include_copy3=False,enable_separators=False,
                               precision_bits=6,execution_mode='indexed')
        assert int(modular['count'])==expected%64
        count_checks+=1
    output={'version':'1.7.0','seed':170017,'instances':240,
            'independent_permutation_optimality_checks':score_checks,
            'exact_or_modular_count_comparisons':count_checks,
            'strict_cost_proxy_improvements_over_min_degree':strict_improvements,
            'paper_subexponential_recursion_reproduced':False}
    from _evidence import evidence_path, write_evidence
    write_evidence(evidence_path('validation/validation_v17.json'),
                   json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))

if __name__=='__main__':main()
