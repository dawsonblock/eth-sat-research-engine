"""Seeded deterministic random small-instance differential checks (v2.0)."""
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, eliminate
from veritas.research.optimal_packets import optimize_packets_exact
from veritas.research.matching_packets import optimize_packets_matching
from veritas.research.matching_checker import verify_matching_evidence
from veritas.research.packet_schedule import relabel_network
import json
rng=Random(20261030)
verified=0
for i in range(250):
    n=rng.randint(1,6)
    cs=[]
    for j in range(rng.randint(0,6)):
        width=rng.randint(1,min(n,3))
        cs.append([v if rng.randrange(2) else -v for v in rng.sample(range(1,n+1),width)])
    net=from_cnf(CNF.from_lists(n,cs),max_degree=16)
    if net.edges>16:continue
    plan,proof=optimize_packets_matching(net)
    assert verify_matching_evidence(net,plan,proof)[0]
    oracle,_=optimize_packets_exact(net,packet_size=2,timeout_s=5)
    assert (plan.optimized_collisions,plan.optimized_max_incidence)==(oracle.optimized_collisions,oracle.optimized_max_incidence)
    original=eliminate(net,max_table_entries=1<<16)
    recoded=eliminate(relabel_network(net,plan.wire_order),max_table_entries=1<<16)
    assert original==recoded
    verified+=1
assert verified>=175, verified
print(json.dumps({'seed':20261030,'oracle_and_count_comparisons':verified,'result':'PASS'}))
