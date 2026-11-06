from dataclasses import replace
from fractions import Fraction

import pytest

from veritas.core.cnf import CNF
from veritas.research.tensor import from_cnf
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_interpolation.tapered_hermite import (
    make_tapered_plan, reconstruct_tapered, sample_integer_polynomial,
)
from veritas.research.tapered_v4 import RecursionPolicy, TaperedState, contract_recursive


def corrupt_weight(plan):
    weights = list(plan.recovery_plan.weights)
    weights[0] += Fraction(1)
    return replace(plan, recovery_plan=replace(plan.recovery_plan, weights=tuple(weights)))


def test_reconstruction_rejects_forged_weight_that_previously_returned_wrong_count():
    plan = make_tapered_plan(M=1, a=1, u=1, p=5)
    jets = sample_integer_polynomial(plan, (19,))
    assert reconstruct_tapered(plan, jets) == 19
    with pytest.raises(ValueError, match='weights do not recover'):
        reconstruct_tapered(corrupt_weight(plan), jets)


def test_reconstruction_rejects_forged_source_precision_and_multiplicity():
    plan = make_tapered_plan(M=1, a=1, u=1, p=5)
    jets = sample_integer_polynomial(plan, (19, -23, 7, 9))
    first = plan.nodes[0]
    for node in (replace(first, precision_bits=first.precision_bits + 1),
                 replace(first, multiplicity=first.multiplicity + 1)):
        with pytest.raises(ValueError, match='nodes or prescribed precision'):
            reconstruct_tapered(replace(plan, nodes=(node,) + plan.nodes[1:]), jets)


def test_recursor_rejects_forged_recovery_functional_before_count(monkeypatch):
    from veritas.research.tapered_v4 import recursor
    source = describe_integer_network(from_cnf(CNF.from_lists(1, [[1]])),
                                      creation_precision=2, defining_polynomial=first_irreducible(3))
    state = TaperedState(source, 0, 2, first_irreducible(3), 1, source.edges)
    original = recursor.make_source_tapered_plan
    def forged(**kwargs):
        plan = original(**kwargs)
        rows = list(plan.weights)
        t, weights = rows[0]
        rows[0] = (t, (weights[0] + 1,) + weights[1:])
        return replace(plan, weights=tuple(rows))
    monkeypatch.setattr(recursor, 'make_source_tapered_plan', forged)
    result = contract_recursive(state, RecursionPolicy(allow_nonshrinking_leaf=True))
    assert result['status'] == 'INCONCLUSIVE_INVARIANT_FAILURE'
    assert 'weights differ' in result['reason']
    assert 'result' not in result and 'certificate' not in result
