"""Seeded, standalone weighted DAG and exact conditional regression checks."""
import random
import sys
from fractions import Fraction
from itertools import product

from veritas.core.cnf import CNF
from veritas.solvers.weighted_dag import (
    make_weighted_dag_certificate, check_weighted_dag_certificate,
    parse_weights, decode_fraction,
)
from veritas.solvers.conditional import exact_conditional


def oracle(cnf, weights):
    parsed = parse_weights(cnf.n,weights)
    answer = Fraction(0)
    for bits in product((False,True),repeat=cnf.n):
        if cnf.evaluate(dict(enumerate(bits,1))):
            z = Fraction(1)
            for v, bit in enumerate(bits, 1): z *= parsed[v][int(bit)]
            answer += z
    return answer


def main():
    rng = random.Random(230026)
    trials = 1600
    for idx in range(trials):
        n=rng.randrange(9)
        cnf=CNF.from_lists(n,[[rng.choice((-1,1))*rng.randint(1,n)
                            for _ in range(rng.randrange(5))] if n else []
                           for _ in range(rng.randrange(10))])
        choices=('0','1','2/3','1/2','3','1/4','5/2')
        weights={str(v):[rng.choice(choices),rng.choice(choices)] for v in range(1,n+1)}
        proof=make_weighted_dag_certificate(cnf,weights)
        if proof.status != 'WEIGHTED_COUNT':
            raise AssertionError((idx,proof.reason))
        verified, reason, value, _=check_weighted_dag_certificate(cnf,weights,proof.certificate)
        if not verified or decode_fraction(value)!=oracle(cnf,weights):
            raise AssertionError((idx,reason))
    conditional=100
    for idx in range(conditional):
        n=rng.randint(1,6)
        x=CNF.from_lists(n,[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randrange(1,4))] for _ in range(rng.randrange(5))])
        q=CNF.from_lists(n,[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randrange(1,4))] for _ in range(rng.randrange(4))])
        weights={str(v): ['1/2','1/2'] if rng.randrange(2) else ['1/3','2/3'] for v in range(1,n+1)}
        got=exact_conditional(x,q,weights)
        den=oracle(x,weights)
        num=oracle(x.with_extra_clauses([list(c) for c in q.clauses]),weights)
        if den == 0:
            assert got.status == 'UNDEFINED'
        else:
            assert got.status == 'PROBABILITY' and decode_fraction(got.probability)==num/den
    print(f'PASS: {trials} weighted exact-count certificates and {conditional} conditional queries vs independent exhaustive oracles')


if __name__=='__main__':main()
