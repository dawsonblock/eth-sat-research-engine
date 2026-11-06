import random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.cauchy_modes import cauchy_modes_at_node
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod


@pytest.mark.parametrize('clauses', [[],[[]],[[1]], [[1,2]],[[1],[2]],[[1],[-1]],[[1,2],[-2]]])
@pytest.mark.parametrize('L,node', [(1,-1),(1,0),(2,-2),(2,-1),(2,0),(2,1),(4,-4),(4,1)])
def test_modes_equal_independent_full_local_jet(clauses,L,node):
    n=max([2]+[abs(x) for c in clauses for x in c])
    network=from_cnf(CNF.from_lists(n,clauses))
    result,modes,stats=cauchy_modes_at_node(network,packet_size=L,node=node,
                           precision_bits=10,jet_order=6)
    oracle,_=shifted_cauchy_jet_mod(network,packet_size=L,node=node,
                          precision_bits=10,jet_order=6)
    assert result==oracle
    assert all(m.row!=m.column or m.source_group!=m.target_group for m in modes)
    assert all(m.min_z_degree is None or m.min_z_degree>=1 for m in modes)
    assert all(m.min_valuation is None or m.min_valuation>=0 for m in modes)
    assert stats.available_cross_modes==len(modes)


def test_small_randomized_modes_precision_and_pruning():
    rng=random.Random(83919)
    pruned=0
    for trial in range(95):
        n=rng.randrange(1,5)
        m=rng.randrange(0,4)
        clauses=[]
        for _ in range(m):
            length=rng.randrange(0,3)
            clauses.append([rng.choice((-1,1))*rng.randrange(1,n+1) for _ in range(length)])
        if sum(map(len,clauses))>5:continue
        net=from_cnf(CNF.from_lists(n,clauses))
        L=rng.choice((1,2,4))
        t=rng.randrange(-L,L)
        bits=rng.randrange(1,13)
        order=rng.randrange(1,9)
        result,_,stats=cauchy_modes_at_node(net,packet_size=L,node=t,precision_bits=bits,jet_order=order)
        oracle,_=shifted_cauchy_jet_mod(net,packet_size=L,node=t,precision_bits=bits,jet_order=order)
        assert result==oracle, (clauses,L,t,bits,order,result,oracle)
        pruned+=stats.dropped_by_valuation+stats.dropped_by_z_degree
    assert pruned>0


def test_modes_reject_bad_limits():
    net=from_cnf(CNF.from_lists(1,[[1]]))
    for bad in (0,3,16):
        with pytest.raises(ValueError): cauchy_modes_at_node(net,packet_size=bad)
    with pytest.raises(ValueError): cauchy_modes_at_node(net,node=2)
    with pytest.raises(ValueError): cauchy_modes_at_node(net,precision_bits=0)
