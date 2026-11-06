from copy import deepcopy
from itertools import product
from random import Random

import pytest

from veritas.core.cnf import CNF
from veritas.research.eth_arithmetic.extension_ring import ExtensionRing
from veritas.research.eth_arithmetic.gf2 import first_irreducible
from veritas.research.eth_arithmetic.residue_points import distinct_residue_points
from veritas.research.eth_interpolation.source_hermite import make_source_tapered_plan
from veritas.research.eth_modes_v27.enumeration import ModeBudgetExceeded
from veritas.research.eth_packing_v26.implicit import (
    construct_implicit_packing, implicit_sparse_mode_source,
)
from veritas.research.eth_recursive_contraction_v39 import describe_integer_network
from veritas.research.eth_recursive_contraction_v39.point_children import contract_point_child_expansion
from veritas.research.eth_recursive_contraction_v39.point_modes import make_point_modes
from veritas.research.eth_recursive_contraction_v39.structural_tuples import structural_tuples
from veritas.research.independent_r82 import (
    audit_finite_pruning, cauchy_polynomial, independent_parent_point,
    independent_tuple_coefficient,
    verify_point_mode_action,
)
from veritas.research.tensor import from_cnf


def _case(n=4, *, precision=5, node=-1, zeta=None, degree=3):
    cnf = CNF.from_lists(n, [[i] for i in range(1, n + 1)])
    f = first_irreducible(degree)
    network = describe_integer_network(from_cnf(cnf), creation_precision=precision,
                                      defining_polynomial=f)
    source = implicit_sparse_mode_source(
        construct_implicit_packing(network.bipartite_edges(), r=4, a=1,
                                  max_work=1_000_000), max_work=1_000_000)
    if zeta is None:
        zeta = (1,) + (0,) * (degree - 1)
    modes = make_point_modes(source, node=node, precision=precision,
                             extension_degree=degree, zeta=zeta,
                             max_tuples=100_000, max_parent_wires=8)
    return network, source, modes


@pytest.mark.parametrize("L", [1, 2, 4, 8])
def test_exact_rational_cauchy_polynomial_division_and_origin_identity(L):
    for x in range(L):
        for y in range(L):
            polynomial = cauchy_polynomial(L, x, y)
            assert polynomial[0] == (1 if x == y else 0)


@pytest.mark.parametrize("node,zeta,precision", [
    (-1, (1, 0, 0), 5), (1, (0, 1, 0), 7), (-1, (1, 1, 0), 3),
])
def test_independent_point_action_matches_production_on_finite_shift(node, zeta, precision):
    network, source, certificate = _case(4, precision=precision, node=node,
                                         zeta=zeta, degree=3)
    checked = verify_point_mode_action(source, certificate)
    assert checked["valid"]
    assert checked["status"] == "FINITE_INDEPENDENT_CAUCHY_MODE_ACTION_CHECKED"
    assert checked["production_mode_count"] == checked["independent_canonical_mode_count"]
    assert checked["packet_entry_count"] > 0


def test_seeded_random_legal_packet_sources_match_direct_rational_oracle():
    rng = Random(82026)
    for _ in range(18):
        n = rng.randrange(2, 7)
        precision = rng.randrange(3, 8)
        degree = 3
        node = rng.choice((-1, 1))
        zeta = tuple(rng.randrange(1 << precision) for _ in range(degree))
        _, source, certificate = _case(n, precision=precision, node=node,
                                       zeta=zeta, degree=degree)
        checked = verify_point_mode_action(source, certificate, max_work=1_000_000)
        assert checked["valid"], checked


def test_larger_packet_geometry_and_higher_node_valuation_are_checked():
    cnf = CNF.from_lists(4, [[i] for i in range(1, 5)])
    f = first_irreducible(3)
    network = describe_integer_network(from_cnf(cnf), creation_precision=7,
                                      defining_polynomial=f)
    source = implicit_sparse_mode_source(
        construct_implicit_packing(network.bipartite_edges(), r=4, a=2,
                                  max_work=3_000_000), max_work=3_000_000)
    certificate = make_point_modes(source, node=-2, precision=7,
                                   extension_degree=3, zeta=(1, 1, 0),
                                   max_tuples=100_000, max_parent_wires=8)
    assert source["L"] == 4
    checked = verify_point_mode_action(source, certificate)
    assert checked["valid"] and checked["node"] == -2


def test_nontrivial_clause_network_matches_independent_parent_point():
    cnf = CNF.from_lists(4, [[1, 2], [-3, 4]])
    f = first_irreducible(5)
    network = describe_integer_network(from_cnf(cnf), creation_precision=5,
                                      defining_polynomial=f)
    source = implicit_sparse_mode_source(
        construct_implicit_packing(network.bipartite_edges(), r=4, a=1,
                                  max_work=3_000_000), max_work=3_000_000)
    cert = make_point_modes(source, node=-1, precision=8,
                            extension_degree=5, zeta=(1, 0, 0, 0, 0),
                            max_tuples=100_000, max_parent_wires=8)
    child = contract_point_child_expansion(network, cert, max_parent_wires=8,
                                           max_tuples=100_000, max_work=2_000_000,
                                           timeout_s=30)
    parent = independent_parent_point(network, source, cert, max_edges=8,
                                      max_work=5_000_000, timeout_s=30)
    assert child["direct_oracle_matches"] and parent["valid"]
    assert child["result"][0] == tuple(parent["result"])


@pytest.mark.parametrize("mutation", [
    "missing_mode", "wrong_coefficient", "wrong_sign", "duplicate_mode",
    "wrong_shift", "wrong_point", "overstated_weight", "duplicate_row",
    "wrong_row_support",
])
def test_independent_action_oracle_rejects_adversarial_mode_mutations(mutation):
    _, source, original = _case(4, precision=5, degree=3)
    cert = deepcopy(original)
    assert cert["modes"]
    if mutation == "missing_mode":
        cert["modes"].pop()
    elif mutation == "wrong_coefficient":
        mode = cert["modes"][0]
        mode["rows"][0][1][0][0] = (mode["rows"][0][1][0][0] + 1) % (1 << cert["precision"])
    elif mutation == "wrong_sign":
        mode = cert["modes"][0]
        row = mode["rows"][0][1][0]
        mode["rows"][0][1][0] = [(-v) % (1 << cert["precision"]) for v in row]
    elif mutation == "duplicate_mode":
        cert["modes"].append(deepcopy(cert["modes"][0]))
    elif mutation == "wrong_shift":
        cert["node"] = 0
    elif mutation == "wrong_point":
        cert["zeta"][0] = (cert["zeta"][0] + 1) % (1 << cert["precision"])
    elif mutation == "overstated_weight":
        cert["modes"][0]["weight"] = cert["precision"]
    elif mutation == "duplicate_row":
        cert["modes"][0]["rows"].append(deepcopy(cert["modes"][0]["rows"][0]))
    elif mutation == "wrong_row_support":
        cert["modes"][0]["rows"][0][0] = 10_000
    checked = verify_point_mode_action(source, cert)
    assert not checked["valid"]
    assert "result" not in checked


def test_independent_pruning_checks_precision_boundary_and_stream_completeness():
    network, source, certificate = _case(4, precision=3, degree=3)
    tuples = tuple(structural_tuples(certificate["modes"], 3, max_tuples=1000))
    checked = audit_finite_pruning(certificate["modes"], 3, emitted_tuples=tuples)
    assert checked["valid"]
    assert checked["precision_pruned_tuple_count"] > 0
    assert checked["valuation_certified_pruned_tuple_count"] == checked["precision_pruned_tuple_count"]
    altered = list(tuples)
    if len(altered) > 1:
        altered[-1] = altered[-2]
        rejected = audit_finite_pruning(certificate["modes"], 3, emitted_tuples=altered)
        assert not rejected["valid"]
    child = contract_point_child_expansion(network, certificate, max_parent_wires=8,
                                           max_tuples=1000, max_work=2_000_000,
                                           timeout_s=30)
    parent = independent_parent_point(network, source, certificate, max_edges=8,
                                      max_work=5_000_000, timeout_s=30)
    assert child["direct_oracle_matches"] and parent["valid"]
    assert child["result"][0] == tuple(parent["result"])

    # Independently enumerate every unweighted coefficient in the small mode
    # box. The precision-pruned tail must vanish coefficient by coefficient.
    modes = certificate["modes"]
    group_rows = {}
    for mode in modes:
        group_rows.setdefault((mode["packet"], mode["target_group"]), set()).update(
            rid for rid, _ in mode["rows"])
    caps = [len({rid for rid, _ in mode["rows"]}) for mode in modes]
    full = (0, 0, 0)
    retained_sum = (0, 0, 0)
    modulus = 1 << certificate["precision"]
    for beta in product(*(range(cap + 1) for cap in caps)):
        loads = {}
        for exponent, mode in zip(beta, modes):
            key = (mode["packet"], mode["target_group"])
            loads[key] = loads.get(key, 0) + exponent
        if any(load > len(group_rows[key]) for key, load in loads.items()):
            continue
        coefficient = independent_tuple_coefficient(
            network, source, certificate, beta, max_edges=4,
            max_work=2_000_000, timeout_s=30)
        assert coefficient["valid"], coefficient
        value = tuple(coefficient["result"])
        full = tuple((x + y) % modulus for x, y in zip(full, value))
        weight = sum(exponent * mode["weight"] for exponent, mode in zip(beta, modes))
        if weight < certificate["precision"]:
            retained_sum = tuple((x + y) % modulus for x, y in zip(retained_sum, value))
        else:
            assert value == (0, 0, 0)
    assert retained_sum == child["result"][0]
    assert full == tuple(parent["result"])


def test_pruning_refuses_an_underestimated_valuation_or_unproved_discard():
    _, _, certificate = _case(4, precision=3, degree=3)
    modes = deepcopy(certificate["modes"])
    # Keep the coefficient intact and raise its declared valuation weight.
    # The independent checker must reject the false premise before pruning.
    modes[0]["weight"] = 3
    result = audit_finite_pruning(modes, 3)
    assert not result["valid"]
    assert "valuation" in result["reason"]

    _, source, mutated = _case(4, precision=3, degree=3)
    mutated = deepcopy(mutated)
    mutated["modes"][0]["rows"][0][1][0] = [1, 0, 0]
    assert not verify_point_mode_action(source, mutated)["valid"]
    bad_bound = audit_finite_pruning(mutated["modes"], 3)
    assert not bad_bound["valid"] and "valuation" in bad_bound["reason"]


def test_overlapping_supports_and_hall_deficiency_are_not_unsafely_pruned():
    def synthetic(packet, target, rows):
        return {"packet": packet, "target_group": target, "weight": 1,
                "rows": [[rid, [[2]]] for rid in rows]}

    overlapping = [synthetic(0, 0, (0,)), synthetic(0, 0, (0, 1))]
    overlap_check = audit_finite_pruning(overlapping, 2)
    assert overlap_check["valid"]
    assert overlap_check["structurally_zero_tuple_count"] > 0

    # Modes A and B both require row 0; C can use rows 1 or 2. The tuple
    # (1,1,1) passes the coarse group-union bound but fails Hall's condition.
    hall_modes = [synthetic(0, 0, (0,)), synthetic(0, 0, (0,)),
                  synthetic(0, 0, (1, 2))]
    hall_emitted = [beta for beta in product(range(2), range(2), range(3))
                    if sum(beta) < 4 and sum(beta) <= 3]
    assert (1, 1, 1) in hall_emitted
    hall_check = audit_finite_pruning(hall_modes, 4, emitted_tuples=hall_emitted)
    assert hall_check["valid"] and hall_check["hall_pruning_checked"] is False
    assert hall_check["retained_tuple_count"] == len(hall_emitted)


@pytest.mark.parametrize("n", [4, 6])
def test_direct_parent_oracle_and_complete_child_sum_for_selected_small_calls(n):
    f = first_irreducible(5)
    cnf = CNF.from_lists(n, [[i] for i in range(1, n + 1)])
    network = describe_integer_network(from_cnf(cnf), creation_precision=n + 1,
                                      defining_polynomial=f)
    plan = make_source_tapered_plan(M=network.edges, a=1, u=1, p=n + 1,
                                    max_precision_bits=1024)
    node = next(item for item in plan.nodes if item.t == -1)
    source = implicit_sparse_mode_source(
        construct_implicit_packing(network.bipartite_edges(), r=4, a=1,
                                  max_work=3_000_000), max_work=3_000_000)
    certificate = make_point_modes(source, node=-1,
                                   precision=node.precision_bits,
                                   extension_degree=5,
                                   zeta=(1, 0, 0, 0, 0),
                                   max_tuples=100_000, max_parent_wires=8)
    child = contract_point_child_expansion(network, certificate,
                                           max_parent_wires=8,
                                           max_tuples=100_000,
                                           max_work=2_000_000,
                                           timeout_s=30)
    parent = independent_parent_point(network, source, certificate,
                                      max_edges=8, max_work=5_000_000,
                                      timeout_s=30)
    assert child["direct_oracle_matches"]
    assert parent["valid"], parent
    assert child["result"][0] == tuple(parent["result"])
    assert parent["half_edge_assignments"] == 1 << (2 * n)


def test_pinned_eight_wire_point_matches_independent_parent_and_child_sums():
    n = 8
    f = first_irreducible(5)
    cnf = CNF.from_lists(n, [[i] for i in range(1, n + 1)])
    network = describe_integer_network(from_cnf(cnf), creation_precision=9,
                                      defining_polynomial=f)
    plan = make_source_tapered_plan(M=network.edges, a=1, u=1, p=9,
                                    max_precision_bits=1024)
    node = next(item for item in plan.nodes if item.t == -1)
    points = distinct_residue_points(ExtensionRing(node.precision_bits, f),
                                     plan.degree_bound + 1, max_points=32)
    zeta = points[1]
    assert zeta == (1, 0, 0, 0, 0)
    source = implicit_sparse_mode_source(
        construct_implicit_packing(network.bipartite_edges(), r=4, a=1,
                                  max_work=3_000_000), max_work=3_000_000)
    certificate = make_point_modes(source, node=-1,
                                   precision=node.precision_bits,
                                   extension_degree=5, zeta=zeta,
                                   max_tuples=100_000, max_parent_wires=8)
    assert len(certificate["modes"]) == 6
    assert certificate["structural_tuple_count"] == 64
    mode_check = verify_point_mode_action(source, certificate,
                                          max_entries=4096, max_work=1_000_000,
                                          timeout_s=30)
    assert mode_check["valid"], mode_check
    tuples = tuple(structural_tuples(certificate["modes"], 521,
                                     max_tuples=100_000))
    prune_check = audit_finite_pruning(certificate["modes"], 521,
                                       emitted_tuples=tuples)
    assert prune_check["valid"], prune_check
    child = contract_point_child_expansion(network, certificate,
                                           max_parent_wires=8,
                                           max_tuples=100_000,
                                           max_work=2_000_000,
                                           timeout_s=30)
    parent = independent_parent_point(network, source, certificate,
                                      max_edges=8, max_work=5_000_000,
                                      timeout_s=30)
    expected = (169600000000, 0, 0, 0, 0)
    assert child["direct_oracle_matches"]
    assert child["result"] == (expected,)
    assert child["direct_oracle_result"] == (expected,)
    assert parent["valid"] and tuple(parent["result"]) == expected
