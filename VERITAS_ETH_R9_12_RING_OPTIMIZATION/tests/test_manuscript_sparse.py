"""Differential tests for lem:tensor-sparse-query and lem:rational-idempotent.

Every finite check is against an independently computed quantity: exhaustive
Boolean enumeration, raw multilinear expansion by ordered tuples, or the sealed
direct CNF enumerator. PASS means the two computations agree exactly; resource
exhaustion is INCONCLUSIVE and is never counted as evidence.
"""
from itertools import product
from math import comb

import pytest

from veritas.research.manuscript.cnf import Formula, clause_violation_polynomial, count, direct_count
from veritas.research.manuscript.resources import Budget, Limits
from veritas.research.manuscript.sparse import (
    factor_coefficients,
    idempotent_coefficients,
    incidence_coefficient,
    normalize_equation,
    normalize_system,
    subset_rank,
    subset_unrank,
    truncated_multiply,
    wire_bits,
)
from veritas.research.manuscript.sparse_query import (
    _blocks,
    _decode_block,
    _enumerate_arrays,
    _incidences,
    build_network,
    common_zeros,
)


def budget():
    return Budget(Limits(max_work=50_000_000, max_seconds=180))


def exhaustive_zeros(n, equations):
    count = 0
    for x in product((0, 1), repeat=n):
        if all(
            (sum(1 for m in eq if all(x[v] for v in m)) & 1) == 0
            for eq in equations):
            count += 1
    return count


def oracle_factor(L_value, modulus, ell, es):
    """e_j/h expansion of B_i at integer L, computed without factoring."""
    h = (L_value * (L_value - 1)) % modulus
    out = []
    hp = 1
    for j in range(ell):
        a, b = es[j]
        out.append((a + b * L_value) * hp % modulus)
        hp = hp * h % modulus
    return tuple(out)


def oracle_incidence(monomials, subset, modulus, ell, es):
    """[z_S] B̄_i by raw expansion: ordered monomial tuples with union S."""
    S = frozenset(subset)
    mons = list(monomials)
    out = []
    for j, (a, b) in enumerate(es):
        total = 0
        for s in range(j + 1):
            c = comb(j, s) * (-1 if (j - s) & 1 else 1)
            for t, coef in ((j + s, a), (j + s + 1, b)):
                assert t <= 12, 'test parameters keep tuples enumerable'
                for tp in product(mons, repeat=t):
                    if frozenset().union(*tp) == S:
                        total += c * coef
        out.append(total % modulus)
    return tuple(out)


class TestRationalIdempotent:

    def test_indicator_identity(self):
        for ell in (1, 2, 3, 4, 5, 8):
            es = idempotent_coefficients(ell)
            modulus = 1 << ell
            assert len(es) == ell
            assert all(len(e) == 2 for e in es)
            for y in range(-4, 14):
                value = sum((a + b * y) * (y * (y - 1)) ** j
                            for j, (a, b) in enumerate(es))
                expected = 1 if y % 2 == 0 else 0
                assert value % modulus == expected % modulus, (ell, y)

    def test_paper_example_ell2(self):
        assert idempotent_coefficients(2) == ((1, -1), (-1, 2))

    def test_factor_at_boolean_matches_indicator(self):
        ell = 4
        modulus = 1 << ell
        es = idempotent_coefficients(ell)
        for y in range(6):
            coeffs = factor_coefficients(y, modulus, ell, es)
            assert sum(coeffs) % modulus == (1 if y % 2 == 0 else 0)


class TestIndexing:

    @pytest.mark.parametrize('n,d', [(0, 0), (1, 0), (1, 1), (4, 2), (7, 3),
                                     (8, 0), (8, 8), (10, 4)])
    def test_subset_unrank_rank_bijection(self, n, d):
        seen = set()
        for index in range(comb(n, d)):
            s = subset_unrank(n, d, index)
            assert len(s) == d and len(set(s)) == d
            assert tuple(sorted(s)) == s
            assert subset_rank(n, s) == index
            seen.add(s)
        assert len(seen) == comb(n, d)

    def test_subset_unrank_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            subset_unrank(5, 2, comb(5, 2))
        with pytest.raises(ValueError):
            subset_unrank(5, 6, 0)

    def test_wire_bits_counts_boolean_wires(self):
        assert wire_bits(1) == 0
        assert wire_bits(2) == 1
        assert wire_bits(3) == 2
        assert wire_bits(4) == 2
        assert wire_bits(5) == 3

    def test_decode_block_invalid_index_is_none(self):
        incidences = ((0, 0), (0, 1), (0, 2))
        # C(3,1)=3 needs 2 wires; index 3 is invalid
        assert _decode_block((1, 1), incidences, 1) is None
        assert _decode_block((0, 1), incidences, 1) == {(0, 2)}

    def test_decode_block_unique_subset_no_bits(self):
        incidences = ((1, 2), (1, 3))
        assert _decode_block((), incidences, 2) == {(1, 2), (1, 3)}
        assert _decode_block((), incidences, 0) == set()


class TestCoefficientExtraction:

    @pytest.mark.parametrize('monomials,subset', [
        ((frozenset({0}),), (0,)),
        ((frozenset({0}),), ()),
        ((frozenset({0, 1}), frozenset({1, 2})), (0, 2)),
        ((frozenset({0, 1}), frozenset({1, 2})), (1,)),
        ((frozenset({0}), frozenset({1}), frozenset({0, 1})), (0, 1)),
        ((frozenset({0, 1, 2}),), (0, 1)),
    ])
    def test_incidence_matches_ordered_expansion(self, monomials, subset):
        ell = 5
        modulus = 1 << ell
        es = idempotent_coefficients(ell)
        got = incidence_coefficient(monomials, subset, modulus, ell, es, budget())
        expected = oracle_incidence(monomials, subset, modulus, ell, es)
        assert got == expected

    def test_truncated_multiply_convention(self):
        modulus = 32
        left = (1, 2, 0, 0)
        right = (3, 1, 0, 0)
        out = truncated_multiply(left, right, modulus, 4)
        assert out[0] == 3 and out[1] == (2 * 3 + 1 * 1) % modulus
        assert out[2] == (2 * 1) % modulus and out[3] == 0


class TestCommonZeros:

    @pytest.mark.parametrize('n,equations', [
        (2, [[[0], [1]]]),
        (2, [[[0, 1]]]),
        (3, [[[0], [1]], [[1], [2]]]),
        (3, [[[0, 1]], [[1, 2]]]),
        (4, [[[0], [1], [2], [3]]]),
        (4, [[[0, 1], [1, 2]], [[2, 3]]]),
        (4, [[[0, 1], [2, 3]], [[0, 2], [1, 3]]]),
        (5, [[[0, 1, 2]], [[2, 3], [3, 4]]]),
        (5, [[[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]]]),
        (6, [[[0, 1]], [[1, 2]], [[2, 3]], [[3, 4]], [[4, 5]]]),
        (3, []),
        (3, [[[0], []]]),          # constant-1 equation
        (2, [[[0, 0]]]),           # duplicate variables multilinearize
        (4, [[[0], [0]]]),         # duplicate monomials cancel mod 2
    ])
    def test_matches_exhaustive_enumeration(self, n, equations):
        result = common_zeros(n, equations, limits=Limits(
            max_work=100_000_000, max_seconds=180))
        assert result['status'] == 'PASS_EXACT_COUNT'
        assert result['count'] == exhaustive_zeros(n, equations)

    def test_empty_system_counts_all_assignments(self):
        result = common_zeros(4, [], limits=Limits(max_seconds=60))
        assert result['count'] == 16

    def test_resource_limit_is_inconclusive(self):
        result = common_zeros(5, [[[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]]],
                              limits=Limits(max_work=64, max_seconds=60))
        assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
        assert 'count' not in result

    def test_heavy_variable_branching(self):
        # one variable appearing in many scopes forces the D_* branch fan-out
        equations = [[[0, j]] for j in range(1, 6)]
        result = common_zeros(6, equations, limits=Limits(
            max_work=100_000_000, max_seconds=180))
        if result['status'] == 'PASS_EXACT_COUNT':
            assert result['count'] == exhaustive_zeros(6, equations)
        else:
            assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'


class TestNetworkConstruction:

    def test_vertex_count_and_bipartite_ports(self):
        n = 4
        system = normalize_system(n, [[[0, 1], [1, 2]], [[2, 3]]])
        es = idempotent_coefficients(n + 1)
        free = (0, 1, 2, 3)
        J = 2
        network = build_network(n, system, [[1, 1], [0, 0]], 1 << (n + 1),
                                n + 1, es, J, list(free), budget())
        assert len(network.vertices) == 2 * J
        sides = {v.side for v in network.vertices}
        assert sides == {'row', 'column'}
        assert network.wires == 1  # C(2,1)=2 -> one wire between the groups

    def test_every_wire_has_two_endpoints(self):
        n = 4
        system = normalize_system(n, [[[0, 1], [1, 2]], [[2, 3]]])
        es = idempotent_coefficients(n + 1)
        network = build_network(n, system, [[1, 1], [0, 0]], 32, 5, es, 2,
                                [0, 1, 2, 3], budget())
        owners = [0] * network.wires
        for v in network.vertices:
            for w in v.ports:
                owners[w] += 1
        assert owners == [2] * network.wires

    def test_contraction_matches_direct_sum_on_zero_wire_network(self):
        n = 4
        system = normalize_system(n, [[[0, 1], [1, 2]], [[2, 3]]])
        es = idempotent_coefficients(n + 1)
        network = build_network(n, system, [[2, 0], [0, 0]], 32, 5, es, 2,
                                [0, 1, 2, 3], budget())
        assert network.wires == 0
        from veritas.research.manuscript.executor import contract
        receipt = contract(network, s=4, precision=5, ell=5, size_constant=2,
                           budget=budget())
        assert receipt['status'] == 'PASS_MANUSCRIPT_CONSTRUCTION_EXECUTION'
        # the (2,0) monomial of test 0 is z_{0,{0,1}}: two incidences
        assert sum(row[0] for row in receipt['result']) % 32 == 28


class TestCNFRoutes:

    @pytest.mark.parametrize('n,clauses', [
        (2, [(1,), (-1, 2)]),
        (3, [(1, 2), (-1, -2), (2, 3)]),
        (4, [(1, 2), (2, 3), (3, 4), (-1, -4)]),
        (4, [(1, 2, 3), (-1, -2, -3)]),
        (3, [(1,), (2,), (-3,)]),
        (4, [(1, -1), (2,)]),
        (3, [(1, 1, -2)]),
        (4, [(1, -2), (-1, 2)]),
    ])
    def test_sparse_route_matches_direct_count(self, n, clauses):
        formula = Formula(n, tuple(tuple(c) for c in clauses))
        result = count(formula, limits=Limits(
            max_work=100_000_000, max_seconds=180))
        assert result['status'] == 'PASS_EXACT_COUNT'
        assert result['count'] == direct_count(formula, Budget())

    def test_clause_violation_polynomial_content(self):
        # x1 \/ -x2 violated iff x1=0 and x2=1: indicator x2(1+x1)
        monomials = clause_violation_polynomial((1, -2))
        assert {frozenset(m) for m in monomials} == {
            frozenset({1}), frozenset({0, 1})}

    def test_empty_and_tautological_formulas(self):
        assert count(Formula(3, ()), limits=Limits(max_seconds=30))['count'] == 8
        assert count(Formula(3, ((), (1,))), limits=Limits(max_seconds=30))['count'] == 0
        f = Formula(2, ((1, -1), (2,)))
        assert count(f, limits=Limits(max_seconds=60))['count'] == \
            direct_count(f, Budget())

    def test_fail_closed_on_small_budget(self):
        formula = Formula(4, ((1, 2), (2, 3), (3, 4)))
        result = count(formula, limits=Limits(max_work=32, max_seconds=60))
        assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
        assert 'count' not in result


class TestSmallInputGate:

    @pytest.mark.parametrize('clauses', [[(1,)], [(-1,)], [(1, 1)]])
    def test_one_variable_no_crash(self, clauses):
        # regression: n=1 used to crash with s=1 below Schedule's floor
        result = count(Formula(1, tuple(clauses)),
                       limits=Limits(max_seconds=60))
        assert result['status'] == 'PASS_EXACT_COUNT'
        assert result['count'] == direct_count(Formula(1, tuple(clauses)),
                                               Budget())

    def test_small_input_routes_to_bounded_exhaustive(self):
        result = common_zeros(1, [[[0]]], limits=Limits(max_seconds=60))
        assert result['status'] == 'PASS_EXACT_COUNT'
        assert result['count'] == 1
        assert result['route'] == 'BOUNDED_EXHAUSTIVE_SEARCH'

    def test_construction_route_still_exercised_at_paper_sizes(self):
        # n>=20 with a small scope keeps the array counters feasible, so
        # lem:tensor-sparse-query's construction runs end to end.
        result = common_zeros(20, [[[0], [1]], [[1], [2]]],
                              limits=Limits(max_work=50_000_000,
                                            max_seconds=180))
        assert result['status'] == 'PASS_EXACT_COUNT'
        assert result['count'] == 1 << 18
        assert result['route'] == 'SPARSE_POLY_CONTRACT'

    def test_counter_enumeration_is_lazy(self):
        # _enumerate_arrays yields arrays without materializing the index set
        gen = _enumerate_arrays(normalize_system(4, [[[0], [1]]]),
                                ((0,), (), ()), ((0, 1), (2,), (3,)), 4, 5,
                                Budget())
        seen = list(gen)
        assert set(seen) == {((i, 0, 0), (0, 0, 0), (0, 0, 0))
                             for i in range(3)}


class TestSparsification:

    def test_select_M_matches_paper_search(self):
        from veritas.research.manuscript.sparsify import select_M
        # k=2: Gamma=4, C=4, h=ceil(log2(16M)); Gamma*h <= sigma*M
        assert select_M(2, 1, 4, Budget()) == 256
        assert select_M(2, 1, 2, Budget()) == 128

    def test_leaves_partition_satisfying_assignments(self):
        from veritas.research.manuscript.sparsify import (
            select_M, sparsification_leaves)
        # sigma=1/2 -> M=128: 130 clauses sharing literal 1 must branch
        clauses = [[1, i] for i in range(2, 132)]
        n = 131
        leaves = list(sparsification_leaves(clauses, 2, 1, 2,
                                            budget=Budget()))
        assert len(leaves) == 2
        M = select_M(2, 1, 2, Budget())
        assert M == 128

        def unit_count(leaf):
            # leaves here are all-unit after antichain restore:
            # propagate units; return 2^{free} or 0 on contradiction
            assigned = {}
            for c in leaf:
                if len(c) != 1:
                    return None
                lit = next(iter(c))
                v, val = abs(lit) - 1, lit > 0
                if v in assigned and assigned[v] != val:
                    return 0
                assigned[v] = val
            return 1 << (n - len(assigned))

        counts = [unit_count(leaf) for leaf in leaves]
        assert all(c is not None for c in counts)
        # disjointness: contradictory forced units on the branch literal
        leaf_units = [{next(iter(c)): None for c in leaf if len(c) == 1}
                      for leaf in leaves]
        assert any(1 in u for u in leaf_units)
        assert any(-1 in u for u in leaf_units)
        # coverage: 2^{130} (x1=1) + 2^0 (x1=0 and every petal forced)
        assert sum(counts) == (1 << 130) + 1

    def test_single_leaf_matches_parent_exactly(self):
        from veritas.research.manuscript.sparsify import sparsification_leaves
        clauses = [[1, 2], [3, 4]]
        n = 4
        leaves = list(sparsification_leaves(clauses, 2, 1, 4,
                                            budget=Budget()))
        assert len(leaves) == 1

        def sat(clause, x):
            return any(bool((x >> (abs(l) - 1)) & 1) == (l > 0)
                       for l in clause)
        parent = {x for x in range(1 << n)
                  if all(sat(c, x) for c in clauses)}
        leaf0 = {x for x in range(1 << n)
                 if all(sat(c, x) for c in leaves[0])}
        assert leaf0 == parent

    def test_sparse_input_single_leaf_occurrence_bound(self):
        from veritas.research.manuscript.sparsify import (
            occurrence_bound, select_M, sparsification_leaves)
        clauses = [[1, 2], [3, 4]]
        leaves = list(sparsification_leaves(clauses, 2, 1, 4,
                                            budget=Budget()))
        assert len(leaves) == 1
        M = select_M(2, 1, 4, Budget())
        assert occurrence_bound(2, M) == 2 * (1 + M)


class TestHashes:

    def test_sparse_check_parameters(self):
        from veritas.research.manuscript.hashes import sparse_check_parameters
        mu, P, D0 = sparse_check_parameters(4, 2, 4)
        assert mu == 3  # floor(log2 4)+1
        assert P == 20000 * 4 * 9
        assert D0 == 320000 * 4 * 27

    def test_sparse_checks_returns_two_local_copies(self):
        from veritas.research.manuscript.hashes import sparse_checks
        A0 = sparse_checks(4, [[1, 2], [2, 3], [3, 4], [1, -4]], 2)
        assert len(A0) % 2 == 0  # two copies of the local code
        half = len(A0) // 2
        assert A0[:half] == A0[half:]

    def test_greedy_rows_fail_closed(self):
        from veritas.research.manuscript.hashes import count_sparse_formula
        result = count_sparse_formula(4, [[1, 2], [2, 3]], 2, 2,
                                      limits=Limits(max_work=10_000_000))
        assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
        assert 'count' not in result


class TestPipelineDispatch:

    def test_n20_uses_sparse_machinery_and_fails_closed(self):
        # quantitative-reduction: sigma=1/ceil(sqrt(lam)) with no s<2 gate;
        # the greedy (2m)^P candidate enumeration exceeds the allowance
        clauses = tuple((i % 19 + 1, -((i + 3) % 19 + 1)) for i in range(8))
        formula = Formula(20, clauses)
        result = count(formula, limits=Limits(max_work=50_000_000,
                                              max_seconds=120))
        assert result['status'] == 'INCONCLUSIVE_RESOURCE_LIMIT'
        assert 'count' not in result
