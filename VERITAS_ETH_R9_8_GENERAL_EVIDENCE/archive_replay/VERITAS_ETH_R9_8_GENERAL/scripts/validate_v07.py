"""Seeded independent check: split-wire polynomial vs 4**E exhaustive oracle.

Checks degree-0 CNF count and two independent rank-one identities. This
is not a proof of OpenAI's ETH algorithm. The standalone report is committed
in the release and can be recreated with the same seed.
"""
import json
import random
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count
from veritas.research.tensor import from_cnf
from veritas.research.wire_deformation import (
    deform_polynomial, independent_defect_histogram, check_deformation_invariants,
)

rng = random.Random(20261030)
verified = 0
modular = 0
attempts = 0
while verified < 250:
    attempts += 1
    n = rng.randrange(0, 5)
    clauses = [[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randrange(0, 4))] if n else []
               for _ in range(rng.randrange(0,5))]
    if sum(map(len,clauses)) > 6:
        continue
    cnf = CNF.from_lists(n,clauses)
    network=from_cnf(cnf,max_degree=14)
    poly,stats=deform_polynomial(network)
    assert poly == independent_defect_histogram(network)
    assert poly[0] == exhaustive_count(cnf,max_vars=5)
    check_deformation_invariants(network,poly)
    for p in (1,3,6):
        reduced,_=deform_polynomial(network,precision_bits=p)
        assert reduced == [c%(1<<p) for c in poly]
        check_deformation_invariants(network,reduced,precision_bits=p)
        modular+=1
    verified+=1
result={
    'release':'0.7.0', 'status':'PASS','seed':20261030,
    'exact_split_wire_vs_independent_half_edge_histograms':verified,
    'modular_cross_checks':modular,
    'max_edges_tested':6,
    'limitations':'Small exact reference cases; no Cauchy deformation or ETH asymptotic guarantee',
}
path=Path(__file__).resolve().parents[1]/'validation'/'validation_v07.json'
path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
