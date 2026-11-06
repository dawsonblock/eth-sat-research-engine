"""Deterministic independent oracle trials; result JSON saved for release audit."""
from __future__ import annotations
from pathlib import Path
import itertools
import json
import random
import time
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.solvers.projected import projected_count
from veritas.solvers.certificates import make_unsat_certificate, check_unsat_certificate

ROOT = Path(__file__).resolve().parents[1]


def oracle_projection(cnf, variables):
    distinct = set()
    for values in itertools.product((False, True), repeat=cnf.n):
        model = {i+1:v for i,v in enumerate(values)}
        if cnf.evaluate(model):
            distinct.add(tuple(model[v] for v in variables))
    return len(distinct)


def main():
    rng = random.Random(2026102919)
    total = 1200
    proofs = 0
    sats = 0
    checks = 0
    start = time.monotonic()
    for trial in range(total):
        n = rng.randrange(0,8)
        clauses = [[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randrange(0,5))] if n else []
                   for __ in range(rng.randrange(0,11))]
        cnf = CNF.from_lists(n,clauses)
        expected = exhaustive_count(cnf)
        built = make_unsat_certificate(cnf, timeout_s=5.0)
        if expected == 0:
            assert built.status == "UNSAT", (trial, built)
            valid, detail, _ = check_unsat_certificate(cnf,built.certificate)
            assert valid, (trial, detail)
            proofs += 1
        else:
            assert built.status == "SAT" and cnf.evaluate(built.model), (trial,built)
            sats += 1
        projection = rng.sample(range(1,n+1),rng.randrange(n+1))
        result = projected_count(cnf,projection,timeout_s=5.0)
        assert result.status == 'COUNT', (trial,result)
        assert result.count == oracle_projection(cnf,projection), (trial, result, projection)
        checks += 1
    output = {
        "version":"0.5.0", "seed":2026102919,
        "trial_count":total, "proofs_independently_checked":proofs,
        "satisfiable_witnesses_checked":sats,
        "projected_counts_cross_checked":checks,
        "failures":0,
        "duration_seconds":round(time.monotonic()-start,3),
        "limits":"Random CNF <=7 variables; bounded certificate trees; not ETH algorithm validation",
    }
    dest = ROOT/'validation'/'validation_upgrade_1200.json'
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))

if __name__=='__main__':
    main()
