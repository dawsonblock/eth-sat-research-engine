"""Independent brute-force packet tests, integration and fail-closed caps."""
from itertools import permutations
from random import Random

import pytest
from fastapi.testclient import TestClient

from veritas.api.main import app
from veritas.audit.store import AuditStore
from veritas.core.cnf import CNF
from veritas.research.optimal_packets import optimize_packets_exact, PacketPlanningLimit
from veritas.research.packet_schedule import collision_score, plan_packets, relabel_network
from veritas.research.tensor import from_cnf, brute_contract, eliminate


def test_global_optima_independent_permutation_oracle():
    rng = Random(18002026)
    checked = 0
    for _ in range(75):
        n = rng.randrange(0, 5)
        clauses = []
        if n:
            for _ in range(rng.randrange(0, 5)):
                width = rng.randrange(0, min(3, n) + 1)
                clauses.append([v if rng.randrange(2) else -v
                                for v in rng.sample(range(1, n+1), width)])
        net = from_cnf(CNF.from_lists(n, clauses))
        if net.edges > 7:
            continue
        for k in (1, 2, 4, 8):
            plan, evidence = optimize_packets_exact(net, packet_size=k)
            oracle = min((collision_score(net, order, k), order)
                         for order in permutations(range(net.edges)))
            assert (plan.optimized_collisions, plan.optimized_max_incidence) == oracle[0]
            assert plan.wire_order == oracle[1]
            assert evidence.independent_score_replayed
            assert evidence.certificate_type == 'RECOMPUTABLE_EXHAUSTIVE_SUBSET_RECURRENCE'
            assert plan.exact_optimum
            checked += 1
    assert checked >= 100


def test_15_wire_dp_is_exact_and_count_preserving():
    # Much larger than legacy 8-wire exhaustive optimum, but within 16-wire DP.
    n = 8
    clauses = [[1,2,3],[-1,4],[2,-3,5],[-2,6],[3,7],[-4,8,1]]
    net = from_cnf(CNF.from_lists(n, clauses))
    assert net.edges == 15
    for packet in (2, 4, 8):
        result, evidence = optimize_packets_exact(net,packet_size=packet,timeout_s=10)
        assert len(result.wire_order) == 15
        assert result.optimized_collisions <= result.original_collisions
        assert evidence.subset_states <= 1<<15
        assert evidence.independent_score_replayed
    first, _ = optimize_packets_exact(net,packet_size=2)
    second, _ = optimize_packets_exact(net,packet_size=2)
    assert first == second
    assert brute_contract(net,max_edges=15) == eliminate(relabel_network(net,first.wire_order))


def test_budget_and_invalid_input():
    net = from_cnf(CNF.from_lists(4,[[1,2],[2,3],[3,4]]))
    with pytest.raises(PacketPlanningLimit):
        optimize_packets_exact(net,packet_size=2,max_states=1)
    with pytest.raises(PacketPlanningLimit):
        optimize_packets_exact(net,packet_size=2,max_transitions=1)
    with pytest.raises(PacketPlanningLimit):
        optimize_packets_exact(net,packet_size=2,max_wires=2)
    with pytest.raises(ValueError):
        optimize_packets_exact(net,packet_size=3)
    with pytest.raises(ValueError):
        optimize_packets_exact(net,packet_size=2,max_states=0)
    with pytest.raises(ValueError):
        optimize_packets_exact(net,packet_size=2,timeout_s=0)


def test_api_and_legacy_compatibility(tmp_path):
    app.state.audit = AuditStore(tmp_path/'v18_audit.sqlite3')
    client = TestClient(app)
    data = {'n':4,'clauses':[[1,2],[-1,3],[2,4]],'packet_size':2,'optimizer':'exact_dp'}
    response = client.post('/v1/research/packet-schedule',json=data)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'SCHEDULE'
    assert body['finite_optimum_evidence']['independent_score_replayed'] is True
    assert body['stats']['exact_optimum'] is True
    assert body['original_count_check'] is not None
    assert client.get('/health').json()['version'] == '2.4.0'
    assert client.post('/v1/research/packet-schedule',json={**data,'optimizer':'wrong'}).status_code == 422
    legacy = client.post('/v1/research/packet-schedule',json={**data,'optimizer':'legacy'})
    assert legacy.status_code == 200
    assert legacy.json()['finite_optimum_evidence'] is None


def test_api_resource_fail_closed(tmp_path):
    app.state.audit=AuditStore(tmp_path/'v18_budget.sqlite3')
    client=TestClient(app)
    # This surface rejects oversized inputs instead of pretending a certificate exists.
    payload={'n':16,'clauses':[[i] for i in range(1,17)],'cross_check':False,'optimizer':'exact_dp'}
    result=client.post('/v1/research/packet-schedule',json=payload)
    assert result.status_code==200,result.text
    assert result.json()['status']=='SCHEDULE'


def test_exact_dp_strictly_beats_local_swaps_on_fixed_twelve_wire_case():
    # Fixed network: every wire occurs in exactly two tensors.
    from veritas.research.tensor import TensorNetwork, Factor
    port_lists = (
        (0, 4, 5, 9), (2,), (3, 7, 11), (10,),
        (1, 2, 5), (1, 10), (6, 7, 8, 11), (0, 3, 4, 6, 8, 9),
    )
    net = TensorNetwork(12, tuple(Factor(ports,(1,)*(1<<len(ports)),f'factor:{i}')
                                      for i,ports in enumerate(port_lists)))
    legacy = plan_packets(net,packet_size=4,timeout_s=5)
    exact,proof = optimize_packets_exact(net,packet_size=4)
    assert (legacy.optimized_collisions,legacy.optimized_max_incidence)==(6,2)
    assert (exact.optimized_collisions,exact.optimized_max_incidence)==(5,2)
    assert proof.independent_score_replayed
    assert eliminate(net)==eliminate(relabel_network(net,exact.wire_order))
