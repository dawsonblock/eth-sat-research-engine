"""Independent exhaustive oracle for generic recursive exact contraction."""
import random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract, Factor, TensorNetwork
from veritas.research.recursive_separator import (
    recursive_contract, separator_plan, ResourceLimit, edge_owners,
)


def test_edge_cases():
    for n,clauses in [(0,[]),(1,[]),(3,[]),(1,[[1]]),(1,[[1],[-1]]),
                      (3,[[1,-2],[-1,3]]),(3,[[]])]:
        net=from_cnf(CNF.from_lists(n,clauses))
        want=brute_contract(net)
        for leaf in (1,2,3):
            got,stats=recursive_contract(net,leaf_factors=leaf)
            assert got==want
            assert stats.calls>0


def test_randomized_exact_and_modular():
    rng=random.Random(20261029)
    for _ in range(270):
        n=rng.randrange(0,6)
        m=rng.randrange(0,5)
        clauses=[]
        for _ in range(m):
            width=rng.randrange(0,min(3,n)+1)
            variables=rng.sample(range(1,n+1),width)
            clauses.append([v if rng.choice((True,False)) else -v for v in variables])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>11:continue
        expect=brute_contract(net)
        for leaf in (2,3):
            value,stats=recursive_contract(net,leaf_factors=leaf,max_cut_edges=10)
            assert value==expect,(n,clauses,value,expect)
            assert 0<=stats.max_depth<=6
        bits=rng.randrange(1,11)
        value,_=recursive_contract(net,modulus=1<<bits)
        assert value==expect%(1<<bits)


def test_simple_plan_and_collision_accounting():
    net=from_cnf(CNF.from_lists(3,[[1,2],[-2,3]]))
    plan=separator_plan(net)
    assert len(plan.left)+len(plan.right)==len(net.factors)
    assert not (set(plan.left)&set(plan.right))
    assert set(plan.left)|set(plan.right)==set(range(len(net.factors)))
    owners=edge_owners(net)
    assert set(plan.cut_edges)=={e for e,(a,b) in enumerate(owners)
        if (a in plan.left)!=(b in plan.left)}


def test_time_resource_and_malformed_boundaries():
    net=from_cnf(CNF.from_lists(4,[[1,2,3],[-1,-2,-3]]))
    with pytest.raises(ResourceLimit):
        recursive_contract(net,leaf_factors=1,max_cut_edges=0)
    with pytest.raises(ValueError):
        recursive_contract(net,leaf_factors=0)
    with pytest.raises(ValueError):
        recursive_contract(net,modulus=1)
    # A self-loop in the factory model is invalid for this bipartite split.
    loop=TensorNetwork(1,(Factor((0,),(1,1),'loop'),Factor((0,),(1,1),'second')))
    assert recursive_contract(loop)[0]==2
