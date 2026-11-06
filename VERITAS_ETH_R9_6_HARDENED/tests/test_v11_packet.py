"""Independent packet optimizer checks: exhaustive finite search + count invariance."""
from itertools import permutations
from random import Random
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf,brute_contract,eliminate
from veritas.research.packet_schedule import collision_score,plan_packets,relabel_network


def test_small_exhaustive_optimum_and_relabel_count():
    rng=Random(111104)
    tested=0
    for trial in range(60):
        n=rng.randrange(0,5)
        clauses=[]
        for _ in range(rng.randrange(0,4)):
            if n==0: break
            chosen=rng.sample(range(1,n+1),rng.randrange(0,min(3,n)+1))
            clauses.append([x if rng.randrange(2) else -x for x in chosen])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>6: continue
        size=rng.choice((1,2,4))
        plan=plan_packets(net,packet_size=size,timeout_s=4)
        assert plan.exact_optimum
        full=min((collision_score(net,order,size),order) for order in permutations(range(net.edges)))
        assert (plan.optimized_collisions,plan.optimized_max_incidence,plan.wire_order)==(full[0][0],full[0][1],full[1])
        other=relabel_network(net,plan.wire_order)
        assert brute_contract(net,max_edges=6)==eliminate(other)
        assert plan.optimized_collisions<=plan.original_collisions
        tested+=1
    assert tested>=25


def test_schedule_rejects_malformed_order_and_limits():
    import pytest
    net=from_cnf(CNF.from_lists(3,[[1,2]]))
    for order in ((0,0),(0,),(-1,1)):
        with pytest.raises(ValueError):relabel_network(net,order)
    with pytest.raises(ValueError):plan_packets(net,packet_size=3)
    with pytest.raises(ValueError):plan_packets(net,max_permutations=0)
    with pytest.raises(ValueError):plan_packets(net,timeout_s=0)
    partial=plan_packets(net,packet_size=2,max_permutations=1)
    assert not partial.exact_optimum
