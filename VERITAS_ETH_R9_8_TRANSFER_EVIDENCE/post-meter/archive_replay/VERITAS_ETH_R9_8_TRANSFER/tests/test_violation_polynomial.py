import random
import pytest
from veritas.core.cnf import CNF
from veritas.research.violation_polynomial import (
    evaluate_polynomial, recover_zero_from_positive_nodes, multiply_polynomials, PolynomialStats,
    eliminate_violation_polynomial, exact_violation_histogram)


def test_histogram_cases():
    for cnf in [CNF.from_lists(0,[]), CNF.from_lists(0,[[]]),
                CNF.from_lists(3,[]), CNF.from_lists(3,[[]]),
                CNF.from_lists(3,[[1],[-1]]), CNF.from_lists(3,[[1,-1],[2,3]]),
                CNF.from_lists(3,[[1,1],[-2,2],[-3]])]:
        coeffs, _ = eliminate_violation_polynomial(cnf)
        assert coeffs == exact_violation_histogram(cnf)
        assert sum(coeffs) == 1 << cnf.n
        assert coeffs[0] == exact_violation_histogram(cnf)[0]
        assert evaluate_polynomial(coeffs,1) == 1 << cnf.n


def test_random_histograms_and_modular_lifting():
    rng = random.Random(90017)
    for _ in range(300):
        n = rng.randint(0,5)
        clauses = [[rng.choice((-1,1))*rng.randint(1,n) for _ in range(rng.randint(0,3))] if n else []
                   for _ in range(rng.randint(0,5))]
        cnf = CNF.from_lists(n,clauses)
        exact, _ = eliminate_violation_polynomial(cnf)
        assert exact == exact_violation_histogram(cnf)
        for precision in [1,2,4, n+1]:
            residues, _ = eliminate_violation_polynomial(cnf,precision_bits=precision)
            assert residues == [c % (1<<precision) for c in exact]
            for t in [-2,-1,0,1,3]:
                assert evaluate_polynomial(residues,t,precision) == evaluate_polynomial(exact,t) % (1<<precision)


def test_v2_safe_omission():
    stats = PolynomialStats()
    assert multiply_polynomials((8,2,0),(4,3,0),precision_bits=4,stats=stats) == (0,0,6)
    assert stats.v2_zero_pairs_elided == 1


def test_limits():
    with pytest.raises(ValueError):
        eliminate_violation_polynomial(CNF.from_lists(1,[[1]]), precision_bits=0)
    with pytest.raises(ValueError):
        eliminate_violation_polynomial(CNF.from_lists(1,[[1]]), max_edges=0)
    with pytest.raises(ValueError):
        eliminate_violation_polynomial(CNF.from_lists(2,[[1,2]]),max_table_entries=1)


def test_exact_nonzero_interpolation():
    for poly in [(7,), (2,3), (0,1,2), (5,-4,3,-1), (100,0,0,0,0)]:
        nodes=[evaluate_polynomial(poly,x) for x in range(1,len(poly)+1)]
        assert recover_zero_from_positive_nodes(nodes)==poly[0]
        for p in [1,2,4,7]:
            assert recover_zero_from_positive_nodes(nodes,p)==poly[0]%(1<<p)
    with pytest.raises(ValueError):
        recover_zero_from_positive_nodes([])
