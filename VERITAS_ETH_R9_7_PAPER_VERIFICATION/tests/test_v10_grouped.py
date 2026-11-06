"""Exact rational low-rank coefficient reconstruction and jet differential tests."""
from fractions import Fraction
from random import Random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.grouped_cauchy import (
    group_cauchy_modes, grouped_cauchy_jet_mod, _outer_modes,
)
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod


def test_rank_decomposition_adversarial():
    for mat in (
        ((Fraction(0),Fraction(0)),(Fraction(0),Fraction(0))),
        ((Fraction(1),Fraction(2)),(Fraction(2),Fraction(4))),
        ((Fraction(1),Fraction(2)),(Fraction(3),Fraction(4))),
        ((Fraction(0),Fraction(2),Fraction(0)),(Fraction(0),Fraction(0),Fraction(0))),
    ):
        terms=_outer_modes(mat)
        assert len(terms)<=min(len(mat),len(mat[0]))
        for i in range(len(mat)):
            for j in range(len(mat[0])):
                assert sum((u[i]*v[j] for u,v in terms),Fraction(0))==mat[i][j]


def test_grouped_nodes_and_all_spans():
    for size in (1,2,4):
        for edges in range(0,min(6,2*size)+1):
            for t in range(-size,size):
                for span in range(1,size+1):
                    kernel,modes,summary=group_cauchy_modes(edges=edges,packet_size=size,
                          node=t,jet_order=4,group_span=span)
                    assert len(kernel)==edges
                    assert summary.zero_constant_cross_checked
                    for m in modes: assert m.coefficient_degree>=1


def test_cauchy_randomized_differential():
    rng=Random(11029)
    for _ in range(125):
        n=rng.randrange(0,5)
        clauses=[]
        for _ in range(rng.randrange(0,4)):
            if not n:break
            width=rng.randrange(0,min(2,n)+1)
            choices=rng.sample(range(1,n+1),width)
            clauses.append([x if rng.randrange(2) else -x for x in choices])
        net=from_cnf(CNF.from_lists(n,clauses))
        if net.edges>5:continue
        size=rng.choice((1,2,4))
        t=rng.randrange(-size,size)
        order=rng.randrange(1,6)
        span=rng.randrange(1,size+1)
        jet,modes,summary=grouped_cauchy_jet_mod(net,packet_size=size,node=t,
                     group_span=span,precision_bits=8,jet_order=order)
        reference,_=shifted_cauchy_jet_mod(net,packet_size=size,node=t,
                      precision_bits=8,jet_order=order,max_edges=6)
        assert jet==reference,(n,clauses,size,t,span,jet,reference)


def test_reject_bad_values():
    with pytest.raises(ValueError):group_cauchy_modes(edges=9)
    with pytest.raises(ValueError):group_cauchy_modes(edges=2,group_span=3)
    with pytest.raises(ValueError):group_cauchy_modes(edges=2,node=2)
