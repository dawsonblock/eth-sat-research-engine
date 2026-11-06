"""Deterministic finite D.4.4 independent-checker validation runner."""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from veritas.research.eth_packing_v26 import construct_d3_packing
from veritas.research.eth_modes_v27 import construct_tile_modes,verify_tile_modes
from veritas.research.eth_modes_v27.reference import network_edges,check_full_scalar_identity
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf

rng=random.Random(270026)
accepted=0
for _ in range(125):
    a=rng.choice([1,2])
    edges=[[rng.randrange(3),rng.randrange(3)] for _ in range(rng.randint(1,7))]
    d3=construct_d3_packing(edges,r=2,a=a)
    t=rng.choice([n for n in range(-(1<<a),(1<<a)) if n and abs(n)% (1<<a)])
    mode=construct_tile_modes(d3,node=t,zeta=rng.randrange(0,4),precision=rng.randrange(2,8))
    res=verify_tile_modes(mode)
    if not res['valid']:raise AssertionError(res)
    accepted+=1
scalar=0
for _ in range(60):
    formula=CNF.from_lists(2,[[rng.choice([-1,1])*rng.randint(1,2)] for _ in range(rng.randint(1,4))])
    net=from_cnf(formula)
    d3=construct_d3_packing(network_edges(net),r=2,a=1)
    cert=construct_tile_modes(d3,node=rng.choice([-1,1]),zeta=rng.randrange(0,3),precision=rng.randrange(2,7))
    check_full_scalar_identity(net,cert)
    scalar+=1
print(json.dumps({'finite_mode_check_cases':accepted,'complete_scalar_identity_cases':scalar,
 'claimed_subexponential_solver':False,'result':'PASS'},indent=2))
