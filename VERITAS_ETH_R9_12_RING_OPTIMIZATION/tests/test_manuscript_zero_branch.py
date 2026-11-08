"""Paper sparse-query branch normalization, with original-equation oracles."""
from itertools import product
import pytest
from veritas.research.manuscript import sparse_query as query
from veritas.research.manuscript.resources import Limits


def original_count(n, equations):
    variables = sorted({v for eq in equations for monomial in eq for v in monomial})
    total = 0
    for bits in product((0, 1), repeat=len(variables)):
        assignment = dict(zip(variables, bits))
        total += all(sum(all(assignment[v] for v in monomial)
                         for monomial in eq) % 2 == 0 for eq in equations)
    return total * (1 << (n - len(variables)))


@pytest.mark.parametrize('equations', [[], [[]], [[], []], [[[0], [0]]]], ids=['empty','zero','two_zeros','cancelled'])
def test_zero_equations_take_empty_branch_without_contraction(monkeypatch, equations):
    def forbidden(*args, **kwargs):
        raise AssertionError('zero branch must not construct a tensor network')
    monkeypatch.setattr(query, '_branch_count', forbidden)
    result = query.common_zeros(20, equations, limits=Limits(max_work=100))
    assert result['status'] == 'PASS_EXACT_COUNT'
    assert result['count'] == original_count(20, equations)
    assert result['ledger']['calls'] == 0


@pytest.mark.parametrize('equation', [[[0]], [[], [0]]])
def test_zero_created_by_heavy_substitution_preserves_free_factor(monkeypatch, equation):
    equations = [equation] * 4  # four scopes exceed D_* = ceil(sqrt(5)) = 3
    def forbidden(*args, **kwargs):
        raise AssertionError('surviving heavy branch has no equations')
    monkeypatch.setattr(query, '_branch_count', forbidden)
    result = query.common_zeros(20, equations, limits=Limits(max_work=100))
    assert result['status'] == 'PASS_EXACT_COUNT'
    assert result['count'] == original_count(20, equations) == 1 << 19


def test_mixed_branch_groups_only_remaining_equations(monkeypatch):
    equations = [[[0]]] * 4 + [[[1]]]
    seen = []
    def inspect(system, n, free, *args):
        seen.append((system, free))
        assert system == ((frozenset({1}),),)
        assert free == tuple(range(1, 20))
        return 1 << 18, None
    monkeypatch.setattr(query, '_branch_count', inspect)
    result = query.common_zeros(20, equations, limits=Limits(max_work=100))
    assert len(seen) == 1
    assert result['count'] == original_count(20, equations)
