"""Seeded, reproducible v1.4 count-preserving gadget validation."""
import json,random
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.bounded_degree import bounded_degree_from_cnf
from veritas.research.minfill_contract import minfill_contract
from veritas.solvers.reference import exhaustive_count


def main():
    rng=random.Random(2026103014)
    comparisons=0
    for i in range(800):
        n=rng.randrange(0,7)
        clauses=[]
        for _ in range(rng.randrange(0,10)):
            width=rng.randrange(0,4) if n else 0
            clauses.append([rng.choice((-1,1))*rng.randrange(1,n+1) for _ in range(width)])
        cnf=CNF.from_lists(n,clauses)
        net,stats=bounded_degree_from_cnf(cnf,max_clause_width=3)
        oracle=exhaustive_count(cnf,max_vars=7)
        got,cstats=minfill_contract(net,max_table_entries=1<<12,timeout_s=15)
        assert got==oracle,(i,cnf,stats,cstats)
        assert stats.maximum_factor_degree<=3
        comparisons+=1
    report={'version':'1.4.0','seed':2026103014,'cases':comparisons,
            'result':'PASS','method':'exact_COPY3_bijection_plus_min_neighbor_oracle',
            'subexponential_ETH_contraction':'NOT_IMPLEMENTED'}
    output=Path(__file__).resolve().parents[1]/'validation'/'validation_v14.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
