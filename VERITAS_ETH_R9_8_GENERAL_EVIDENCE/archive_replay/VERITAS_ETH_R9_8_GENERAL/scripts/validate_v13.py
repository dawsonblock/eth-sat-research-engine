"""Seeded end-to-end exact reconstruction vs an independent Boolean oracle."""
import json
import random
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.weighted_recovery import recover_weighted_count, verify_recovery_transcript


def main():
    rng=random.Random(2026103013)
    tested=0
    for i in range(300):
        n=rng.randrange(0,5)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            clause=[]
            for _ in range(rng.randrange(0,3)):
                if n:
                    clause.append(rng.choice([-1,1])*rng.randrange(1,n+1))
            if len(clause)+sum(map(len,clauses))>5:break
            clauses.append(clause)
        cnf=CNF.from_lists(n,clauses)
        result=recover_weighted_count(cnf,packet_size=2,
                    group_span=1 if (i%2) else 2,cross_check=True)
        assert result.exact_count==exhaustive_count(cnf,max_vars=12),(n,clauses)
        assert verify_recovery_transcript(cnf,result,replay_jets=i%25==0)
        tested+=1
    report={'release':'1.3.0','seed':2026103013,'differential_cases_passed':tested,
       'transcript_replays':(tested+24)//25,'algorithm':'bounded_weighted_child_jets_plus_guarded_hermite',
       'status':'PASS','eth_asymptotic_claim':'NOT_IMPLEMENTED'}
    target=Path(__file__).resolve().parents[1]/'validation/validation_v13.json'
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
