from veritas.core.cnf import CNF
from veritas.research.residual_equivalence import (
    count_with_residual_memo,
    prefix_residual_table,
    residual_after_assignment,
)
from veritas.solvers.reference import exhaustive_count


def test_block_example_prefix_buckets():
    # F = (x∨z) ∧ (y∨z) with (x,y,z) = (1,2,3)
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    buckets = prefix_residual_table(cnf, (1, 2))
    assert sum(b['multiplicity'] for b in buckets) == 4
    # Three (x,y) pairs share the same unit-z residual; (1,1) leaves z free.
    assert len(buckets) == 2
    mults = sorted(b['multiplicity'] for b in buckets)
    assert mults == [1, 3]


def test_block_example_count_five():
    cnf = CNF.from_lists(3, [[1, 3], [2, 3]])
    count, stats, _ = count_with_residual_memo(cnf, preprocess=False)
    assert count == exhaustive_count(cnf) == 5
    assert stats.distinct_residual_states >= 2


def test_residual_memo_matches_exhaustive_random():
    cnf = CNF.from_lists(4, [[1, 2], [2, 3], [3, 4]])
    got, _, _ = count_with_residual_memo(cnf, preprocess=True)
    assert got == exhaustive_count(cnf)
