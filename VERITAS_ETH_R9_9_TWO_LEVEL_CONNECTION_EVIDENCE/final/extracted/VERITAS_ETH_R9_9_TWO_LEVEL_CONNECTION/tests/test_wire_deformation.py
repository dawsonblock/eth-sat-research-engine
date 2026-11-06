"""Differential, metamorphic, adversarial and resource-budget tests for v0.7."""
import random
import pytest
from veritas.core.cnf import CNF
from veritas.research.tensor import TensorNetwork, Factor, from_cnf, eliminate
from veritas.solvers.reference import exhaustive_count
from veritas.research.violation_polynomial import evaluate_polynomial, recover_zero_from_positive_nodes
from veritas.research.wire_deformation import (
    deform_polynomial, independent_defect_histogram, check_deformation_invariants,
    factorized_evaluation,
)


def _check(cnf):
    network = from_cnf(cnf, max_degree=14)
    poly, stats = deform_polynomial(network, max_edges=10)
    oracle = independent_defect_histogram(network, max_edges=7)
    assert poly == oracle
    assert poly[0] == exhaustive_count(cnf, max_vars=10)
    assert poly[0] == eliminate(network)
    assert check_deformation_invariants(network, poly)['rank_one_nodes_checked']
    assert recover_zero_from_positive_nodes([evaluate_polynomial(poly,t) for t in range(1,len(poly)+1)]) == poly[0]
    assert stats.eliminated_half_edges == 2*network.edges
    for p in (1, 2, 4, 8):
        mod, mstats = deform_polynomial(network, precision_bits=p, max_edges=10)
        assert mod == [v % (1 << p) for v in poly]
        assert check_deformation_invariants(network, mod, precision_bits=p)['rank_one_nodes_checked']
    return poly


def test_special_inputs():
    for n, clauses in [
        (0, []), (0, [[]]), (1, []), (3, []), (1, [[1]]), (1, [[1], [-1]]),
        (3, [[1, -1]]), (2, [[1, 2],[-2]]), (3, [[1,1,1]]),
        (3, [[1,-1],[2,-2]]), (4, [[], [1,2],[-1,3]]),
    ]:
        _check(CNF.from_lists(n,clauses))


def test_seeded_random_networks():
    rng = random.Random(7070)
    for _ in range(140):
        n = rng.randrange(0,5)
        clauses=[]
        for _ in range(rng.randrange(0,5)):
            clause=[rng.choice([-1,1])*rng.randint(1,n) for _ in range(rng.randrange(0,4))] if n else []
            clauses.append(clause)
        if sum(map(len,clauses)) > 6:
            continue
        _check(CNF.from_lists(n,clauses))


def test_signed_tensors_independent_of_cnf():
    nw = TensorNetwork(1, (
        Factor((0,), (-5,7), 'left'),
        Factor((0,), (3,-11), 'right'),
        Factor((), (-2,), 'scalar'),
    ))
    poly, _ = deform_polynomial(nw)
    assert poly == independent_defect_histogram(nw)
    assert poly[0] == eliminate(nw)
    assert check_deformation_invariants(nw,poly)['rank_one_nodes_checked']
    assert factorized_evaluation(nw,1) == sum(poly)
    assert factorized_evaluation(nw,-1) == evaluate_polynomial(poly,-1)


def test_invalid_limits_and_corrupt_invariants():
    nw=from_cnf(CNF.from_lists(2, [[1,2]]))
    with pytest.raises(ValueError):
        deform_polynomial(nw, max_edges=1)
    with pytest.raises(ValueError):
        deform_polynomial(nw, precision_bits=0)
    with pytest.raises(ValueError):
        deform_polynomial(nw, max_table_entries=1)
    with pytest.raises(ValueError):
        independent_defect_histogram(nw,max_edges=1)
    with pytest.raises(ValueError):
        factorized_evaluation(nw,0)
    poly,_=deform_polynomial(nw)
    bad=poly.copy()
    bad[-1]+=1
    with pytest.raises(AssertionError):
        check_deformation_invariants(nw,bad)
    with pytest.raises(ValueError):
        check_deformation_invariants(nw,poly[:-1])


def test_matrix_deterministic_reproducibility():
    network = from_cnf(CNF.from_lists(3,[[1,2],[-2,3],[-1,-3]]))
    a,sa=deform_polynomial(network)
    b,sb=deform_polynomial(network)
    assert a==b and sa==sb
