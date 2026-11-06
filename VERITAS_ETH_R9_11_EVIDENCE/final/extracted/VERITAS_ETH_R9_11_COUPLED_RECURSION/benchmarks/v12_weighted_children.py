"""Small illustrative performance comparison; no asymptotic implications."""
import json
from time import perf_counter
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.weighted_children import recursive_weighted_jet
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod

for clauses,n in [([[1]],1),([[1,2]],2),([[1,2],[-2,3]],3),([[1,-2],[-1,3]],3)]:
    net=from_cnf(CNF.from_lists(n,clauses))
    start=perf_counter()
    jet, modes, stats=recursive_weighted_jet(net,packet_size=2,node=1,precision_bits=12,jet_order=5)
    recursive_s=perf_counter()-start
    start=perf_counter()
    oracle,_=shifted_cauchy_jet_mod(net,packet_size=2,node=1,precision_bits=12,jet_order=5,max_edges=6)
    reference_s=perf_counter()-start
    assert jet==oracle
    print(json.dumps({'clauses':clauses,'edges':net.edges,'child_tensor_s':round(recursive_s,7),
                      'exhaustive_s':round(reference_s,7),'max_join_vars':stats.max_join_variables,
                      'mode_count':len(modes),'equal':True,'scope':'tiny example; no extrapolation'}))
