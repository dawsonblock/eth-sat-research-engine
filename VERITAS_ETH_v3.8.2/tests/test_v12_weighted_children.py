"""Independent differential tests of exact polynomial child tensor contraction."""
from random import Random
from dataclasses import asdict
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
from veritas.research.weighted_children import (
    ChildTensorLimit, reconstruct_weighted_kernel, recursive_weighted_jet,
)


def test_constant_network_no_factors():
    net=from_cnf(CNF.from_lists(0,[]))
    jet, modes, st=recursive_weighted_jet(net)
    assert jet==(1,0,0,0,0) and not modes
    assert st.recursion_calls==0


def test_weighted_mode_pruning_exact():
    for L in (1,2,4):
        for t in range(-L,L):
            for p in (1,2,3,7,12):
                matrix,modes=reconstruct_weighted_kernel(edges=min(5,L*2),packet_size=L,
                              node=t,group_span=1,precision_bits=p,jet_order=6)
                assert all(len(row)==min(5,L*2) for row in matrix)
                assert all(m.degree>=1 for m in modes)
                assert all(m.v2_lower_bound>=p for m in modes if m.discarded_mod_precision)
    _,modes=reconstruct_weighted_kernel(edges=4,packet_size=2,node=-2,
                                       group_span=1,precision_bits=2,jet_order=7)
    assert any(m.discarded_mod_precision for m in modes)


def test_exact_recursion_vs_exhaustive_randomized():
    rng=Random(121314)
    checked=0
    for trial in range(160):
        n=rng.randrange(0,5)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            if n==0:break
            width=rng.randrange(0,min(n,3)+1)
            chosen=rng.sample(range(1,n+1),width)
            clauses.append([v if rng.randrange(2) else -v for v in chosen])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>6:continue
        L=rng.choice((1,2,4))
        t=rng.randrange(-L,L)
        p=rng.choice((1,2,4,8,12))
        q=rng.randrange(1,7)
        span=rng.randrange(1,L+1)
        jet,modes,stats=recursive_weighted_jet(net,packet_size=L,node=t,
                            group_span=span,precision_bits=p,jet_order=q,timeout_s=8)
        oracle,_=shifted_cauchy_jet_mod(net,packet_size=L,node=t,
                            precision_bits=p,jet_order=q,max_edges=6,timeout_s=8)
        assert jet==oracle,(trial,n,clauses,L,t,p,q,span,jet,oracle)
        assert stats.raw_rank_one_modes==len(modes)
        assert stats.kept_rank_one_modes+stats.dropped_rank_one_modes==len(modes)
        checked+=1
    assert checked>=90, checked


def test_budgets_fail_closed_and_bad_input():
    net=from_cnf(CNF.from_lists(3,[[1,2],[-2,3]]))
    with pytest.raises(ChildTensorLimit):
        recursive_weighted_jet(net,max_work_assignments=1)
    with pytest.raises(ChildTensorLimit):
        recursive_weighted_jet(net,max_boundary_vars=0)
    with pytest.raises(ChildTensorLimit):
        recursive_weighted_jet(net,max_table_entries=1)
    with pytest.raises(ValueError):
        recursive_weighted_jet(net,jet_order=0)
    with pytest.raises(ValueError):
        recursive_weighted_jet(net,node=2)
    with pytest.raises(ValueError):
        recursive_weighted_jet(net,precision_bits=True)
    with pytest.raises(ValueError):
        recursive_weighted_jet(net,max_edges=1)
