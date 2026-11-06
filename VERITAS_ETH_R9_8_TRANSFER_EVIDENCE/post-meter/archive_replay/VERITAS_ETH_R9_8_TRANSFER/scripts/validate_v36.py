"""Seeded v3.6 packet coefficient/reference and tamper validation."""
from random import Random
from copy import deepcopy
import json
from pathlib import Path
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_packet_tensors_v36 import construct_packet_tensor_certificate,check_packet_tensor_certificate
rng=Random(360036)
ok=0;rejected=0;moebius=0
for i in range(40):
    n=rng.randint(1,3)
    clauses=[[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(1,2))] for _ in range(rng.randint(1,2))]
    net=from_cnf(CNF.from_lists(n,clauses))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    mode=make_jet_tile_modes(d3,node=1,precision=rng.choice((4,5,6)),extension_degree=3,jet_length=2)
    cert=construct_packet_tensor_certificate(net,mode)
    assert check_packet_tensor_certificate(cert)['valid']
    moebius+=cert['stats']['moebius_assignments_checked'];ok+=1
    bad=deepcopy(cert)
    bad['subexponential_runtime_proven']=True
    assert not check_packet_tensor_certificate(bad)['valid'];rejected+=1
summary={'release':'3.6.0','status':'PASS','seed':360036,
         'packet_oracle_and_certificate_cases':ok,'forged_claim_rejections':rejected,
         'independently_checked_boolean_coefficient_assignments':moebius,
         'subexponential_algorithm_claimed':False}
Path('validation/v36_validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
