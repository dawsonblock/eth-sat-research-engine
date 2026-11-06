"""Independent deterministic exhaustive-oracle audit of exact posterior marginals."""
from __future__ import annotations
from fractions import Fraction
from itertools import product
from pathlib import Path
from time import perf_counter
import json
import random

from veritas.core.cnf import CNF
from veritas.solvers.marginals import exact_marginals, check_marginal_certificate
from veritas.solvers.weighted_dag import decode_fraction, parse_weights


def main():
    rng = random.Random(240026)
    begin = perf_counter()
    cases = 0
    posterior_cells = 0
    zero_evidence = 0
    weight_options = [('1/2','1/2'),('0','1'),('1','0'),('1/3','2/3'),('3/5','2/5')]
    for _ in range(1000):
        n = rng.randrange(0, 9)
        clauses = [[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,4))]
                   for _ in range(rng.randrange(0,9))] if n else ([[]] if rng.randrange(2) else [])
        cnf = CNF.from_lists(n, clauses)
        supplied = {str(v): list(rng.choice(weight_options)) for v in range(1,n+1)}
        weights = parse_weights(n,supplied)
        actual = exact_marginals(cnf,supplied)
        assert actual.status in ('POSTERIORS','UNDEFINED'), (actual.status, actual.reason)
        ok,why,status,checked,visited = check_marginal_certificate(cnf,supplied,actual.certificate)
        assert ok and status==actual.status and checked==actual.marginals,why
        z = Fraction(0)
        joints = [[Fraction(0),Fraction(0)] for _ in range(n+1)]
        for bits in product((0,1),repeat=n):
            if not cnf.evaluate({v:bool(bits[v-1]) for v in range(1,n+1)}):continue
            mass = Fraction(1)
            for v,bit in enumerate(bits,1):mass*=weights[v][bit]
            z+=mass
            for v,bit in enumerate(bits,1):joints[v][bit]+=mass
        assert decode_fraction(actual.evidence_weight)==z
        if z:
            for v in range(1,n+1):
                assert [decode_fraction(x) for x in actual.marginals[str(v)]]==[joints[v][0]/z,joints[v][1]/z]
                posterior_cells+=2
        else:
            assert actual.status=='UNDEFINED' and actual.marginals is None
            zero_evidence+=1
        cases+=1
    result={'release':'2.4.0','seed':240026,'cases':cases,'posterior_cells':posterior_cells,
            'zero_evidence_cases':zero_evidence,'all_checks_passed':True,
            'exhaustive_truth_table_oracle':True,
            'dag_replay_checked':True,
            'elapsed_seconds':round(perf_counter()-begin,3),
            'claim_scope':'Small-instance exact correctness only; no asymptotic speedup proved'}
    dest=Path(__file__).resolve().parents[1]/'validation/validation_v24.json'
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
