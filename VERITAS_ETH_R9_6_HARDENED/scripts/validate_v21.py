"""Deterministic v2.1 differential and adversarial validation."""
import json
import random
import time
from pathlib import Path

from veritas.research.tensor import TensorNetwork,Factor
from veritas.research.optimal_packets import optimize_packets_exact
from veritas.research.bounded_partition import optimize_packets_bounded
from veritas.research.bounded_partition_checker import verify_bounded_partition

root=Path(__file__).resolve().parents[1]
rng=random.Random(210026)
started=time.monotonic(); trials=0;cutoffs=0
for k in (1,2,4,8):
    for n in range(0,11):
        for sample in range(10):
            m=max(4,(n+1)//2)
            ports=[[] for _ in range(m)]
            for v in range(n):
                a,b=rng.sample(range(m),2)
                ports[a].append(v);ports[b].append(v)
            net=TensorNetwork(n,tuple(Factor(tuple(p),tuple((i+j)%2 for j in range(1<<len(p))),str(i))
                                          for i,p in enumerate(ports)))
            plan,ev=optimize_packets_bounded(net,packet_size=k,timeout_s=8)
            oracle,_=optimize_packets_exact(net,packet_size=k,timeout_s=8)
            assert (plan.optimized_collisions,plan.optimized_max_incidence)==(oracle.optimized_collisions,oracle.optimized_max_incidence)
            good,why=verify_bounded_partition(net,plan,ev)
            assert good,why
            trials+=1
    # Force finite-resource fallback on a nontrivial network.
    n=17;m=9;ports=[[] for _ in range(m)]
    for v in range(n):
        a,b=rng.sample(range(m),2)
        ports[a].append(v);ports[b].append(v)
    net=TensorNetwork(n,tuple(Factor(tuple(p),(1,)*(1<<len(p)),str(i)) for i,p in enumerate(ports)))
    plan,ev=optimize_packets_bounded(net,packet_size=k,max_states=1,max_blocks=1,independent_check=False)
    good,why=verify_bounded_partition(net,plan,ev)
    assert good,why
    assert not plan.exact_optimum
    cutoffs+=1

report={'version':'2.1.0','seed':210026,'independent_optimality_comparisons':trials,
        'budget_cutoff_replays':cutoffs,'all_passed':True,
        'elapsed_seconds':round(time.monotonic()-started,3),
        'scope':'finite packet incidence surrogate only; not ETH D.3 or D.4.4'}
from _evidence import evidence_path, write_evidence
write_evidence(evidence_path('validation/validation_v21.json',root=root),
               json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
