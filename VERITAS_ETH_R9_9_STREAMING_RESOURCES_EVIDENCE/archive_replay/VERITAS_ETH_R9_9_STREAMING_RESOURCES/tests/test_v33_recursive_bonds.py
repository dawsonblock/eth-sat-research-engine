"""Exact v3.3 recursive sparse-mode contraction: independent finite oracles."""
from copy import deepcopy
from itertools import product
from random import Random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_packing_v26.constructor import construct_d3_packing
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_modes_v31 import make_jet_tile_modes
from veritas.research.eth_mode_bonds_v32.bonds import construct_bond_certificate
from veritas.research.eth_recursive_bonds_v33.recursive import (
    RecursiveContractor, RecursiveBudgetExceeded,
    construct_recursive_certificate, check_recursive_certificate)
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.jets import JetRing

def case(n=2,clauses=((1,2),),p=5,jet=2,node=1):
    net=from_cnf(CNF.from_lists(n,[list(x) for x in clauses]))
    d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
    modes=make_jet_tile_modes(d3,node=node,precision=p,extension_degree=3,jet_length=jet)
    return net,modes

def test_recursive_exact_certificate_three_way_oracles():
    net,modes=case()
    c=construct_recursive_certificate(net,modes)
    assert check_recursive_certificate(c)['valid']
    assert c['result']==construct_bond_certificate(net,modes)['result']
    assert c['stats']['calls']>=2
    assert c['scope']['manuscript_m_over_8_guarantee'] is False

def test_fail_closed_tampering_and_caps():
    net,modes=case();cert=construct_recursive_certificate(net,modes)
    for mutate in ('result','mode','network','child','scope','stats','claim'):
        corrupted=deepcopy(cert)
        if mutate=='result':corrupted['result'][0][0]+=1
        if mutate=='mode':corrupted['mode_certificate']['node']=0
        if mutate=='network':corrupted['network']['factors'][0]['table'][0]+=1
        if mutate=='child':corrupted['child_descriptions'][0]['entries'][0][0][0]+=1
        if mutate=='scope':corrupted['scope']['subexponential_runtime_proven']=True
        if mutate=='stats':corrupted['stats']['branches']+=1
        if mutate=='claim':corrupted['claim']='PROVEN_ETH'
        assert not check_recursive_certificate(corrupted)['valid'],mutate
    with pytest.raises((ValueError,RuntimeError)):
        construct_recursive_certificate(net,modes,max_work=1)

def test_randomized_full_cauchy_reference():
    rng=Random(330033);successful=0
    for _ in range(26):
        n=rng.randint(1,3)
        clauses=[[rng.choice((-1,1))*rng.randint(1,n)
            for j in range(rng.randint(1,2))] for i in range(rng.randint(1,2))]
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>5:continue
        d3=construct_d3_packing(make_bipartite_edges(net),r=2,a=1,max_packets=256)
        modes=make_jet_tile_modes(d3,node=rng.choice((-1,1)),precision=rng.randint(3,6),
            extension_degree=rng.randint(1,3),jet_length=rng.randint(1,3))
        cert=construct_recursive_certificate(net,modes)
        assert cert['result']==construct_bond_certificate(net,modes)['result']
        successful+=1
    assert successful>=18

def test_random_sparse_factor_bonds_against_independent_bruteforce():
    rng=Random(3300001)
    jr=JetRing(ExtensionRing(5,first_irreducible(2)),2)
    for _ in range(100):
        width=rng.randint(1,4);nf=rng.randint(1,5)
        factors=[]
        for f in range(nf):
            modes=tuple(sorted(rng.sample(range(width),rng.randint(0,min(3,width)))))
            table={}
            for key in product((0,1),repeat=len(modes)):
                if rng.random()>.35:
                    v=rng.randint(1,5)
                    table[key]=jr.elem([[v]])
            factors.append({'modes':modes,'table':table})
        contractor=RecursiveContractor(jr,max_work=200000,timeout_s=10)
        got,_=contractor.run(factors)
        open_modes=sorted(set(k for f in factors for k in f['modes']))
        expected=jr.zero
        for values in product((0,1),repeat=len(open_modes)):
            env=dict(zip(open_modes,values));val=jr.one
            for factor in factors:
                k=tuple(env[m] for m in factor['modes'])
                val=jr.mul(val,factor['table'].get(k,jr.zero))
            expected=jr.add(expected,val)
        assert got==expected

def test_component_splits_and_cache_hits():
    jr=JetRing(ExtensionRing(5,first_irreducible(1)),1)
    mk=lambda x:jr.elem([[x]])
    # Two independent modes have no shared factors, so can be separated.
    c=RecursiveContractor(jr)
    got,stats=c.run([{'modes':(0,),'table':{(0,):mk(1),(1,):mk(2)}},
                     {'modes':(1,),'table':{(0,):mk(3),(1,):mk(4)}}])
    assert got==mk(21) and stats['component_splits']>=1
    # Each branch of mode 0 leaves the same residual mode-1 problem.
    c=RecursiveContractor(jr)
    got,stats=c.run([{'modes':(0,),'table':{(0,):mk(1),(1,):mk(1)}},
                     {'modes':(0,1),'table':{(a,b):mk(1) for a,b in product((0,1),repeat=2)}},
                     {'modes':(1,),'table':{(0,):mk(2),(1,):mk(3)}}])
    assert got==mk(10) and stats['cache_hits']>=1

def test_api_and_cli(tmp_path):
    from fastapi.testclient import TestClient
    from veritas.api.main import app
    client=TestClient(app)
    s=client.get('/v1/research/eth/v33/status')
    assert s.status_code==200 and 'not_implemented' in s.json()
    r=client.post('/v1/research/eth/recursive-mode-bonds',json={'n':2,'clauses':[[1,2]]})
    assert r.status_code==200,r.text
    c=r.json()['certificate']
    v=client.post('/v1/research/eth/recursive-mode-bonds/check',json={'certificate':c})
    assert v.status_code==200 and v.json()['valid']
    from veritas.research.eth_recursive_bonds_v33.cli import main
    path=tmp_path/'cert.json'
    assert main(['construct','--output',str(path)])==0
    assert main(['check','--certificate',str(path)])==0
