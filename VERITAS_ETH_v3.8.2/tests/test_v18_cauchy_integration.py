"""Exact subset-packet planning integrated with the bounded Cauchy backend."""
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.cauchy_elimination import eliminate_cauchy_jet
from veritas.research.cauchy_deformation import shifted_cauchy_jet_mod
from veritas.research.packet_schedule import relabel_network


def test_cauchy_exact_packet_plan_independent_jet_oracle():
    net=from_cnf(CNF.from_lists(3,[[1,2],[-1,3]]))
    for node in (-1,0,1):
        coeffs,stats=eliminate_cauchy_jet(net,packet_size=2,node=node,
            precision_bits=8,jet_order=3,optimize_packets=True,
            packet_optimizer='exact_dp',timeout_s=10)
        assert stats.packet_schedule.exact_optimum
        reordered=relabel_network(net,stats.packet_schedule.wire_order)
        oracle,_=shifted_cauchy_jet_mod(reordered,packet_size=2,node=node,
            precision_bits=8,jet_order=3,max_edges=4,timeout_s=10)
        assert coeffs==oracle


def test_cauchy_packet_optimizer_rejects_invalid():
    net=from_cnf(CNF.from_lists(1,[[1]]))
    with pytest.raises(ValueError):
        eliminate_cauchy_jet(net,optimize_packets=True,packet_optimizer='wrong')
