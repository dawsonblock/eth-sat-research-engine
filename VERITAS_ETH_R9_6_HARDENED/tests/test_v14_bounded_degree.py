"""Property, differential, adversarial and timeout tests for COPY3 gadgets."""
import random
from dataclasses import asdict
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf, brute_contract, eliminate
from veritas.research.bounded_degree import bounded_degree_from_cnf, describe_network
from veritas.research.minfill_contract import minfill_contract, ContractionBudgetExceeded
from veritas.solvers.reference import exhaustive_count


def test_bijection_edge_cases():
    for cnf in [CNF.from_lists(0,[]),CNF.from_lists(3,[]),CNF.from_lists(3,[[]]),
                CNF.from_lists(2,[[1,-1]]),CNF.from_lists(3,[[1,1,1],[-2,3]]),
                CNF.from_lists(1,[[1],[-1]]),CNF.from_lists(2,[[1],[1],[1],[1],[1]])]:
        net, stats=bounded_degree_from_cnf(cnf)
        expected=exhaustive_count(cnf)
        assert stats.maximum_factor_degree<=max(3,max(map(len,cnf.clauses),default=0))
        assert stats.resulting_wires==stats.original_occurrence_wires+stats.auxiliary_wires
        assert minfill_contract(net)[0]==expected
        assert minfill_contract(net,modulus=1<<(cnf.n+1))[0]==expected
        if net.edges <=15:
            assert brute_contract(net)==expected


def test_high_occurrence_beyond_dense_limit():
    cnf=CNF.from_lists(2, [[1] for _ in range(21)]+[[-2]])
    with pytest.raises(ValueError,match='too many occurrences'):
        from_cnf(cnf,max_degree=15)
    net,stats=bounded_degree_from_cnf(cnf,max_clause_width=1)
    assert stats.maximum_variable_occurrences==21
    assert stats.maximum_factor_degree==3
    assert stats.auxiliary_wires==18
    count,trace=minfill_contract(net,timeout_s=15)
    assert count==1
    assert trace.eliminated_wires==net.edges
    assert trace.max_join_width<=8


def test_random_count_equivalence_250_cases():
    rng=random.Random(140026)
    for t in range(250):
        n=rng.randrange(0,6)
        clauses=[]
        for _ in range(rng.randrange(0,9)):
            width=rng.randrange(0,4) if n else 0
            clauses.append([rng.choice((-1,1))*rng.randrange(1,n+1) for _ in range(width)])
        cnf=CNF.from_lists(n,clauses)
        network,stats=bounded_degree_from_cnf(cnf,max_clause_width=3)
        assert all(len(f.ports)<=3 for f in network.factors)
        assert all(sum(edge in f.ports for f in network.factors)==2 for edge in range(network.edges))
        oracle=exhaustive_count(cnf)
        got,trace=minfill_contract(network,modulus=None,max_table_entries=4096)
        assert got==oracle,(t,cnf,stats,trace)
        modulus = 2**rng.randrange(1,10)
        got_mod,_=minfill_contract(network,modulus=modulus)
        assert got_mod==oracle%modulus


def test_moduli_random_75():
    rng=random.Random(145334)
    for _ in range(75):
        n=rng.randrange(0,5)
        clauses=[[rng.choice((-1,1))*rng.randrange(1,n+1) for _ in range(rng.randrange(0,4))]
                 for j in range(rng.randrange(0,5))] if n else [[]]
        cnf=CNF.from_lists(n,clauses)
        net,_=bounded_degree_from_cnf(cnf)
        mod=1<<rng.randrange(1,11)
        assert minfill_contract(net,modulus=mod)[0]==exhaustive_count(cnf)%mod


def test_fail_closed_caps():
    cnf=CNF.from_lists(1,[[1]]*9)
    for kw in ({'max_clause_width':0},{'max_wires':10},{'max_factors':9}):
        with pytest.raises(ValueError):bounded_degree_from_cnf(cnf,**kw)
    net,_=bounded_degree_from_cnf(cnf)
    with pytest.raises(ContractionBudgetExceeded):minfill_contract(net,max_work_assignments=1)
    with pytest.raises(ValueError):minfill_contract(net,modulus=1)
    with pytest.raises(ValueError):minfill_contract(net,modulus=True)
    with pytest.raises(ValueError):minfill_contract(net,max_table_entries=0)
    with pytest.raises(ValueError):bounded_degree_from_cnf(cnf,max_wires=True)
    assert describe_network(cnf)['count_preservation']=='MATHEMATICAL_BIJECTION'
