import random
import sys

from veritas.core.cnf import CNF
from veritas.solvers.reference import exhaustive_count, solve


def test_cnf_snapshots_mutable_input():
    original = [[1], [-1, 2]]
    cnf = CNF(2, original)
    digest = cnf.digest()
    original[0][0] = -1
    original.append([])
    assert cnf.clauses == ((1,), (-1, 2))
    assert cnf.digest() == digest
    assert solve(cnf, count=True).count == 1


def test_large_tautology_count_and_unused_variables():
    cnf = CNF.from_lists(512, [[i, -i] for i in range(1, 513)])
    result = solve(cnf, count=True, timeout_s=10)
    assert result.status == 'COUNT'
    assert result.count == 1 << 512


def test_deep_sat_search_does_not_use_python_recursion():
    cnf = CNF.from_lists(256, [[i, i+1] for i in range(1, 256, 2)])
    original_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(100)
        result = solve(cnf, timeout_s=10)
    finally:
        sys.setrecursionlimit(original_limit)
    assert result.status == 'SAT'
    assert cnf.evaluate(result.model)


def test_budget_failure_never_exposes_partial_count():
    cnf = CNF.from_lists(40, [[i, i+1] for i in range(1, 40, 2)])
    result = solve(cnf, count=True, max_nodes=20)
    assert result.status == 'UNKNOWN'
    assert result.count is None


def test_seeded_counting_differential_with_duplicates_and_tautologies():
    rng = random.Random(82506)
    for _ in range(300):
        n = rng.randrange(1, 8)
        clauses = [[rng.choice((-1, 1)) * rng.randint(1, n)
                    for _ in range(rng.randrange(5))]
                   for _ in range(rng.randrange(9))]
        cnf = CNF.from_lists(n, clauses)
        count = solve(cnf, count=True, timeout_s=10)
        assert count.status == 'COUNT'
        assert count.count == exhaustive_count(cnf)
        sat = solve(cnf, timeout_s=10)
        assert (sat.status == 'SAT') == (count.count > 0)
        if sat.model is not None:
            assert cnf.evaluate(sat.model)
