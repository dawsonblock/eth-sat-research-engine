import itertools
import random

import pytest

from research_anthropic.eight_square import crossing_coefficients
from research_anthropic.factors import CrossingFactor
from research_anthropic.grid import direct_grid, rectangle_grid
from research_anthropic.cnf_network import count_occurrences, encode_cnf
from eth_sat.model import CNF


def test_all_small_crossing_factorizations():
    for x, y, u, v in itertools.product(range(2), repeat=4):
        expected = crossing_coefficients(x, y, u, v, 1)
        for i, coefficient in enumerate(expected):
            for direction, left, right in (("row", (x, y), (u, v)),
                                           ("column", (x, u), (y, v))):
                factor = CrossingFactor(1, i, direction)
                assert sum(a * b for a, b in
                           (factor.evaluate(left, right, j) for j in range(1 << factor.bits))) == coefficient


def test_compressed_factors_on_padded_and_full_blocks():
    rng = random.Random(708)
    for width in (5, 6, 7):
        for degree in range((width + 2) // 3 + 1):
            for direction in ("row", "column"):
                factor = CrossingFactor(width, degree, direction)
                assert factor.bits <= 2 * width
                for _ in range(4):
                    x, y, u = (rng.randrange(1 << width) for _ in range(3))
                    # Force compatible xor as well as arbitrary boundaries: the
                    # former exercise nonzero and cancellation contributions.
                    v = x ^ y ^ u if _ % 2 == 0 else rng.randrange(1 << width)
                    left, right = ((x, y), (u, v)) if direction == "row" else ((x, u), (y, v))
                    got = sum(a * b for a, b in
                              (factor.evaluate(left, right, theta) for theta in range(1 << factor.bits)))
                    assert got == crossing_coefficients(x, y, u, v, width)[degree]


def test_rectangle_grid_matches_independent_clique_enumeration():
    rng = random.Random(144)
    cases = [tuple((1,) * 8 for _ in range(4)), tuple((0,) * 8 for _ in range(4))]
    cases += [tuple(tuple(rng.randrange(-2, 3) for _ in range(8)) for _ in range(4))
              for _ in range(12)]
    for tables in cases:
        expected, baseline = direct_grid(1, tables)
        got = rectangle_grid(1, tables)
        assert got.value == expected
        assert got.numerator == expected * got.denominator
        assert len(got.modes) == 2
        assert baseline.local_settings == 64
        assert got.ledger.local_settings == 4096
        assert rectangle_grid(1, tables, orientation="column").value == expected


def test_invalid_inputs_and_work_guards():
    with pytest.raises(ValueError):
        CrossingFactor(0, 0, "row")
    with pytest.raises(ValueError):
        CrossingFactor(3, 2, "row")
    with pytest.raises(ValueError):
        CrossingFactor(1, 0, "diagonal")
    with pytest.raises(ValueError):
        CrossingFactor(3, 0, "row").evaluate((8, 0), (0, 0), 0)
    with pytest.raises(ValueError):
        direct_grid(2, [(1,) * 64] * 4, max_assignments=1)
    with pytest.raises(ValueError):
        rectangle_grid(1, [(1,) * 8] * 4, max_local_settings=1)
    with pytest.raises(ValueError):
        rectangle_grid(1, [(1,) * 8] * 3)
    with pytest.raises(ValueError):
        rectangle_grid(1, [(1,) * 8] * 4, orientation="diagonal")


def test_occurrence_network_matches_independent_cnf_truth_table():
    cases = [CNF.from_signed_clauses(3, []), CNF.from_signed_clauses(2, [[]]),
             CNF.from_signed_clauses(3, [[1, 1, -1], [-1, 2], [2, 2]])]
    rng = random.Random(7001)
    for _ in range(35):
        clauses = [[rng.choice((-1, 1)) * rng.randrange(1, 5)
                    for _ in range(rng.randrange(4))]
                   for _ in range(rng.randrange(4))]
        cases.append(CNF.from_signed_clauses(4, clauses))
    for formula in cases:
        expected = sum(formula.is_satisfied(bits) for bits in
                       itertools.product((0, 1), repeat=formula.num_variables))
        assert count_occurrences(encode_cnf(formula)) == expected
    with pytest.raises(ValueError):
        count_occurrences(encode_cnf(CNF.from_signed_clauses(1, [[1, 1]])), 2)
