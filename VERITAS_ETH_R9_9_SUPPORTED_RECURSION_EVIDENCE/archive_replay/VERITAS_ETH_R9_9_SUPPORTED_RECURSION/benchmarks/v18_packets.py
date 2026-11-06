"""Machine-specific, nonrepresentative finite packet planner comparisons."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from time import perf_counter
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.packet_schedule import plan_packets
from veritas.research.optimal_packets import optimize_packets_exact

cases={
 '6-wire': CNF.from_lists(4,[[1,2],[-1,3],[2,4]]),
 '9-wire': CNF.from_lists(5,[[1,2,3],[-1,4,5],[3,-4,2]]),
 '15-wire': CNF.from_lists(8,[[1,2,3],[-1,4],[2,-3,5],[-2,6],[3,7],[-4,8,1]]),
}
# CNF cases are supplemented by an adversarial factor-network case below.
for label,cnf in cases.items():
 net=from_cnf(cnf)
 for k in (2,4):
    t=perf_counter();a=plan_packets(net,packet_size=k,timeout_s=10); old=perf_counter()-t
    t=perf_counter();b,ev=optimize_packets_exact(net,packet_size=k,timeout_s=10); new=perf_counter()-t
    assert (b.optimized_collisions,b.optimized_max_incidence)<=(a.optimized_collisions,a.optimized_max_incidence)
    print({'case':label,'packet_size':k, 'wires':net.edges,
           'legacy_collisions':a.optimized_collisions,'exact_collisions':b.optimized_collisions,
           'legacy_exact':a.exact_optimum,'dp_exact':b.exact_optimum,
           'legacy_seconds':round(old,6),'dp_seconds':round(new,6),
           'subset_states':ev.subset_states,'block_transitions':ev.evaluated_blocks})

from veritas.research.tensor import TensorNetwork, Factor
ports=((0,4,5,9),(2,),(3,7,11),(10,),(1,2,5),(1,10),(6,7,8,11),(0,3,4,6,8,9))
net=TensorNetwork(12,tuple(Factor(p,(1,)*(1<<len(p)),f'factor:{i}') for i,p in enumerate(ports)))
t=perf_counter();legacy=plan_packets(net,packet_size=4,timeout_s=5);old=perf_counter()-t
t=perf_counter();exact,evidence=optimize_packets_exact(net,packet_size=4,timeout_s=5);new=perf_counter()-t
assert (legacy.optimized_collisions,exact.optimized_collisions)==(6,5)
print({'case':'12-wire-adversarial-factor-network','packet_size':4,
       'legacy_collisions':6,'exact_collisions':5,'legacy_seconds':round(old,6),
       'dp_seconds':round(new,6),'dp_exact':exact.exact_optimum})
