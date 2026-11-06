"""Independent global polynomial elimination, including beyond the old wire cap."""

import pytest

from veritas.research.eth_recursive_contraction_v39.described_network import (
    describe_integer_network,
)
from veritas.research.independent_r95.recipe_oracle import ReferenceArithmetic
from veritas.research.parent_child_r98 import (
    Budget,
    ExponentTuple,
    Policy,
    from_described,
)
from veritas.research.parent_child_r98.independent import (
    parent_point,
)
from veritas.research.parent_child_r98.independent import (
    tuple_coefficient as exhaustive_coefficient,
)
from veritas.research.parent_child_r98.model import Refusal
from veritas.research.parent_child_r98.modes import build_modes
from veritas.research.parent_child_r98.packing import construct_layout
from veritas.research.parent_child_r98.shrinking_oracle import (
    certify_constant_deformation,
    contract_independent,
    eliminate_factors,
    tuple_coefficient,
)
from veritas.research.parent_child_r98.shrinking_oracle import (
    parent_point as component_parent_point,
)
from veritas.research.tensor import Factor, TensorNetwork


def parent(n, *, constant_rows=False):
    factors = tuple(
        factor
        for i in range(n)
        for factor in (
            Factor((i,), (2, 2) if constant_rows else (-2 + i, 3 + i), f"row:{i}"),
            Factor((i,), (4 - i, 5 - i), f"col:{i}"),
        )
    )
    return from_described(
        describe_integer_network(
            TensorNetwork(n, factors), creation_precision=5, defining_polynomial=25
        ),
        root_s=16,
        precision=5,
    )


@pytest.fixture(scope="module")
def two_modes():
    p, budget = parent(3), Budget(Policy(max_tuples=100_000))
    layout = construct_layout(p, budget=budget)
    modes = build_modes(p, layout, -1, (0, 1, 0, 0), budget=budget)
    assert len(modes.certificate["modes"]) == 2
    return p, layout, modes


@pytest.mark.parametrize(
    "exponents", ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2), (2, 1), (4, 0))
)
def test_sparse_elimination_matches_independent_exhaustive_coefficient(
    two_modes, exponents
):
    p, layout, modes = two_modes
    beta = ExponentTuple(modes.content_digest, exponents)
    assert tuple_coefficient(
        p, layout, modes, beta, budget=Budget()
    ) == exhaustive_coefficient(p, layout, modes, beta, budget=Budget())


def test_five_edge_separable_point_does_not_use_exponential_assignment_or_children(
    monkeypatch,
):
    p, budget = parent(5), Budget()
    layout = construct_layout(p, a=1, u=1, strategy="scaled_singletons", budget=budget)
    modes = build_modes(p, layout, -1, (0, 1, 0, 0), budget=budget)
    assert not modes.certificate["modes"]
    beta = ExponentTuple(modes.content_digest, ())
    with pytest.raises(Refusal, match="one-tuple oracle cap"):
        exhaustive_coefficient(p, layout, modes, beta, budget=Budget())

    import veritas.research.parent_child_r98.constructor as production

    monkeypatch.setattr(
        production,
        "construct_children",
        lambda *a, **kw: pytest.fail("production constructor called"),
    )
    expected = parent_point(p, layout, modes, budget=Budget())
    assert tuple_coefficient(p, layout, modes, beta, budget=Budget()) == expected
    assert component_parent_point(p, layout, modes, budget=Budget()) == expected


def test_coefficient_term_cap_fails_closed(two_modes):
    p, layout, modes = two_modes
    beta = ExponentTuple(modes.content_digest, (1, 1))
    with pytest.raises(Refusal, match="polynomial term cap"):
        tuple_coefficient(p, layout, modes, beta, budget=Budget(), max_terms=1)


def test_factor_width_cap_fails_before_table_enumeration():
    ar = ReferenceArithmetic(5, 25, 1, 10_000)
    with pytest.raises(Refusal, match="factor width cap"):
        eliminate_factors([((0, 1), {})], ar, budget=Budget(Policy(max_factor_bits=1)))


def test_independent_constant_certificate_checks_every_row_entry():
    p = parent(5, constant_rows=True)
    result = certify_constant_deformation(p, budget=Budget())
    assert result["parent_digest"] == p.content_digest
    assert result["degree_bound"] == 0
    assert result["row_tensors_checked"] == 5
    assert result["row_entries_checked"] == 10
    assert "result" not in result
    assert result["source_qualified"] is False


def test_constant_deformation_certificate_has_pointwise_independent_evidence():
    p, budget = parent(5, constant_rows=True), Budget()
    certify_constant_deformation(p, budget=budget)
    layout = construct_layout(p, a=1, u=1, strategy="scaled_singletons", budget=budget)
    base = contract_independent(p, Budget())
    for node, point in ((-1, (0, 0, 0, 0)), (1, (0, 1, 0, 0))):
        modes = build_modes(p, layout, node, point, budget=budget)
        value = component_parent_point(p, layout, modes, budget=Budget())
        assert tuple(x % 32 for x in value[0]) == base[0]


def test_nonconstant_inherited_row_cannot_claim_constant_deformation():
    with pytest.raises(ValueError, match="not constant"):
        certify_constant_deformation(parent(3), budget=Budget())


def test_constant_certificate_work_limit_fails_closed():
    with pytest.raises((Refusal, ValueError), match="budget"):
        certify_constant_deformation(
            parent(1, constant_rows=True), budget=Budget(Policy(max_work=1))
        )


def test_component_elimination_preserves_isolated_scalars_and_shared_variables():
    ar = ReferenceArithmetic(5, 25, 1, 100_000)
    scalar = ar.scalar
    factors = [
        ((), {(): scalar(3)}),
        ((0,), {(0,): scalar(1), (1,): scalar(2)}),
        ((0,), {(0,): scalar(4), (1,): scalar(5)}),
        ((1,), {(0,): scalar(6), (1,): scalar(7)}),
    ]
    result = eliminate_factors(factors, ar, budget=Budget())
    assert result == scalar(3 * (1 * 4 + 2 * 5) * (6 + 7))
