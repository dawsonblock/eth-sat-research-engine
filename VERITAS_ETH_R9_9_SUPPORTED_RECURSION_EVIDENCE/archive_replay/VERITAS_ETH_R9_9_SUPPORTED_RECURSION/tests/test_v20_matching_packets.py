"""Differential and security-oriented tests for v2.0 pair-packet matching."""
from dataclasses import replace
from random import Random
from pathlib import Path
import subprocess,sys,json
import pytest
from fastapi.testclient import TestClient
from veritas.api.main import app
from veritas.audit.store import AuditStore
from veritas.core.cnf import CNF
from veritas.research.tensor import TensorNetwork, Factor, from_cnf, eliminate
from veritas.research.matching_packets import optimize_packets_matching
from veritas.research.matching_checker import verify_matching_evidence
from veritas.research.optimal_packets import optimize_packets_exact
from veritas.research.packet_schedule import collision_score, relabel_network


def ring(n: int) -> TensorNetwork:
    if n==0:return TensorNetwork(0,())
    if n==1:return TensorNetwork(1,(Factor((0,),(1,1),'a'),Factor((0,),(1,1),'b')))
    return TensorNetwork(n,tuple(Factor((i,(i+1)%n),(1,1,1,1),f'f{i}') for i in range(n)))


def test_exact_against_independent_subset_dp():
    for n in range(17):
        net=ring(n)
        plan,evidence=optimize_packets_matching(net)
        oracle,_=optimize_packets_exact(net,packet_size=2,timeout_s=5)
        assert collision_score(net,plan.wire_order,2)==collision_score(net,oracle.wire_order,2)
        assert evidence.oracle_checked
        assert verify_matching_evidence(net,plan,evidence)[0]


def test_random_cnf_differential_and_permutation_invariance():
    rng=Random(20261030)
    for _ in range(60):
        n=rng.randint(1,5)
        clauses=[]
        for i in range(rng.randint(0,5)):
            width=rng.randint(1,min(n,3))
            clauses.append([v if rng.randrange(2) else -v for v in rng.sample(range(1,n+1),width)])
        net=from_cnf(CNF.from_lists(n,clauses),max_degree=16)
        if net.edges>16:continue
        plan,proof=optimize_packets_matching(net)
        assert verify_matching_evidence(net,plan,proof)[0]
        oracle,_=optimize_packets_exact(net,packet_size=2)
        assert (plan.optimized_collisions,plan.optimized_max_incidence)==(oracle.optimized_collisions,oracle.optimized_max_incidence)
        assert eliminate(net,max_table_entries=1<<16)==eliminate(relabel_network(net,plan.wire_order),max_table_entries=1<<16)


def test_large_wire_network_and_certificate_caveat():
    net=ring(74)
    plan,proof=optimize_packets_matching(net)
    valid,reason=verify_matching_evidence(net,plan,proof)
    assert valid and reason=='FEASIBLE_SCORE_CHECKED_EXTERNAL_OPTIMALITY_ALGORITHM'
    assert not proof.oracle_checked
    assert proof.optimality_claim=='ALGORITHM_OPTIMUM_UNCERTIFIED_EXTERNAL_SOLVER'
    assert (plan.optimized_collisions,plan.optimized_max_incidence) <= (plan.original_collisions,plan.original_max_incidence)


def test_tampered_report_rejected():
    net=ring(8)
    plan,proof=optimize_packets_matching(net)
    assert verify_matching_evidence(net,plan,proof)[0]
    assert not verify_matching_evidence(net,plan,replace(proof,pair_objective=proof.pair_objective+1))[0]
    assert not verify_matching_evidence(net,plan,replace(proof,oracle_objective=999))[0]
    assert not verify_matching_evidence(net,replace(plan,wire_order=(0,)*8),proof)[0]
    assert not verify_matching_evidence(net,replace(plan,optimized_collisions=999),proof)[0]


def test_limits():
    net=ring(18)
    with pytest.raises(ValueError):optimize_packets_matching(net,max_wires=16)
    with pytest.raises(ValueError):optimize_packets_matching(net,max_wires=-1)
    with pytest.raises(ValueError):optimize_packets_matching(net,max_wires=True)


def test_api_matching_and_invalid_size(tmp_path):
    app.state.audit=AuditStore(tmp_path/'v20.sqlite3')
    c=TestClient(app)
    inp={'n':4,'clauses':[[1,2],[-2,3],[3,4]],'optimizer':'matching','packet_size':2}
    r=c.post('/v1/research/packet-schedule',json=inp)
    assert r.status_code==200,r.text
    d=r.json()
    assert d['status']=='SCHEDULE'
    assert d['matching_evidence']['algorithm']=='NETWORKX_BLOSSOM_MIN_WEIGHT_PERFECT_MATCHING'
    assert d['matching_independent_replay']=='MATCHING_FEASIBLE_AND_INDEPENDENT_DP_OPTIMUM'
    assert d['original_count_check'] is not None
    assert c.post('/v1/research/packet-schedule',json={**inp,'packet_size':4}).status_code==422
    assert c.get('/health').json()['version']=='2.4.0'


def test_matching_in_cauchy_elimination():
    from veritas.research.cauchy_elimination import eliminate_cauchy_jet
    from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
    net=from_cnf(CNF.from_lists(3,[[1,2],[-1,3]]))
    jet,stats=eliminate_cauchy_jet(net,packet_size=2,node=1,precision_bits=8,jet_order=3,
          optimize_packets=True,packet_optimizer='matching',timeout_s=8)
    assert stats.packet_schedule is not None
    reindexed=relabel_network(net,stats.packet_schedule.wire_order)
    independent,_=shifted_cauchy_jet_mod(reindexed,packet_size=2,node=1,precision_bits=8,jet_order=3)
    assert jet==independent


def test_cli_matching(tmp_path):
    path=tmp_path/'in.cnf';path.write_text('p cnf 3 2\n1 2 0\n-1 3 0\n')
    run=subprocess.run([sys.executable,'-m','veritas.cli','cnf',str(path),'--matching-packets','--packet-size','2'],
                       text=True,capture_output=True,timeout=25)
    assert run.returncode==0,run.stderr
    payload=json.loads(run.stdout)
    assert payload['status']=='FINITE_OPTIMAL_SCHEDULE'
    assert payload['matching_evidence']['oracle_checked'] is True
