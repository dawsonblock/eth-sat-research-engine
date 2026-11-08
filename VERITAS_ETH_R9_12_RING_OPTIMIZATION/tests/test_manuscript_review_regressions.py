"""Independent finite regressions for the November 6 manuscript review.

Small, scaled fixtures exercise construction identities, not the paper's
asymptotic theorem. All mathematical claims and source qualifications stay off.
"""
from itertools import product

import pytest

from veritas.research.manuscript import cnf, hashes, sparsify
from veritas.research.manuscript.resources import Budget, Limits, ResourceLimit


@pytest.mark.parametrize('m', [1, 2, 3, 4, 7, 8, 9, 16, 31, 32, 33])
def test_hash_parameters_match_strict_power_bound(m):
    mu, p, d = hashes.sparse_check_parameters(m, 2, max(1, m))
    assert 2 ** (mu - 1) <= m < 2 ** mu
    assert p == 20000 * 4 * mu ** 2
    assert d == 320000 * 4 * mu ** 3


def test_local_code_uses_vector_syndrome_not_xor_of_rows():
    rows = hashes._local_code(2, 3, 1, 1, Budget(Limits(max_work=20000)))
    assert len(rows) == 2
    rejected_by_both = False
    for word in range(1, 8):
        if word.bit_count() < 3:
            syndrome = tuple((word & row).bit_count() % 2 for row in rows)
            assert any(syndrome), (word, rows)
            rejected_by_both |= syndrome == (1, 1)
    # This valid syndrome is precisely what an XOR aggregation loses.
    assert rejected_by_both


def test_local_code_checks_budget_during_fixed_weight_enumeration():
    budget = Budget(Limits(max_work=10, max_seconds=2))
    with pytest.raises(ResourceLimit):
        hashes._local_code(2, 40, 1, 20, budget)
    assert budget.work > 10


def test_walsh_condition_does_not_round_fractional_bound_up():
    # An odd number of signs has absolute sum at least one, not <= 3/5.
    assert hashes._biased_shifts(3, 1, 1, 5, Budget()) is None


def test_balanced_shifts_satisfy_every_nonzero_character():
    shifts = hashes._biased_shifts(4, 2, 1, 8, Budget())
    assert shifts is not None
    assert len(shifts) == 4
    for character in (1, 2, 3):
        walsh = sum((-1) ** ((character & shift).bit_count() % 2)
                    for shift in shifts)
        assert abs(walsh) * 8 <= 4


def _sat(clauses, bits):
    return all(any(bits[abs(literal)-1] == (literal > 0)
                   for literal in clause) for clause in clauses)


def test_mixed_width_branch_retains_unselected_clause():
    formula = frozenset(map(frozenset, [(1, 2), (1, 3), (1, 4, 5)]))
    assert sparsify._find_violation(formula, 2, Budget()) == (2, frozenset({1}))
    a, b = sparsify._children(formula, 2, frozenset({1}), Budget())
    # The width-three clause is not a selected petal; preserve it in G.
    assert frozenset({1, 4, 5}) in b
    assert frozenset({4, 5}) not in b
    for bits in product((False, True), repeat=5):
        assert int(_sat(a, bits)) + int(_sat(b, bits)) == int(_sat(formula, bits))


@pytest.mark.parametrize('clauses', [
    [(1, 2), (1, 3), (1, 4)],
    [(1, 2), (1, -2), (-1, 3), (-1, -3)],
    [(1, 2), (1, 3), (1, 4, 5), (-2, -3, 5)],
    [(1, 2, 3), (1, 2, 4), (-1, 3, 5), (-1, 4, 5)],
    [(), (1, 2), (1, 3)],
    [],
])
def test_scaled_sparsification_exact_partition(monkeypatch, clauses):
    # M=2 is deliberately a finite branching fixture, not a sigma certificate.
    monkeypatch.setattr(sparsify, 'select_M', lambda *args, **kwargs: 2)
    leaves = list(sparsify.sparsification_leaves(clauses, 3, 1, 2))
    for bits in product((False, True), repeat=5):
        assert sum(_sat(leaf, bits) for leaf in leaves) == int(_sat(clauses, bits))


def test_leaf_stream_does_not_visit_future_leaves_early(monkeypatch):
    monkeypatch.setattr(sparsify, 'select_M', lambda *args, **kwargs: 2)
    original = sparsify._find_violation
    visited = []

    def observe(*args):
        visited.append(args[0])
        return original(*args)

    monkeypatch.setattr(sparsify, '_find_violation', observe)
    stream = sparsify.sparsification_leaves([(1, 2), (1, 3), (1, 4)], 2, 1, 2)
    assert iter(stream) is stream
    assert visited == []
    first = next(stream)
    before = len(visited)
    rest = list(stream)
    assert first is not None and rest
    assert len(visited) > before


def test_arbitrary_density_n20_uses_quantitative_sigma(monkeypatch):
    captured = []

    def stop_at_sparsification(*args, **kwargs):
        captured.append((args[2], args[3]))
        raise ResourceLimit('independent dispatcher sentinel')

    monkeypatch.setattr(sparsify, 'sparsification_leaves', stop_at_sparsification)
    result = cnf.count(cnf.Formula(20, ((1, 2), (3, -4))))
    assert captured == [(1, 3)]  # ceil(sqrt(ceil(log2(20)))) == 3
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'count' not in result


@pytest.mark.parametrize('m', [5, 7, 9])
def test_tanner_shortening_matches_independent_vertex_syndromes(monkeypatch, m):
    # Scale graph dimensions only to test addressing, not the existence theorem.
    d = 4
    q = 1 << ((m-1)//d).bit_length()
    local = (0b1011,)
    shifts = tuple(j % q for j in range(d))
    monkeypatch.setattr(hashes, 'sparse_check_parameters', lambda *args: (1, 2, d))
    monkeypatch.setattr(hashes, '_local_code', lambda *args: local)
    monkeypatch.setattr(hashes, '_biased_shifts', lambda *args: shifts)
    rows = hashes.sparse_checks(m, [(1,)] * m, 1)
    assert len(rows) == 2*q
    assert all(row.bit_length() <= m for row in rows)
    for word in range(1 << m):
        expected = []
        for side in ('left', 'right'):
            for vertex in range(q):
                parity = 0
                for edge in range(m):
                    u, port = divmod(edge, d)
                    endpoint = u if side == 'left' else u ^ shifts[port]
                    if endpoint == vertex and (local[0] >> port) & 1:
                        parity ^= (word >> edge) & 1
                expected.append(parity)
        assert [(word & row).bit_count() % 2 for row in rows] == expected


@pytest.mark.parametrize('clauses,expected', [
    (((1,),), 1 << 19),
    (((1,), (-1,)), 0),
    (((1,), (1,), (-2,)), 1 << 18),
])
def test_unit_only_n20_is_exact(clauses, expected):
    result = cnf.count(cnf.Formula(20, clauses))
    assert result['status'] == 'PASS_EXACT_COUNT'
    assert result['count'] == expected
    assert result['source_qualified'] is False


def test_trivial_count_respects_integer_budget():
    result = cnf.count(cnf.Formula(1000, ()), limits=Limits(max_integer_bits=8))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'count' not in result


def test_sparse_trivial_count_respects_integer_budget():
    result = hashes.count_sparse_formula(1000, (), 1, 2,
                                        limits=Limits(max_integer_bits=8))
    assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
    assert 'count' not in result


def test_greedy_large_exponent_refuses_before_constructing_integer():
    budget = Budget(Limits(max_work=10, max_seconds=2, max_items=100))
    with pytest.raises(ResourceLimit, match='allowance'):
        hashes.greedy_rows(1, ((1,),), (), 10 ** 9, budget=budget)


def test_greedy_supports_unbounded_work_with_time_limit():
    limits = Limits(max_work=None, max_seconds=3, max_items=100)
    rows = hashes.greedy_rows(1, ((1,),), (), 1, limits=limits)
    assert len(rows) == 3
    for bits in (0, 1):
        violation = int(bits == 0)
        accepts = all(((row & violation).bit_count() % 2) == 0 for row in rows)
        assert accepts == bool(bits)


def test_sparsification_search_uses_ceiling_not_strict_log_bound():
    # k=2: Gamma=4, C=4; M=32 fails and M=64 first satisfies 4*10 <= (2/3)*64.
    assert sparsify.select_M(2, 2, 3, Budget()) == 64


@pytest.mark.parametrize('formula', [
    cnf.Formula(4, ((1, 2), (1, 3), (1, 4))),
    cnf.Formula(6, ((1, 2), (1, 3), (1, 4))),
    cnf.Formula(4, ((1, 1), (2, -2), (-1, 3))),
])
def test_fixed_density_encoding_matches_independent_count(formula):
    expected = sum(_sat(formula.clauses, bits)
                   for bits in product((False, True), repeat=formula.n))
    result = cnf.count_fixed_density(formula,
                                    limits=Limits(max_work=100000000, max_seconds=30))
    assert result['status'] == 'PASS_EXACT_COUNT'
    assert result['count'] == expected
    assert result['source_qualified'] is False
    assert result['complexity_proven'] is False


def test_greedy_unbounded_work_still_preflights_candidate_storage():
    limits = Limits(max_work=None, max_items=100, max_seconds=2)
    with pytest.raises(ResourceLimit, match='allocation item allowance'):
        hashes.greedy_rows(1, ((1,),), (), 1000, limits=limits)


def test_local_code_preflights_combination_pool():
    limits = Limits(max_work=1000000, max_items=4, max_seconds=2)
    with pytest.raises(ResourceLimit, match='allocation item allowance'):
        hashes._local_code(2, 20, 1, 10, Budget(limits))
