"""Seeded, explicitly small performance comparison: bounded vs subset-DP."""
import json
from pathlib import Path
from time import perf_counter
import random
from veritas.research.tensor import TensorNetwork,Factor
from veritas.research.bounded_partition import optimize_packets_bounded
from veritas.research.optimal_packets import optimize_packets_exact

rng=random.Random(21)
rows=[]
for n,k in [(8,4),(10,4),(12,4),(12,8)]:
    incidence=[[] for _ in range(7)]
    for v in range(n):
        a,b=rng.sample(range(7),2)
        incidence[a].append(v);incidence[b].append(v)
    net=TensorNetwork(n,tuple(Factor(tuple(f),(1,)*(1<<len(f)),str(i)) for i,f in enumerate(incidence)))
    t=perf_counter();old,_=optimize_packets_exact(net,packet_size=k,timeout_s=8)
    old_ms=1000*(perf_counter()-t)
    t=perf_counter();new,ev=optimize_packets_bounded(net,packet_size=k,timeout_s=8)
    new_ms=1000*(perf_counter()-t)
    assert (old.optimized_collisions,old.optimized_max_incidence)==(new.optimized_collisions,new.optimized_max_incidence)
    rows.append({'wires':n,'packet_size':k,'finite_collision_score':new.optimized_collisions,
                 'subset_dp_ms':round(old_ms,3),'bounded_branch_ms':round(new_ms,3),
                 'bounded_visited_states':ev.visited_states,'bounded_blocks':ev.tested_blocks,
                 'full_search_completed':ev.finished_search})
output={'version':'2.1.0','workload':'seeded small finite packet proxies',
        'warning':'Not a SAT or tensor contraction speed benchmark; hardware dependent.',
        'rows':rows}
path=Path(__file__).resolve().parents[1]/'validation/benchmark_v21.json';path.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
