"""Independent oracle, tamper, resource-cap and integration checks for v1.9."""
from dataclasses import replace
from itertools import permutations
from random import Random

import pytest
from fastapi.testclient import TestClient

from veritas.api.main import app
from veritas.audit.store import AuditStore
from veritas.core.cnf import CNF
from veritas.research.packet_bound_checker import check_packet_search_evidence
from veritas.research.scalable_packets import collision_lower_bound, optimize_packets_scalable
from veritas.research.packet_schedule import collision_score, relabel_network
from veritas.research.tensor import from_cnf, eliminate


def make_small(seed):
    rng = Random(seed)
    n = rng.randrange(1, 5)
    clauses = []
    for _ in range(rng.randrange(1, 6)):
        width = rng.randrange(1, min(n, 3)+1)
        clauses.append([x*(1 if rng.getrandbits(1) else -1)
                        for x in rng.sample(range(1,n+1),width)])
    return from_cnf(CNF.from_lists(n,clauses), max_degree=12)


def test_lower_bounds_against_independent_permutation_oracle():
    checked = 0
    for seed in range(46):
        net = make_small(seed)
        if net.edges > 7:
            continue
        for k in (1,2,4,8):
            pair_lb, peak_lb = collision_lower_bound(net,k)
            global_opt = min(collision_score(net,order,k) for order in permutations(range(net.edges)))
            assert (pair_lb,peak_lb) <= global_opt
            plan, proof = optimize_packets_scalable(net,packet_size=k,timeout_s=2,max_evaluations=3000,
                                                    restarts=3,seed=seed)
            assert check_packet_search_evidence(net,plan,proof)[0]
            assert global_opt <= (plan.optimized_collisions,plan.optimized_max_incidence)
            assert plan.optimized_collisions <= plan.original_collisions
            if proof.exact_optimum_certified:
                assert (plan.optimized_collisions,plan.optimized_max_incidence)==global_opt
            checked += 1
    assert checked >= 75


def test_checker_rejects_forgery_and_invalid_schedule():
    net = from_cnf(CNF.from_lists(5,[[1,2],[2,3,4],[4,5],[1,5]]))
    plan,proof = optimize_packets_scalable(net,packet_size=4,max_evaluations=500)
    assert check_packet_search_evidence(net,plan,proof)[0]
    assert not check_packet_search_evidence(net,plan,replace(proof,pair_lower_bound=proof.pair_lower_bound+1))[0]
    assert not check_packet_search_evidence(net,plan,replace(proof,exact_optimum_certified=not proof.exact_optimum_certified))[0]
    assert not check_packet_search_evidence(net,replace(plan,wire_order=(0,)*net.edges),proof)[0]
    assert not check_packet_search_evidence(net,replace(plan,optimized_collisions=plan.optimized_collisions+1),proof)[0]


def test_large_wire_network_and_count_preserving_relabel():
    clauses = [[(i%39)+1, ((i+11)%39)+1] for i in range(52)]
    net = from_cnf(CNF.from_lists(39,clauses),max_degree=12)
    assert net.edges == 104
    plan,proof = optimize_packets_scalable(net,packet_size=4,timeout_s=5,max_evaluations=2200,restarts=2)
    assert check_packet_search_evidence(net,plan,proof)[0]
    assert plan.optimized_collisions <= plan.original_collisions
    assert len(set(plan.wire_order))==net.edges
    # No 2^104 enumeration here: wire relabeling is a mathematical bijection.
    permuted = relabel_network(net,plan.wire_order)
    assert sorted((tuple(sorted(f.ports)), f.table) for f in net.factors) != []
    assert len(permuted.factors)==len(net.factors)


def test_budget_behavior_and_determinism():
    net = make_small(2)
    results = [optimize_packets_scalable(net,packet_size=4,max_evaluations=100,restarts=4,seed=128)
               for _ in range(3)]
    assert results[0]==results[1]==results[2]
    for plan,proof in results:
        assert check_packet_search_evidence(net,plan,proof)[0]
        assert proof.candidate_swaps <= 100
    for invalid in [{'packet_size':3},{'timeout_s':0},{'max_evaluations':0},
                    {'restarts':65},{'seed':-1},{'max_wires':0}]:
        with pytest.raises(ValueError):
            optimize_packets_scalable(net,**invalid)


def test_api_scalable_and_legacy_paths(tmp_path):
    app.state.audit=AuditStore(tmp_path/'v19-api.sqlite3')
    client=TestClient(app)
    inp={'n':5,'clauses':[[1,2],[-1,3],[2,4],[3,5]],'optimizer':'scalable',
         'packet_size':2,'seed':81,'restarts':3}
    r=client.post('/v1/research/packet-schedule',json=inp)
    assert r.status_code==200, r.text
    d=r.json()
    assert d['status']=='SCHEDULE'
    assert d['scalable_lower_bound_evidence']['objective_replayed'] is True
    assert d['independent_lower_bound_check']
    assert d['original_count_check'] is not None
    assert client.get('/health').json()['version']=='2.4.0'
    large={'n':35,'clauses':[[i,i+1] for i in range(1,35)],
           'optimizer':'scalable','cross_check':False,'max_evaluations':1000}
    r=client.post('/v1/research/packet-schedule',json=large)
    assert r.status_code==200,r.text
    assert r.json()['status']=='SCHEDULE'
    assert r.json()['scalable_lower_bound_evidence']['wires']==68
    r=client.post('/v1/research/packet-schedule',json={**large,'cross_check':True})
    assert r.status_code==422
    assert client.post('/v1/research/packet-schedule',json={**inp,'optimizer':'bad'}).status_code==422
    legacy=client.post('/v1/research/packet-schedule',json={**inp,'optimizer':'legacy'})
    assert legacy.status_code==200


def test_cauchy_jet_with_scalable_schedule():
    from veritas.research.cauchy_elimination import eliminate_cauchy_jet
    from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
    net=from_cnf(CNF.from_lists(3,[[1,2],[-1,3]]))
    jet,stats=eliminate_cauchy_jet(net,packet_size=2,node=1,
       precision_bits=8,jet_order=3,timeout_s=6,packet_optimizer='scalable', optimize_packets=True)
    assert stats.packet_schedule is not None
    permuted=relabel_network(net,stats.packet_schedule.wire_order)
    oracle,_=shifted_cauchy_jet_mod(permuted,packet_size=2,node=1,precision_bits=8,jet_order=3)
    assert jet == oracle
