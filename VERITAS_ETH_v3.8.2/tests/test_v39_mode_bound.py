from copy import deepcopy
from collections import Counter
from itertools import product
from random import Random

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_recursion_v30.implicit_children import make_bipartite_edges
from veritas.research.eth_packing_v26.implicit import construct_implicit_packing, implicit_mode_source
from veritas.research.eth_recursive_contraction_v39 import (
    make_point_modes, audit_point_mode_multiplicity, weighted_tuple_upper_exponent,
)


def test_checked_point_modes_satisfy_the_abstract_weighted_tuple_bound():
    network = from_cnf(CNF.from_lists(2, [[1, 2], [-1, -2]]))
    packing = construct_implicit_packing(make_bipartite_edges(network), r=2, a=2)
    cert = make_point_modes(implicit_mode_source(packing), node=1, precision=5,
                            extension_degree=3, zeta=(1, 0, 0))
    audit = audit_point_mode_multiplicity(cert)
    assert audit['valid']
    assert cert['mode_tuple_count'] <= 1 << audit['tuple_count_upper_power_of_two']
    assert audit['multiplicity_cap_numerator'] == 6 * audit['M']
    assert audit['multiplicity_cap_denominator'] == audit['D']
    assert not audit['uniform_packing_proven']
    assert not audit['total_runtime_proven']

    corrupt = deepcopy(cert)
    corrupt['modes'][0]['weight'] += 1
    assert not audit_point_mode_multiplicity(corrupt)['valid']


def test_rational_tuple_bound_uses_exact_ceiling_even_for_large_integers():
    for numerator, denominator, precision in (
            (0, 7, 100), (1, 16, 1), (2, 3, 17),
            (10**200 + 9, 10**100 + 7, 10**50 + 3)):
        exponent = weighted_tuple_upper_exponent(numerator, denominator, precision)
        square_target = 16 * numerator * precision
        assert exponent * exponent * denominator >= square_target
        assert exponent == 0 or (exponent - 1) ** 2 * denominator < square_target


def test_rational_tuple_bound_against_independent_small_enumerations():
    random = Random(42069)
    for _ in range(80):
        weights = [random.randrange(1, 6) for _ in range(random.randrange(0, 6))]
        precision = random.randrange(1, 8)
        denominator = random.randrange(1, 8)
        cap = max(Counter(weights).values(), default=0)
        numerator = cap * denominator + random.randrange(denominator)
        actual = sum(
            sum(weight * exponent for weight, exponent in zip(weights, beta)) < precision
            for beta in product(*(range((precision - 1) // weight + 1) for weight in weights))
        )
        exponent = weighted_tuple_upper_exponent(numerator, denominator, precision)
        assert actual <= 1 << exponent


@pytest.mark.parametrize('values', [(-1, 1, 1), (1, 0, 1), (1, -1, 1),
                                    (1, 1, 0), (True, 1, 1), (1, 1.0, 1)])
def test_rational_tuple_bound_rejects_invalid_hypotheses(values):
    with pytest.raises(ValueError):
        weighted_tuple_upper_exponent(*values)
