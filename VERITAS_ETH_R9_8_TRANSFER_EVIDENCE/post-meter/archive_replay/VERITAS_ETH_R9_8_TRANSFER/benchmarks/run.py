"""Seeded CPU-only benchmark; prints JSONL to stdout. No speedup claims."""
import json, random, time
from veritas.core.cnf import CNF
from veritas.solvers.reference import solve, exhaustive_count
from veritas.research.tensor import from_cnf, eliminate


def run():
    rng = random.Random(20261029)
    for n in (4,6,8,10,12,14,16):
        for instance in range(6):
            clauses = [[rng.choice((-1,1))*rng.randint(1,n) for __ in range(3)] for _ in range(3*n)]
            cnf = CNF.from_lists(n,clauses)
            t = time.perf_counter()
            result = solve(cnf, count=True, timeout_s=5.0)
            timing = time.perf_counter()-t
            count = result.count
            oracle = exhaustive_count(cnf) if n <= 12 else None
            if oracle is not None and count is not None and oracle != count:
                raise RuntimeError('COUNT MISMATCH')
            print(json.dumps({'n':n,'instance':instance,'clauses':len(clauses),
                              'status':result.status,'count':str(count) if count is not None else None,
                              'time_s':round(timing,6),'nodes':result.nodes,
                              'oracle_matched':(oracle == count) if oracle is not None and count is not None else None}),flush=True)

if __name__ == '__main__': run()
