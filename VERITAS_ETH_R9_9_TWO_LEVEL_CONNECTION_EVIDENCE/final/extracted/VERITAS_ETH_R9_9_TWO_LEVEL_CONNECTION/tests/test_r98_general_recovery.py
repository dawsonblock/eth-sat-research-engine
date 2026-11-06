"""Complete point-grid recovery without a constant-row premise."""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from math import comb

import pytest

from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_interpolation.source_hermite import (
    SourceHermiteLimits,
    make_source_tapered_plan,
    reconstruct_source_tapered,
)
from veritas.research.eth_recursive_contraction_v39.described_network import describe_integer_network
from veritas.research.parent_child_r98.general_recovery import (
    general_points,
    make_general_plan,
    recover_general_grid,
)
from veritas.research.parent_child_r98.model import Budget, PacketLayout, Refusal, canonical, from_described
from veritas.research.parent_child_r98.shrinking_engine import DEFAULT_SHRINKING_POLICY
from veritas.research.tensor import Factor, TensorNetwork


def parent(M=22, degree=7):
    network = TensorNetwork(M, tuple(
        factor for edge in range(M)
        for factor in (Factor((edge,), (1, 2), "row:" + str(edge)),
                       Factor((edge,), (3, 5), "col:" + str(edge)))
    ))
    return from_described(
        describe_integer_network(network, creation_precision=8,
                                 defining_polynomial=first_irreducible(degree)),
        root_s=max(2, M), precision=8,
    )


def budget(**changes):
    return Budget(replace(DEFAULT_SHRINKING_POLICY, **changes))


def layout(p):
    # Recovery consumes the layout binding and L, not a packing certificate.
    # Topology and per-point contraction are checked by the driver separately.
    return PacketLayout(p.content_digest, 1, 1, canonical({}), "balanced_vertices")


def sample(p, terms):
    b = budget()
    plan = make_general_plan(p, budget=b)
    rows = []
    for t, zeta, precision in general_points(p, plan, budget=b):
        ring = ExtensionRing(precision, p.defining_polynomial,
                             max_precision_bits=b.policy.max_precision)
        point = ring.add(ring.elem([t]), ring.mul(ring.elem([4]), zeta))
        value = ring.zero
        for power, coefficient in terms.items():
            value = ring.add(value, ring.mul(ring.elem(coefficient), ring.pow(point, power)))
        rows.append([t, list(zeta), precision, list(value)])
    return plan, rows


def test_general_22_edge_plan_uses_full_nonconstant_grid_and_exact_basis():
    p = parent()
    plan = make_general_plan(p, budget=budget())
    assert plan.degree_bound == 66
    assert [(n.t, n.multiplicity, n.precision_bits) for n in plan.nodes] == [(-1, 66, 1416), (1, 66, 1416)]
    assert len(list(general_points(p, plan, budget=budget()))) == 134
    for power in range(67):
        value = sum((weight * comb(power, j) * t ** (power - j) * 4**j
                     for t, weights in plan.weights
                     for j, weight in enumerate(weights) if j <= power), Fraction(0))
        assert value == int(power == 0)


def test_general_full_degree_extension_polynomial_recovers_every_coordinate():
    p = parent()
    _, rows = sample(p, {0: (19, 7, 3), 1: (-23, 4), 32: (7,), 66: (9, 2)})
    value, certificate = recover_general_grid(p, layout(p), rows, budget=budget())
    assert value == ((19, 7, 3, 0, 0, 0, 0),)
    assert b'"degree_bound":66' in certificate.payload
    assert b'"source_qualified":false' in certificate.payload


@pytest.mark.parametrize("power", range(7))
def test_complete_small_monomial_point_grids(power):
    p = parent(2, 3)
    _, rows = sample(p, {power: (1,)})
    value, _ = recover_general_grid(p, layout(p), rows, budget=budget())
    assert value == ((int(power == 0), 0, 0),)


def test_rational_cauchy_polynomial_with_integral_shifted_coefficients():
    p = parent(2, 3)
    b = budget()
    plan = make_general_plan(p, budget=b)
    rows = []
    for t, zeta, precision in general_points(p, plan, budget=b):
        ring = ExtensionRing(precision, p.defining_polynomial)
        # W(T)=1+T/2-T^2-T^3/2 has even denominators in T. Its
        # shifted coefficients at t+4z are integral, as the lemma requires.
        coefficients = (-12, -40, -32) if t == 1 else (4, 8, -32)
        w = ring.zero
        for power, coefficient in enumerate(coefficients, 1):
            w = ring.add(w, ring.mul(ring.elem([coefficient]), ring.pow(zeta, power)))
        value = ring.pow(ring.add(ring.elem([3]), ring.mul(ring.elem([5]), w)), 2)
        rows.append([t, list(zeta), precision, list(value)])
    result, _ = recover_general_grid(p, layout(p), rows, budget=budget())
    assert result == ((64, 0, 0),)


@pytest.mark.parametrize("mutation", ["omit", "duplicate", "node", "boolean_node", "precision", "zeta", "value"])
def test_general_grid_rejects_changed_inventory_and_arithmetic(mutation):
    p = parent(2, 3)
    _, rows = sample(p, {0: (13,), 1: (4,)})
    rows = deepcopy(rows)
    if mutation == "omit":
        rows.pop()
    elif mutation == "duplicate":
        rows[1] = rows[0]
    elif mutation == "node":
        rows[0][0] = 1
    elif mutation == "boolean_node":
        rows[-1][0] = True
    elif mutation == "precision":
        rows[0][2] -= 1
    elif mutation == "zeta":
        rows[0][1][0] = 1
    else:
        rows[0][3][0] = 1 << rows[0][2]
    with pytest.raises(ValueError):
        recover_general_grid(p, layout(p), rows, budget=budget())


def test_general_limits_preflight_before_large_functional(monkeypatch):
    import veritas.research.parent_child_r98.general_recovery as module
    monkeypatch.setattr(module, "make_source_tapered_plan", lambda **kw: pytest.fail("preflight did not run first"))
    with pytest.raises(Refusal, match="residue-distinct"):
        make_general_plan(parent(22, 6), budget=budget())
    with pytest.raises(Refusal, match="residue-distinct"):
        make_general_plan(parent(), budget=budget(), max_points=64)
    with pytest.raises(Refusal, match="precision cap"):
        make_general_plan(parent(), budget=budget(max_precision=1024))
    with pytest.raises(Refusal, match="byte cap"):
        make_general_plan(parent(), budget=budget(max_certificate_bytes=100))


def test_shared_hermite_limits_are_explicit_and_precision_is_coefficientwise():
    with pytest.raises(ValueError, match="degree cap"):
        make_source_tapered_plan(M=22, a=1, u=1, p=8)
    limits = SourceHermiteLimits(max_degree=66, max_precision_bits=2048)
    plan = make_source_tapered_plan(M=22, a=1, u=1, p=8,
                                    max_precision_bits=2048, max_terms=132, limits=limits)
    jets = {node.t: tuple(13 if j == 0 else 0 for j in range(node.multiplicity))
            for node in plan.nodes}
    precisions = {node.t: (node.precision_bits,) * node.multiplicity for node in plan.nodes}
    assert reconstruct_source_tapered(plan, jets, coefficient_precisions=precisions, limits=limits) == 13
    bad = dict(precisions)
    bad[-1] = (1,) + bad[-1][1:]
    reduced = dict(jets)
    reduced[-1] = (1,) + reduced[-1][1:]
    with pytest.raises(ValueError, match="invalid coefficient precision|insufficient coefficient"):
        reconstruct_source_tapered(plan, reduced, coefficient_precisions=bad, limits=limits)
    with pytest.raises(ValueError, match="degree cap"):
        reconstruct_source_tapered(plan, jets)
