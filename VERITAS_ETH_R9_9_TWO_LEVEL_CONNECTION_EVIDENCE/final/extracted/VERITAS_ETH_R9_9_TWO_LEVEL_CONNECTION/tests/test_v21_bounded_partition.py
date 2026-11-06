"""v2.1: finite proxy exactness, bounded fallback, checker adversaries and API."""
import random
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from veritas.research.tensor import Factor, TensorNetwork, from_cnf
from veritas.research.optimal_packets import optimize_packets_exact
from veritas.research.packet_schedule import relabel_network
from veritas.research.tensor import brute_contract
from veritas.research.bounded_partition import (
    optimize_packets_bounded, partition_lower_bound, pair_weights)
from veritas.research.bounded_partition_checker import verify_bounded_partition
from veritas.core.cnf import CNF
from veritas.api.main import app
from veritas.audit.store import AuditStore


def network(n,seed=0):
    r=random.Random(seed)
    incidence=[[] for _ in range(max(4,(n+1)//2))]
    for w in range(n):
        a,b=r.sample(range(len(incidence)),2)
        incidence[a].append(w);incidence[b].append(w)
    return TensorNetwork(n,tuple(Factor(tuple(ports),(1,)*(1<<len(ports)),str(i))
                                    for i,ports in enumerate(incidence)))


@pytest.mark.parametrize('k',[1,2,4,8])
def test_independent_optimum_small(k):
    for n in range(0,11):
        for seed in range(3):
            net=network(n,seed)
            plan,proof=optimize_packets_bounded(net,packet_size=k,timeout_s=8)
            ref,_=optimize_packets_exact(net,packet_size=k,timeout_s=8)
            assert plan.exact_optimum
            assert (plan.optimized_collisions,plan.optimized_max_incidence)==(
                ref.optimized_collisions,ref.optimized_max_incidence)
            good,why=verify_bounded_partition(net,plan,proof)
            assert good, why
            assert proof.absolute_gap_pairs==0


def test_interrupted_budget_never_claims_exact_optimality():
    net=network(17,902)
    plan,proof=optimize_packets_bounded(net,packet_size=4,max_states=1,
                                       max_blocks=1,independent_check=False)
    assert not plan.exact_optimum
    assert not proof.finished_search
    assert proof.lower_bound_pairs<=plan.optimized_collisions
    assert verify_bounded_partition(net,plan,proof)[0]


def test_tampered_evidence_is_rejected():
    net=network(10,102)
    plan,proof=optimize_packets_bounded(net,packet_size=4)
    assert verify_bounded_partition(net,plan,proof)[0]
    assert not verify_bounded_partition(net,plan,replace(proof,lower_bound_pairs=10000))[0]
    assert not verify_bounded_partition(net,plan,replace(proof,independent_oracle_checked=True,
                            optimum_status='INDEPENDENT_SUBSET_DP',oracle_pairs=12345))[0]
    assert not verify_bounded_partition(net,replace(plan,wire_order=tuple(reversed(plan.wire_order))),proof)[0] or (
        tuple(reversed(plan.wire_order))==plan.wire_order)


def test_lower_bound_admissible_and_enforced_divisibility():
    net=network(8,17)
    w=pair_weights(net)
    assert 0<=partition_lower_bound(w,4,tuple(range(8)))
    with pytest.raises(ValueError):
        partition_lower_bound(w,4,(0,1,2))


def test_count_preservation_by_relabeling():
    cnf=CNF.from_lists(3,[[1,2],[-1,3],[2,3]])
    net=from_cnf(cnf)
    for k in (2,4,8):
        plan,proof=optimize_packets_bounded(net,packet_size=k)
        assert brute_contract(net,max_edges=12)==brute_contract(
            relabel_network(net,plan.wire_order),max_edges=12)


def test_api_bounded(tmp_path):
    app.state.audit=AuditStore(tmp_path/'v21.sqlite3')
    c=TestClient(app)
    body={'n':3,'clauses':[[1,2],[-1,3]],'optimizer':'bounded',
          'packet_size':4,'cross_check':True}
    response=c.post('/v1/research/packet-schedule',json=body)
    assert response.status_code==200,response.text
    obj=response.json()
    assert obj['bounded_partition_evidence']['packet_size']==4
    assert obj['bounded_partition_replay'].startswith(('SCORE_BOUND','FEASIBLE_SCORE'))
    assert obj['original_count_check'] is not None
    assert c.get('/health').json()['version']=='2.4.0'
    bad=c.post('/v1/research/packet-schedule',json={**body,'max_states':0})
    assert bad.status_code==422
    cutoff=c.post('/v1/research/packet-schedule',json={**body,
                 'max_states':1,'max_blocks':1,'cross_check':False})
    assert cutoff.status_code==200
    assert cutoff.json()['bounded_partition_evidence']['finished_search'] is False
