"""Differential exact modular Cauchy jet contraction tests."""
from random import Random
from pytest import raises
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
from veritas.research.cauchy_elimination import eliminate_cauchy_jet,EliminationLimit
from veritas.research.packet_schedule import relabel_network


def test_randomized_all_nodes_orders_permutations():
    rng=Random(202611)
    count=0
    for _ in range(100):
        n=rng.randrange(0,5)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            if n==0:break
            chosen=rng.sample(range(1,n+1),rng.randrange(0,min(3,n)+1))
            clauses.append([x if rng.randrange(2) else -x for x in chosen])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>5:continue
        size=rng.choice((1,2,4))
        node=rng.randrange(-size,size)
        bits=rng.randrange(1,17)
        order=rng.randrange(1,7)
        optimize=bool(rng.randrange(2))
        method=rng.choice(('min_fill','natural'))
        result,stats=eliminate_cauchy_jet(net,packet_size=size,node=node,
             precision_bits=bits,jet_order=order,optimize_packets=optimize,elimination_order=method,
             timeout_s=5)
        original=relabel_network(net,stats.packet_schedule.wire_order) if stats.packet_schedule else net
        oracle,_=shifted_cauchy_jet_mod(original,packet_size=size,node=node,
                     precision_bits=bits,jet_order=order,max_edges=6)
        assert result==oracle, (clauses,size,node,method,result,oracle)
        assert stats.eliminated_variables==2*net.edges
        assert stats.maximum_width<=2*net.edges
        count+=1
    assert count>=45


def test_constant_term_equals_count_for_all_packets():
    for n,clauses in [(0,[]),(4,[]),(2,[[1,2]]),(3,[[1,-2],[2,3]]),(2,[[1],[-1]]),(2,[[],[1]])]:
        net=from_cnf(CNF.from_lists(n,clauses))
        for size in (1,2,4,8):
            residue,stats=eliminate_cauchy_jet(net,packet_size=size,node=0,
                         precision_bits=12,jet_order=4)
            assert residue[0]==brute_contract(net,max_edges=6)%(1<<12)


def test_fail_closed_caps_and_invalid_inputs():
    net=from_cnf(CNF.from_lists(3,[[1,2],[-2,3]]))
    with raises(EliminationLimit):
        eliminate_cauchy_jet(net,packet_size=4,max_table_entries=2,max_total_entries=256)
    with raises(ValueError):
        eliminate_cauchy_jet(net,precision_bits=0)
    with raises(ValueError):
        eliminate_cauchy_jet(net,packet_size=3)
    with raises(ValueError):
        eliminate_cauchy_jet(net,node=9)
    with raises(ValueError):
        eliminate_cauchy_jet(net,elimination_order='fastest')
